# s2_lasa: değişken η'nın LASA/S² üzerinde sınanması

Analitik GVF, sinir ağı alanı ve world model yok. Kurallar [PROTOKOL.md](PROTOKOL.md) içinde,
sonradan yapılan değişiklikler aynı dosyanın "Sapmalar" bölümünde.

## Çalıştırma

    ./run_all.sh <python>      # numpy, scipy, pyLasaDataset gerekir

| Dosya | İş |
|---|---|
| `gvf_s2.py` | S² geometrisi, GVF, rollout, DTW/Fréchet |
| `test_gvf.py` | Birim testler |
| `theory.py`, `t1b.py` | T1-T6 teori kontrolleri |
| `schedule.py`, `analyze.py` | Ön-kayıtlı çizelge deneyi ve karar kuralları |
| `explore.py` | Keşifsel varyantlar; karara girmez |

Sonuçlar `results/` altında: `analysis.txt`, `explore.txt`, `theory.json`, `t1b.json`, `schedule.npz`.

## Sonuç

Teori kontrolleri tuttu. Ön-kayıtlı çizelge kazancı **reddedildi**: ayrılmış demonstrasyon hedefinde
`F_letter`'a göre medyan kazanç `A` için −%5.3, `P` için %0; eşik %10'du. Döndürülmüş ayrımda ikisi de
yaklaşık sıfır. Pay kapısı 0.252 ile geçildi, ama tanıma duyarlı ve sınırda.

Kazanç hedefe bağlı: fazla yol cezasında `P` ve `A2` yaklaşık %40-55 kazanıyor (şekil başına en iyi,
betimsel), karesel takip cezasında sabit η yenilmiyor. Bu, deneyden önce yazılan analitik öngörüyle
uyumlu, ama `A`'nın η tabanı 1 iken öngörü tutmamıştı.

## Sınırlar

- Yalnızca analitik alan; öğrenilmiş alanın `ε_c`, `ε_m` değerleri ölçülmedi.
- Dinamik, gecikme ve lag çizelge deneyinde yok.
- Ayrılmış demolar referansa yakın başlıyor. Yörünge ortasındaki bozucu için veri tanımlı bir hedef yok.
- S²'ye eşleme ve zaman ölçeği makalede tam verilmediği için bizim seçimimiz.
