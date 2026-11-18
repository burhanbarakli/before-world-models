# Temaslı sokma protokolü

Temaslı hiçbir koşu yapılmadan, kod yazılmadan yazıldı (2026-11-02). Sonraki değişiklikler "Sapmalar" bölümüne işlenir.

Şimdiye kadarki bütün sonuçlar deliksiz bir benzetimdendi: çarpışmalar kapalıydı, "sokma" geometrik ölçüttü
([panda_learned/README.md](../panda_learned/README.md)). η seçimini de "ne zaman ilerle" sorusunu da elle yazılmış
kurallar çözdü. Elle yazılan kuralların göremediği şey, alanın **yanlış yere** gidiyor olmasıdır: delik sanıldığı yerde
değilse `d = ‖c‖` küçük kalır, kapı açıktır, çubuk ağzın kenarına çarpar. Bu bilgi yalnız temasın kendisinde vardır.

Soru: gerçek delikte, delik konumu hatalıyken, klasik bir temas refleksi işi çözüyor mu, yoksa delik konumunu bilmek
kayda değer pay bırakıyor mu? World model bu deneyde **kurulmaz**. Deney yalnız onun için yer olup olmadığını ölçer.

Makalenin gerçek robot deneyi temasa bu yüzden değer verir: başarı "şemsiye deliğe girdi" demektir ve bir taban yöntemi
"deliğin köşesine çarparak" kalır. Ama makale kuvvet ölçümü, boşluk ve delik konum hatası vermiyor. Sayılar
karşılaştırılamaz.

Bu protokolden önce görülen: temassız bütün sonuçlar. Alan modelleri ve koşul değerleri onlardan alınır. Temaslı
davranış hakkında hiçbir ölçüm yok.

## Kurulum

Değişmeyenler: Panda, `θ̇ = J† V`, 100 Hz kontrol, delikler `gate_rule.HOLES`, ağız `z = 0.25`, derinlik 0.06 m,
`T`, kural `η = min(20, 0.6 / (h + τ))`, kapı `KAPI0` (`L = 0.02`, bant 0.12 m).

Yeni olanlar:

- **Delik.** Yarıçap `r + c`, `r = 10 mm`. Sabit bir tutucu blokta, 24 kutudan halka. Kenar pahı yok. Boşluk `c` artık
  eşik değil, fiziksel ölçüdür.
- **Çubuk.** Tutma noktasından takım çerçevesine uzanan silindir, URDF'e sabit bağlantı olarak eklenir. Yalnız çubuk
  çarpışır, kolun geri kalanı kapalı kalır.
- **Sürtünme.** `μ ~ U(0.2, 0.8)`, koşu başına çekilir, politikalar görmez.
- **Uyum.** Hız kontrolü temasta sonsuz sert olduğu için kuvvet ölçümüyle admitans eklenir:
  `V ← V + A F`. `F`, çubuk ucundaki temas kuvvetlerinin toplamıdır, 20 ms ortalanır, `σ = 0.5 N` gürültü eklenir ve
  komutla aynı `h`, `τ` yolundan geçer. Bütün kol ve politikalarda aynıdır.
- **Delik konum hatası `e`.** Gerçek delik, alanın sandığı yerden yatayda `e` kadar kaymıştır. Yön rastgele, büyüklük
  koşula göre. Alan yeniden eğitilmez: makale kolu da analitik kol da eski deliğe gider. Algı hatasının yerini tutar.
- **Bozucu.** Aynı büyüklükte (ölçek 0.2) ama anlık sıçrama değil, 100 ms süren dış itme. Sıçrama çubuğu duvardan
  geçirir. İtme gecikme yolunu atlar, doğrudan eklem hızına eklenir.
- **Bozucu tetiği yüksekliktir.** Kapısız bozucusuz referansta `gap` öncesine denk gelen `z` geçilince tetiklenir.
  Böylece erken yavaşlayan robot pay almaz ([PROTOKOL_KAPI.md](../panda_learned/PROTOKOL_KAPI.md), Sapma 4).

## Tek arayüz: alan kaydırma

Bütün politikalar aynı şeyi değiştirir, başka hiçbir şeyi değil. Alan `(R, p − ŝ)` noktasında değerlendirilir, `ŝ`
yatay ve politika tarafından verilir. Sabit `ŝ` için bu alanın katı ötelemesidir, yani `D` Lyapunov işlevi ve tüp sınırı
aynen kalır. `ŝ` değiştikçe `D` sıçrar, güvence ancak bekleme süresi koşuluyla taşınır; bu deney bunu sınamaz.

