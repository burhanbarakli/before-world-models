# panda_gate1: gecikme altında başarı–η (Kapı 1)

PyBullet Panda üzerinde analitik GVF ile enjekte edilmiş gecikme ve lag. Sinir ağı alanı ve world model
yok. Kurallar [PROTOKOL.md](PROTOKOL.md) içinde, sonradan yapılan değişiklikler "Sapmalar" bölümünde.

## Çalıştırma

    python test_se3.py
    python gate1.py && python analyze_gate.py > results/analysis.txt    # yaklaşık 1 saat, 9 işlem
    python gate1_t15.py                                                 # yaklaşık 15 dakika
    python inspect_gate.py; python inspect_sim.py; python inspect_p2.py; python inspect_t15.py
    python gate_rule.py && python analyze_rule.py > results/analysis_rule.txt    # yaklaşık 75 dakika

| Dosya | İş |
|---|---|
| `field_se3.py` | SE(3) geometrisi, referans, analitik GVF |
| `robot.py` | Panda, J† kontrol, gecikme ve lag, başarı ölçütleri |
| `gate1.py`, `analyze_gate.py` | Ön-kayıtlı ızgara ve karar kuralları |
| `gate1_t15.py` | Geçerlilik için `T = 15` kolu ve birleşik karar (Sapma 2) |
| `gate1g.py`, `analyze_g.py` | Geç bozucu deneyi ve karar kuralları |
| `gate_rule.py`, `analyze_rule.py` | Gecikme kuralının taze koşullarda sınanması |
| `inspect_*.py` | Keşifsel incelemeler; karara girmez |
| `holes_check.py`, `diag.py`, `pilot.py` | Delik yerleşimi ve ön denemeler |
| `audit_rule/` | Kural deneyinin bağımsız denetim betikleri; içlerindeki yollar geçici dizini gösterir |

`results/`: `analysis.txt`, `analysis_T15.txt` (karar), `inspect*.txt` (keşifsel), `analysis_v1.txt`
(eski yerleşim, Sapma 1).

## Sonuç

**Karar: 1a kaldı, 1b kaldı. Bu görevde sorun yok, world model bu görevde yapılmaz.**

| Ölçüm, R, c = 5 mm, `T ∈ {4, 8, 15}` | Değer | Eşik |
|---|---|---|
| Geçerlilik, `T = 15` makale SR'si, η = 5 / η = 0.5 | 1.00 / 0.81, aralıklar örtüşmüyor | geçti |
| 1a, en büyük düşüş | 0.00 | ≥ 0.10 |
| 1b, en iyi tek η | 8 | |
| 1b, en büyük / ortalama pişmanlık | 0.100 / 0.014 | ≥ 0.10 ve ≥ 0.03 |

`T = 4, 8`'de η = 3, 5, 8 ile 6000 koşuda hata yok. Bu koşular 200 bağımsız bozucudan geliyor, yani hata
oranı için üst sınır yaklaşık %1.8'dir. η = 5'te en kötü yanal hata 1.88 mm.

Gecikme uçurumları teoriyle uyumlu: başarı `ηh` 1.2 ile 1.5 arasında yıkılıyor (kararsızlık sınırı π/2).

## Geç bozucu ([PROTOKOL_GEC.md](PROTOKOL_GEC.md))

Bozucu ağızdan 0.5, 0.3, 0.2 s önce. 36.000 koşu: `gate1g.py`, `analyze_g.py`, `inspect_g.py`.

**Ön-kayıtlı sonuç: 2a ve 2b geçti, `M = 0.058` [0.045, 0.074], yani "Kapı 1 geçildi".
Yorum: bu pay büyük olasılıkla modele ait değil, kural biçiminden geliyor.**

| Politika, c = 5 mm, ayrılmış tohumlar | S |
|---|---|
| `SABİT`, η = 8 | 0.757 |
| `KURAL`, ön-kayıtlı `k ∈ {0.5, 1}` | 0.809 |
| `η = 0.6 / (h + τ)`, `T` kullanmaz, keşifsel | 0.840 |
| `TABLO`, her `(T, h, τ)` için ayrı | 0.867 |
| `KAHİN`, `Δ`'yı da bilir | 0.868 |

- `k = 0.6–0.9` ile `M ≈ 0.028`, eşiğin altında ama aralık eşiği içeriyor. Denetimin `η = s · η_max(h, τ)`
  kuralıyla `M = 0.010` [0.004, 0.021].
- `KAHİN − TABLO = 0.0003`: bozucu zamanını bilmek kazandırmıyor, `T` de çok az katkı veriyor.
- İkincil ölçütler kararsız: `c = 2 mm`'de kural yetiyor (`M = 0.021`), `c = 10 mm`'de 2b kalıyor.
- Başarısızlıkların yaklaşık %75'i süre yetmemesi, %11'i süren kararsızlık, %7'si sönümlenen salınım,
  %7'si ağız altına atlama (denetim, eşikler keşifsel).
- Bozucu ilerlemeyi de değiştirdiği için `T = 8`'de etkin `Δ` çok değişken (Sapma 3).

