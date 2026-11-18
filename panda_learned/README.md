# panda_learned: öğrenilmiş alan ve hız kapısı

Makalenin tarifiyle eğitilmiş GVF, PyBullet Panda üzerinde, geç bozucu altında. Görev ve koşullar `panda_gate1` ile
aynıdır. Kurallar [PROTOKOL_KAPI.md](PROTOKOL_KAPI.md) içinde, sonradan yapılan değişiklikler "Sapmalar" bölümünde.
[PROTOKOL.md](PROTOKOL.md) alan eğitimini tanımlar, oradaki kural deneyi koşulmadı.

## Çalıştırma

    ./train_all.sh                # alan modelleri, MPS, birkaç saat; torch gerekir
    ./run_speed.sh                # alan hatası, 120.000 koşu, çözümleme; yaklaşık 6 saat; pybullet gerekir

| Dosya | İş |
|---|---|
| `make_data.py`, `train_field.py`, `train_all.sh` | Veri ve DeepOVec eğitimi |
| `learned.py`, `field_error.py` | Alanı robotta kullanma, alan hatası |
| `gate_learned.py` | Kollar ve koşullar; `gate_speed.py` modül olarak kullanır |
| `gate_speed.py`, `analyze_speed.py`, `run_speed.sh` | Hız kapısı deneyi ve karar kuralları |
| `analyze_learned.py` | Kullanılmadı, bırakılan kural deneyi için yazılmıştı |
| `audit_speed/` | Bağımsız denetim betikleri ve çıktıları; içlerindeki yollar geçici dizini gösterir |

`models/`: model 0, 1, 2 (20.000 adım), model 3 (zayıf, 4.000 adım). `results/`: `analysis_speed.txt` (karar),
`field_error.txt`, `gate_speed.npz`.

## Sonuç

**Ön-kayıtlı sonuç: `H` geçti, `Q < 0.03`, yani "kapı yetiyor, koşu başına kusursuz bir tahminci bile kayda değer
kazanç bırakmıyor, model gerekmiyor". Bu sonuç temassız bir görev içindir.**

| Politika, c = 5 mm, test yarısı, makale kolu | S |
|---|---|
| `KURAL`, kapı yok | 0.855 |
| `KAPI0`, `L = 0.02`, seçim yok | 0.960 |
| `TABLOK`, her model ve `(T, h, τ)` için ayrı | 0.970 |
| `KOŞU-KAHİN`, üst sınır | 0.970 |

- `H` 0.105 [0.074, 0.139], `P` 0.010 [0.001, 0.023], `Q` 0.010 [0.001, 0.024].
- `P` ve `Q` büyük ölçüde zamanlama etkisidir (Sapma 4). Bozucu yüksekliğe bağlanınca `H` 0.103, `P` −0.0004,
  `Q` 0.0015 [0, 0.005]. Bu yeniden koşu ön-kayıtlı değildir, kısmi örnekle yapıldı.
- Analitik kol: `KURAL` 0.856, `KAPI0` 0.959, `H` 0.103. Zayıf kol: 0.845, 0.953, 0.108. Öğrenme bedeli bu ölçekte
  görünmüyor. Bozucusuz `SR_insert`: makale 1.000, zayıf 0.983, analitik 1.000.
- Skor düzeyi iyimser: zor bölge test yarısında %6.5, seçim yarısında %13.6. Bütün tohumlarda `KAPI0` 0.931,
  `KURAL` 0.816, `H` 0.115.
- İkincil: `c = 2 mm`'de `H` 0.256, `Q` 0.019. `c = 10 mm`'de `H` 0.030, `Q` 0.008.
- Dilimler, `KURAL` → `KAPI0`: `T = 8` 0.829 → 0.919, `T = 4` 0.880 → 1.000, `Δ = 0.25` 0.745 → 0.922,
  `h + τ ≥ 0.09` 0.747 → 0.948.
- Analitik kolda hiçbir η'da başarmayan koşuların (%14.6) %52.8'ini `KAPI0` kurtarıyor. Yani kuralın bıraktığı
  başarısızlıkların yarısı gerçekten zamandandı.
- Kapının bedeli: derinliğe varış ortalama 0.23 s, en çok 0.54 s gecikiyor (model 0, test tohumları, üç gecikme
  ayarı). `T + 4 s` sınırı hiç bağlamadı, yani süre bedeli yalnız ilke olarak ölçüme dahil.
- Kalan `KAPI0` hatalarının tamamı bozucunun ağız altına veya ağzın 8 mm'den yakınına attığı, 5 mm'den fazla yanal
  hatalı koşulardır. %36'sı ağız altına düşer, orada kapı devre dışıdır. Sağlam `T = 8`, `Δ = 0.25` tavanı yaklaşık 0.84.
- Başarı kümeleri iç içedir: `L = 0.01`'in başaramadığı hiçbir koşu başka seçenekte başarmıyor (makale kolu). Bu yüzden
  `KOŞU-KAHİN` burada şans toplamıyor. Üst sınır yalnız bu beş seçenek içindir.

Bağımsız denetim karar değiştiren kusur bulmadı: skorlar ayrı kodla yeniden hesaplandı, 8 iş bit düzeyinde aynı çıktı,
test tohumlarından seçime sızıntı yok. Tek delik çıkarılınca `H` 0.096–0.111, `Q` 0.007–0.012. Yer değiştirmiş yarılarda
`H` 0.125, `Q` 0.018. 5000 rastgele bölmenin hepsinde sonuç aynı, `Q` en çok 0.023.

## Alan

Üç modelde makale örneklemesinde c rms 0.118–0.122, m rms 0.022–0.023, m/hız 0.026–0.028. Bozucu bölgesinde c rms 0.008,
m rms 0.003. Zayıf model bunların yaklaşık iki katı. Makale, Tablo V: DeepOVec CVF 2.95e-3, MVF 8.68e-3; birimler net
olmadığı için doğrudan karşılaştırılmadı. Referans üstünde aşağı inişte `|c_v|` 0.3–0.4 mm, zayıf modelde 0.5–0.95 mm.

Zayıf modelin yanlılığı `L = 0.01` eşiğine yakındır ve kapıyı gerçekten kilitliyor (Sapma 5). `L` alan hatasının altına
inmemeli. `L = 0.02` hiçbir kolda takılma eklemedi.

## Sınırlar

- **Delik yok.** Bütün çarpışmalar kapalı (`panda_gate1/robot.py:36`). "Sokma" geometrik bir ölçüttür, temas kuvveti,
  sıkışma veya sürtünme yoktur. `H`, kapının kinematikte düzeltme süresi kazandırdığını gösterir, temaslı sokmayı değil.
- Algı kusursuz, motor ideal. Koşu başına tek ve anlık, yaklaşık 19.5 mm'lik sıçrama. Yalnız 200 farklı bozucu, testte 100.
- `KURAL`'ın öğrenilmiş alanda sabit η'yı veya tabloyu geçtiği **ölçülmedi** (Sapma 2).
- Beş delik, üç model. Bu koşullar ve tohumlar analitik alanda daha önce görüldü, üzerlerinde ayar yapılmadı. Yörüngeler
  insan gösterimi değil, yeniden kurgu.
- Kapılı bozucusuz koşu ölçülmedi (Sapma 6). Öncesinden yavaşlayan robot için bozucu anı saatle verildi (Sapma 4).
- Ön-kayıt zamanı dosya tarihlerine dayanıyor, depo git değil.
- Phase stopping fikri bilinir. Atıf bellekten, literatür taraması yapılmadı.