Sonraki model aşaması da yalnız `ŝ` üretebilir. Yani model, kararlılık yapısının dışına çıkmak zorunda kalmaz.

## Politikalar

| Politika | `ŝ` | Görev |
|---|---|---|
| `TABAN` | hep 0 | kural ve kapı, temasa tepki yok |
| `REFLEKS` | spiral arama | klasik temas stratejisi, modelsiz |
| `KAHİN` | başlangıçta `e`, refleks açık | deliğin yerini bilir; konum tahmin eden her modelin üst sınırı |

`REFLEKS`: ağız yakınında (`z − z_rim ≤ 0.02`) `F_z ≥ F_t` beş adım sürerse temas sayılır. Çubuk bastırır halde kalır,
`ŝ` Arşimet spirali izler (hız `v_s`, adım `2c`, yarıçap en çok 15 mm). Çubuk ağzın 5 mm altına düşünce `ŝ` donar.
Başlangıç değerleri `F_t = 5 N`, `v_s = 20 mm/s`. Yöntem kuvvet kontrollü montajın standart yoludur; atıf verilmedi,
literatür taraması yapılmadı.

`KAHİN`, seçimden gelmediği için en-çoğun yanlılığını taşımaz. Bu nedenle önceki `KOŞU-KAHİN`'in aksine kapı açabilir.
Yalnız bir şeyi ölçer: **konum bilgisinin değerini**. Sürtünme veya sıkışma tahmininin değerini ölçmez.

## Pilot

Ana koşudan önce, tohum 900 ve üstü, yalnız aşağıdaki hücrelerde. Pilotta `TABAN` ile `KAHİN` karşılaştırılmaz.

| Denetim | Koşul | Geçme |
|---|---|---|
| M1 regresyon | çarpışma kapalı, `A = 0`, bozucusuz | `panda_learned` ile aynı, `lat` farkı `< 0.5 mm` |
| M2 geçilebilirlik | `e = 0`, `c = 5`, bozucusuz, `h = 20`, `T = 8`, analitik, 25 koşu | `TABAN` en az 0.95 |
| M3 duvar | `e = 15 mm`, `c = 2`, arama yok, `T = 4, 8`, `h + τ = 130 ms` | derinlik her koşuda `≤ 1 mm`, çubuk geçmiyor |
| M4 temas kararlılığı | M2 ve M3 | süzülmüş en büyük kuvvet `< F_max`, süren salınım yok |
| M5 sayısal | M2 ve M3, benzetim adımı yarıya | başarı farkı `≤ 0.05`, en büyük kuvvet farkı `≤ %20` |
| M6 süre | 8 iş | koşu başına ortalama `≤ 3 s` |

Pilotta ayarlanabilen sabitler: benzetim hızı (500 veya 1000 Hz), `A` (`{1, 2, 4} mm/s/N`), PyBullet temas marjı, `F_t`,
`v_s`. Son ikisi `e ∈ {3, 6} mm`, `c = 5`, `T = 8`, `h = 20` hücrelerinde `REFLEKS` başarısına göre seçilir. Bu ayar
bilerek modelin aleyhinedir: model zayıf bir tabanı değil, iyi ayarlanmış bir tabanı geçmelidir. M5 kalırsa ana koşu
yapılmaz. M6 kalırsa önce tohum sayısı yarıya iner, Sapma olarak yazılır.

`c`, `e`, `tf`, `F_max`, eşikler ve politikaların tanımı pilotta değişmez.

## Koşullar

- `T ∈ {8, 4}`.
- `(h, τ) ∈ {(20, 0), (40, 25), (90, 40)} ms`.
- Bozucu: yok, ya da `gap = 0.25 s`.
- `e ∈ {0, 3, 6, 10} mm`, yön tohumdan.
- `c ∈ {5, 2} mm`. Birincil 5, kararlar onda. 2 ikincildir.
- Delik başına 20 tohum, tohum akışı yeni (100–119). Politikalar arasında `e` yönü, `μ`, bozucu ve algı gürültüsü
  **eşleştirilmiştir**. Seçilen bir politika olmadığı için seçim yarısı yoktur, bütün tohumlar skordur.