## Gecikme kuralı ([PROTOKOL_KURAL.md](PROTOKOL_KURAL.md))

`η = min(20, 0.6 / (h + τ))`, taze koşullarda 72.000 koşu: `gate_rule.py`, `analyze_rule.py`.

**Ön-kayıtlı sonuç: G ve B geçti, `M = 0.015`, `U = 0.023`, yani "kural doğrulandı, bu görevde η seçen model
gerekmiyor". Kapsamı dardır: `c` yaklaşık 3–7 mm, `U` eşiğe yakın.**

| Politika, c = 5 mm, test yarısı | S |
|---|---|
| `SABİT8`, η = 8 | 0.766 |
| `SABİT*`, η = 6.5 | 0.801 |
| `KURAL`, seçim yok | 0.850 |
| `TABLO`, her `(T, h, τ)` için ayrı | 0.864 |
| `KAHİN`, üst sınır | 0.870 |

- `KURAL − SABİT8` 0.083 [0.067, 0.101], `KURAL − SABİT*` 0.048 [0.027, 0.096], `M` [−0.006, 0.023].
- Hiç görülmemiş `T = 6`: kural 0.834, `SABİT8` 0.742, tablo 0.841.
- Her `(T, h, τ)` için en iyi η ile kuralın farkı, seçimsiz ve iyimser: 0.020. 1000 rastgele tohum bölmesinde
  `M` ortalama 0.017, en büyük 0.023. Tek delik çıkarılınca 0.011–0.018.
- Bootstrap yanlı (Sapma 3): düzeltilmiş `U ≈ 0.028`, pivot 0.036. Bu yüzden "pay küçük" sağlam, "pay dışlandı" değil.
- `c = 2 mm`: `M = 0.032`, yani kural yetmiyor. `c ≥ 8 mm`'de G kalıyor, tek η yetiyor. `c = 10 mm`'de kural
  η = 8'den az da olsa kötü (−0.008).
- Gerçek gecikmeler 20 ve 40 ms oldu, 15 ve 35 ms değil (Sapma 2). Etkin `h` ile `M = 0.018`, sonuç aynı.
- Koşuların %14.5'i hiçbir η'da başarılı değil, `Δ = 0.25`'te %26.6. Bunlar η ile düzelmiyor ve farkları sıkıştırıyor.

Bağımsız denetim karar değiştiren kusur bulmadı: skorlar ayrı kodla yeniden hesaplandı, 288 tek koşu ve 12 iş bit
düzeyinde aynı çıktı, seçimden teste sızıntı yok. Skor düzeyleri iyimser: test yarısı seçim yarısından kolay
(kural 0.850 / 0.794), rastgele bölmelerde `KURAL − SABİT8` ortalaması 0.073. `inspect_rule.py` bootstrap
yanlılığını ölçer.

## Kararı değiştirebilecek keşifsel bulgular

- **R sınırı.** `h ≤ 200 ms` ile 1a geçiyor (düşüş 0.92), ama 1b geçmiyor. 1b yalnız tüm ızgarada geçiyor
  (pişmanlık 0.68 / 0.055). Orada bile `T`'ye göre seçilen tek η pişmanlığı sıfırlıyor.
- **Sıkı tolerans.** 1a `c ≤ 1.5 mm`'de, 1b yalnız `c = 0.5 mm`'de geçiyor.
- **Alan hatası.** `m̂ = m + ρ‖m‖u(x)` ile ρ = 0.1'de η = 5, 8 her köşede 1.00; pencere ρ ≈ 0.5'te kapanıyor.
  Makalede FE 0.031–0.045, η = 0.5'te ME 0.128. Bunlar `‖ẋmax‖`'a göre, ρ ise yerel hıza göre tanımlı;
  ME η terimini de içeriyor. Karşılaştırma kabadır.

Düşük η'da SR'nin gecikmeyle artması kısmen zamanlamadandır: gecikmede robot geç kalktığı için `t` anındaki
bozucu yolun daha erken bir yerine denk gelir ve ağza kadar daha çok süre kalır. `η = 1, T = 8`: `h = 0`'da
0.86, bozucu 100 ms erken 0.93, `h = 100 ms`'de 1.00.

## Sınırlar

- Alan analitik: öğrenilmiş alanın gerçek `ε_c`, `ε_m` değerleri ölçülmedi.
- Temas benzetimi yok; motor ideal. Gerçek ivme limitiyle tek hücre denendi, SR 1.0.
- Şemsiye görevi yeniden kurgu; sayılar makaleyle birebir karşılaştırılamaz.
- Kural, `h + τ`'nun bilindiğini varsayar. Gerçek sistemde bu değerin kendisi ölçülmeli veya tahmin edilmelidir.
- Kural deneyinde yeni delik yok: seçim ve test aynı 5 delikte. Yeni deliklere genelleme bootstrap kadar güvenilir.
- R sınırı varsayımdır. Delik yerleşimi ilk sonuçlardan sonra değişti (Sapma 1) ve bu, 1a'nın sonucunu
  geçtiden kaldıya çevirdi. Pratik karar değişmedi.
