# Gecikme kuralı doğrulama protokolü

Sonuçlar görülmeden önce yazıldı (2026-10-31). Sonraki değişiklikler "Sapmalar" bölümüne işlenir.

Kurulum ve başarı ölçütleri [PROTOKOL.md](PROTOKOL.md), bozucu zamanı [PROTOKOL_GEC.md](PROTOKOL_GEC.md)
Sapma 1 ile aynıdır (`t_d = t_rim − Δ`, `t_rim` bozucusuz koşuda ölçülür).

Görülmüş olan: `analysis_g.txt` ve `inspect_g.txt`. Oradaki keşif şunu önerdi; burada sınanan iddia budur:

    η = min(20, 0.6 / (h + τ))

`k = 0.6` ve tavan 20 bu deneyde **ayarlanmaz**. Kural `T`, `Δ` ve delik bilgisi kullanmaz, η yuvarlanmaz.

Soru: bu kural görülmemiş koşullarda sabit η'yı yeniyor mu, ve koşul başına ayrı seçim yapan bir tablonun
üstünde kayda değer pay bırakıyor mu?

## Taze koşullar

Hiçbir `(h, τ)`, `Δ`, delik veya tohum önceki deneylerde kullanılmadı. Gecikmeler R içindedir.

- `h ∈ {15, 35, 70, 90} ms`, `τ ∈ {0, 25, 40} ms`.
- `T ∈ {8, 6, 4}`; `T = 6` hiç görülmedi.
- `Δ ∈ {0.4, 0.25} s`. Ölçek 0.2, yön `D2` ile aynı dağılımdan, yeni tohum akışı.
- Delikler: `(.40, −.12), (.44, −.04), (.44, .04), (.40, .12), (.36, −.08)`. Yalnız kinematik paya göre seçildi
  (σ_min ≥ 0.12, eklem payı ≥ 0.63), adaylar listesinin ilk beşi; başarıya bakılmadı.
- Sabit η ızgarası `{3, 4, 5, 6.5, 8, 10, 12, 16, 20}`. Önceki ızgaradan sıktır, böylece sürekli η kullanan
  kural ızgara kabalığından haksız üstünlük almaz.
- Delik başına 20 tohum, hücre ve η başına 100 koşu; toplam 72.000 koşu. `tf = T + 4 s`.
- Birincil ölçüt `SR_insert(c = 5 mm)`, ikincil `c = 2, 10 mm`.

## Politikalar

Tohum 0–9 seçim, 10–19 test yarısıdır. Bütün skorlar test yarısındadır. Hiçbir politika `Δ` görmez.

| Politika | Tanım |
|---|---|
| `KURAL` | yukarıdaki formül, seçim yok |
| `SABİT8` | η = 8; önceki deneyin `η_rob`'u, önceden sabit |
| `SABİT*` | seçim yarısında en iyi tek η |
| `TABLO` | her `(T, h, τ)` için seçim yarısında en iyi ızgara η'sı |
| `KAHİN` | her hücrede test yarısının en iyisi; yalnız üst sınır, iyimser yanlı |

## Karar

Bootstrap: delikler, seçim tohumları ve test tohumları yeniden örneklenir, `SABİT*` ve `TABLO` her tekrarda
yeniden seçilir, 2000 tekrar, %95 yüzdelik aralık. Önceki `M` aralığı seçim belirsizliğini içermiyordu.

- **G, geçerlilik:** `S(KAHİN) − S(SABİT8) ≥ 0.03`. Tutmazsa koşullar seçimi gerektirmiyor, deney sonuçsuzdur.
- **B, üstünlük:** `S(KURAL) − max(S(SABİT8), S(SABİT*))`'nin aralığının alt sınırı `> 0`. Fark, iki sabit
  politikaya karşı ayrı ayrı hesaplanır, ikisinde de geçmelidir.
- **Y, yeterlilik:** `M = S(TABLO) − S(KURAL)`, aralığın üst sınırı `U`.

| Sonuç | Karar |
|---|---|
| G kaldı | Sonuçsuz. Bu koşullarda tek η yetiyor |
| B kaldı | Kural doğrulanmadı |
| B geçti, `M ≥ 0.03` | Kural yardımcı ama yetmiyor. Model payı açık kalır |
| B geçti, `M < 0.03 ≤ U` | Kural destekleniyor, küçük bir pay dışlanamıyor |
| B geçti, `U < 0.03` | Kural doğrulandı. Bu görevde η seçen model gerekmiyor |

Betimsel olarak raporlanır, karara girmez: `T`, `Δ` ve `h + τ` dilimleri, `c = 2, 10 mm`, seçim ve test
yarılarının yer değiştirdiği `M`.

## Sapmalar

1. **`analyze_rule.py` deney öncesi sahte veriyle sınandı, kurallar değişmedi.** Bilinen cevaplı üç durumda
   doğru sonuç verdi: kural üstünse "doğrulandı", yapı yoksa ve tablo gerçekten üstünse "doğrulanmadı".
   Saf gürültüde G yine de geçiyor, çünkü `KAHİN` yukarı yanlıdır. G tek başına kanıt sayılmaz.
2. **`h = 15, 35 ms` koşulmadı.** `robot.run` gecikmeyi 100 Hz adıma yuvarlıyor, gerçek değerler 20 ve 40 ms oldu.
   Deney öncesi fark edilmedi. Böylece (20, 0) yerleşimi `T = 8, 4`'te önceki deneyde görülmüştü, "hiçbir (h, τ)
   kullanılmadı" cümlesi yanlıştır. Kural nominal `h` aldığı için 12 `(h, τ)` çiftinin 5'inde η %7–14 yüksek
   kaldı. Etkin `h` ile kuralın yeniden koşulması: S 0.847, `M` 0.018 [−0.004, 0.026], sonuç değişmedi.
   `τ` için aynı tür etki var: Euler lag ile 25 ve 40 ms etkin 19.6 ve 34.8 ms (PROTOKOL.md Sapma 3).
3. **Yüzdelik bootstrap üst sınırı aşağı yanlı.** Tohumları iadeli çekmek seçim kümesini küçültür, `TABLO` ve
   `SABİT*` zayıflar: bootstrap ortalaması `M` 0.010, nokta 0.015. Kural önceden yüzdelik yöntemi sabitlediği için
   karar `U = 0.023` ile verildi. Yanlılık çıkarılınca `U ≈ 0.028`, pivot bootstrap ile 0.036. İkincisi ön-kayıtlı
   çözümleme değildir ama "küçük pay dışlandı" iddiasının zayıf olduğunu gösterir.
4. **Delik listesi izlenemiyor.** "Adaylar listesinin ilk beşi" listesi depoda yok. Kinematik paylar yeniden
   hesaplandı ve doğrulandı, seçimin sırası doğrulanamadı.