- Kollar: makale (model 0, 1, 2), analitik. Kararlar makale kolunda, üç modelin ortalamasında.
- `tf = T + 8 s`. Arama süre harcar ve bu bedel ölçüme dahildir. Önceki deneyde süre sınırı hiç bağlamamıştı.

`e = 0`'da `KAHİN = REFLEKS` olduğu için koşulmaz. Toplam 105.600 koşu. Temassız koşu hızına göre kaba tahmin yarım
gün ile bir gün arasındadır, M6 gerçek değeri verir.

## Başarı

**Birincil `SR`:** son derinlik hedefin en az %90'ı **ve** 20 ms süzülmüş temas kuvveti hiçbir anda `F_max = 50 N`
değerini geçmiyor. Yanal ölçüt yoktur, çünkü artık duvar vardır. Skor `S`, birincil hücrelerin (`c = 5`) `e > 0`
ortalamasıdır, bozucu ve bozucusuz eşit ağırlıklı.

İkincil: varış süresi (başaramayan koşu `tf` sayılır), ortalama ve en büyük kuvvet, sıkışma oranı (son 2 s'de derinlik
değişmiyor ve hedefe varmamış), `c = 2`.

## Karar

Bootstrap: modeller, delikler ve tohumlar yeniden örneklenir, 2000 tekrar, yüzdelik aralık. Seçim olmadığı için önceki
yanlılık beklenmez, yine de ortalama kaydırması ve pivot birlikte raporlanır. Karar yüzdelik aralıktadır.
Üç modelle model belirsizliği kabadır.

- **G, geçerlilik:** `e = 0`'da `S(TABAN) ≥ 0.85`. Tutmazsa görev kurulumu yanlıştır, sonuç okunmaz.
- **K, sorun var mı:** `K = S_{e=0}(TABAN) − S(TABAN)`. `K ≥ 0.10` ve alt sınır `> 0`. `e > c` duvara çarptırdığı için
  bunun geçmesi beklenir. Asıl soru sonraki ikisidir, kalırsa kurulum beklenmedik biçimde affedicidir.
- **R, refleks değer katıyor mu:** `R = S(REFLEKS) − S(TABAN)`.
- **W, konum bilgisinin değeri:** `W = S(KAHİN) − S(REFLEKS)`, aralık `[alt, U]`.

| Sonuç | Karar |
|---|---|
| G kaldı | Geçersiz. Kurulum incelenir |
| K kaldı | Temas ve bu konum hataları sorun değil. Model açılmaz |
| K geçti, `U < 0.03` | Konum tahmin eden model gerekmiyor. `S(REFLEKS) ≥ 0.85` ise refleks yetiyor, değilse sorun konum dışındadır |
| K geçti, `W < 0.03 ≤ U` | Küçük bir pay dışlanamıyor. Model açılmaz, yük modelindir |
| K geçti, `W ≥ 0.03`, alt sınır `> 0` | Konum bilgisi pay bırakıyor. Önce basit tahminci sınanır, sonra model |

Son satır world model'i doğrudan açmaz. Önce temas noktalarından geometrik `ŝ` tahmini gibi basit, modelsiz bir tahminci
ayrı protokolle sınanır. World model ancak onu `0.03` geçerse aday olur.

`W` küçük ama varış süresinde `KAHİN` en az 1 s kazandırıyorsa bu başarı açısından modeli açmaz, hedef süre olan ayrı bir
protokol gerekir.

Betimsel, karara girmez:

- `1 − S(KAHİN)`: konum bilmeyle çözülmeyen hata. Sıkışma payı büyükse bu, konum dışı bir tahminin (sürtünme, sıkışma)
  hipotezidir, sonuç değildir.
- Öğrenme bedeli: analitik ile makale kolunun farkı. Kapının alan yanlılığıyla temas altında davranışı.
- `T`, `h + τ`, `e`, bozucu dilimleri, `c = 2`, `μ`'ya göre başarı.

## Bilinen zayıflıklar

- `W`'nin büyüklüğü `tf` ve spiral hızına bağlıdır. `e` büyük ve `c` küçükse arama zamanı doğal olarak uzar. Bu nedenle
  birincil `c = 5`, ve `REFLEKS` önceden ayarlanır.
- PyBullet temas modeli sert cisimlerde kabadır. Sürtünme ve sıkışma nicel olarak gerçek robota taşınmaz. M5 yalnız
  sayısal kararlılığı gösterir, fiziksel doğruluğu göstermez.
- Delik konum hatası yapaydır, kapı `c` dışında bir şey görmez. Gerçek algı hatasının dağılımı ölçülmedi.
- Takım geometrisi gerçek şemsiye değildir. Makalenin tutucu ölçüleri yayımlanmamış.
- `KAHİN` yalnız konum bilgisini ölçer. `W` küçük çıkarsa model başka bir bilgiyle hâlâ yararlı olabilir, ama bu deney
  onu göstermez.

## Sapmalar

1. **Uyum iç döngüye alındı, iki mekanik sabit eklendi (2026-11-12, pilot denetimlerinden önce).** İlk deneme
   koşularında (delik 0, tohumsuz, birkaç koşu, `TABAN` ve `REFLEKS`) kuvvet sürekli değil, darbeler halinde geldi:
   hız motoru sert temasa her adımda 100–270 N'luk darbe uyguladı, 100 Hz uyum bu darbeleri kovalayıp titreşti.
   Değişiklikler:
   - **Uyum gecikme yolundan çıkarıldı.** `A F` terimi `h`, `τ` yolundan geçmiyor, benzetim hızında uygulanıyor.
     Gerekçe: gerçek Panda'da uyum 1 kHz eklem döngüsündedir, gecikme alan sunucusuyla iletişimdedir (makalenin
     3. hata kaynağı). Denetleyicinin gördüğü ölçüm (refleks için) hâlâ 100 Hz, 20 ms süzülmüş ve gürültülüdür.
   - **Uyumun gördüğü kuvvete 10 ms birinci derece süzgeç** (`TAU_ADMIT`). Süzgeçsiz uyum hiçbir `A`'da kararlı olmadı.
   - **PyBullet temas sertliği ve sönümü** çubukta ve tutucuda (`K_CONTACT = 1e4`, `D_CONTACT = 280`). Ölçülen etkin
     sertlik yaklaşık `1e5 N/m`.
   - Uyum yalnız ötelemededir, dönme uyumu yoktur.
   Seçim yalnız mekanik ölçüte göre yapıldı: deliğe kapalı bir yere bastırırken kuvvetin ortalaması, oynaklığı ve en
   büyüğü (`A ∈ {1, 2, 4} mm/s/N`, süzgeç `{0, 10, 30} ms`, 500 ve 1000 Hz). Seçilen: 1000 Hz, `A = 4 mm/s/N`,
   10 ms. Sabit bastırma kuvveti `T = 8`'de yaklaşık 15 N, `T = 4`'te 29 N, yani alanın iniş hızı bölü `A`.
   Bu deneme koşularında `TABAN` duvarda kaldı, `REFLEKS` birkaç durumda girdi. Politikalar karşılaştırılmadı,
   ama bu satır görüldüğünü kaydeder.
2. **İlk pilot bozuk tutucuyla koşuldu, geçersiz sayıldı.** `createCollisionShapeArray` 24 kutunun bir kısmını düşürdü,
   tutucunun bir çeyreği yoktu (ışın taramasıyla görüldü). M3'te çubuk bu boşluktan inip "duvardan geçti" (tutma 0.68),
   M4'te salınım çıktı. Tutucu kutu başına ayrı cisimle yeniden kuruldu, ışın taraması tam halka verdi, M3 yeniden
   denendiğinde 50/50 tuttu. Sapma 1'deki ilk deneme koşuları da bu bozuk tutucuyla yapılmıştı; uyum ayarı yalnız
   kapalı bölgede bastırma kuvvetine baktığı için etkilenmedi. İlk pilotun çıktısı `results/pilot_v1_broken_holder.txt`,
   `REFLEKS` ayarı dahil bütün pilot yeniden koşuldu.
3. **Pilot sonucu ve ondan sonra yapılanlar (2026-11-12, ana koşudan önce).** `results/pilot.txt`: M1, M2, M3, M5 geçti.
   - **M4'ün kodlanmış ölçütü kaldı.** En büyük süzülmüş kuvvet 49.1 N, yani `F_max` altında. Ama 75 koşudan 6'sında son
     2 s'deki `F_z` oynaklığı `max(1 N, ortalamanın %10'u)` sınırını aştı. Hepsi duvar koşuları (M3). İnceleme:
     yaklaşık 0.5 Hz yavaş kayma, aralık 7–12 N, yükseklik oynaması 0.2 mm'nin altında, yani titreşim değil, duvarda
     yapış-kay. Protokol M4 kalırsa ne olacağını söylemiyor. Ana koşu bu yüzden durdurulmadı, kalma burada kaydedilir.
   - **M6 önce kaldı (6.6 s/koşu, 21 saat), hız düzeltmesinden sonra geçti (2.5 s/koşu, yaklaşık 8 saat).** Tutucu
     kutuları birbiriyle çarpışma çifti oluşturuyordu. Çarpışma maskesi yalnız çubukla çarpışacak biçimde değiştirildi.
     Dört örnek koşu bit düzeyinde aynı çıktı. Tohum sayısı bu yüzden yarıya indirilmedi.
   - **`REFLEKS` ayarı:** `F_t = 5 N`, `v_s = 10 mm/s` (SR 0.950). `F_t` başarıyı hiç değiştirmedi, eşitlikte protokolün
     varsayılanı alındı. `v_s = 20 mm/s` 0.925, 40 mm/s 0.870.
   - **Ana betiğin kaydetme yolu pilot tohumu 900 ile küçük bir koşuda sınandı** (`T = 4`, `h = 20`, `c = 5`, analitik ve
     model 0). Bu koşuda politikaların sonuçları da göründü: `e = 3, 6 mm`'de üçü de başardı, `e = 10 mm`'de `TABAN`
     kaldı, ötekiler başardı. Delik başına tek tohum, karar için kullanılmadı. Bir şey değiştirilmedi.
4. **Ana koşudan sonra (2026-11-13), sonucu değiştirmeyen düzeltmeler.**
   - `analyze_contact.py` itme oranını `nan` yazdı, çünkü `e = 0`'daki bilerek boş `KAHİN` hücrelerini ortalamaya kattı.
     `nanmean` ile düzeltildi. Gerçek oran bozuculu koşularda 1.000, bozucusuzlarda 0.000.
   - Varış süresi maddesi (`W` küçük ve `KAHİN` en az 1 s kazandırıyor) çözümleyicide basılmıyordu, denetim yakaladı.
     Madde tetiklendi (`REFLEKS − KAHİN = 1.66 s`), artık basılıyor. Karar satırı değişmedi.
   - Sapma 3'teki "bit düzeyinde aynı" yalnız aynı süreçte arka arkaya koşulan dört örnek için doğruydu. Denetimin
     yeniden koşuları saklananlardan çok az farklı çıktı (`end_z` 0.2096 / 0.2098, `f_max` 78.26 / 78.28), çünkü işçinin
     önceki koşuları PyBullet durumunu etkiliyor. Sonuçlar aynı, hiçbir politikaya yönelik değil.
   - Denetim betikleri `audit/` içindedir.
5. **Kuvvet süzgecinde hata (2026-11-15, süre protokolünün pilotunda bulundu).** `contact.py`'deki 20 ms kayan
   ortalama `popleft()`'tan sonra `len(win)`'e, yani 20 yerine 19'a bölüyordu. Süzülmüş kuvvet her yerde tam 20/19
   (%5.3) yüksek okundu: başarı ölçütündeki 50 N sınırı gerçekte 47.5 N, `REFLEKS` tetiği 5 N yerine 4.75 N,
   raporlanan kuvvetler (pilot dahil) %5.3 yüksek. Kod koşulduğu haliyle bırakıldı, satıra not düşüldü.
   Saklanan `f_max` tam olarak 20/19 kat yüksek olduğu için karar düzeltilmiş ölçütle yeniden hesaplandı:
   S 0.620 / 0.945 / 0.963, G 0.963, K +0.343, R +0.325, **W +0.018 [0.004, 0.036]** (pivot [0.000, 0.032]),
   aynı karar satırı. `c = 2`: W +0.171 [0.141, 0.199]. Tetik eşiğinin etkisi yeniden hesaplanamaz, ama pilotta
   `F_t ∈ {3, 5, 8}` başarıyı hiç değiştirmemişti.
6. **Varış süresinde tanım hatası (2026-11-15, süre protokolünün denetiminde bulundu).** Çözümleyici "başarısızlar
   `tf` sayılır" yazıp `t_in` kullandı; derine inip `F_max`'ı aşan koşular gerçek süresini korudu. Düzeltilmiş tanımla
   `REFLEKS − KAHİN` 1.66 s yerine 1.63 s [1.44, 1.84] (bu protokolün denetimi). Süre maddesi yine tetiklenir,
   karar satırı süreye bağlı değildir.
