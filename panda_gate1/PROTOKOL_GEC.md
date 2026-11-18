# Geç bozucu ön-kayıt protokolü

Sonuçlar görülmeden önce yazıldı (2026-10-31). Sonraki değişiklikler "Sapmalar" bölümüne işlenir.

Kurulum, ölçütler ve R, [PROTOKOL.md](PROTOKOL.md) ile aynıdır. Fark yalnız bozucunun zamanıdır.

Görülmüş olan: Kapı 1 sonuçları ve denetçinin keşif ölçümü (4 köşe hücre, hücre başına 20 koşu,
η ∈ {3, 5, 8, 12}, en büyük pişmanlık 0.30–0.70). Bu ölçüm hipotezi doğurdu, kanıtı sayılmaz.

Soru: bozucu ağza yakın gelince tek η yetmiyorsa, `(T, h, τ)`'dan η seçen bir modelin basit analitik
kuralın üstüne katacağı pay var mı?

## Deney

- `T ∈ {8, 4}`, `h ∈ {0, 10, 20, 50, 100} ms`, `τ ∈ {0, 50} ms`, yani R.
- `Δ ∈ {0.5, 0.3, 0.2} s`. Bozucu anı `t_d = t_rim + h + τ − Δ`; `t_rim` referansın ağzı geçtiği an.
  Ölçek 0.2, yön rastgele (`D2` ile aynı dağılım), sağdan.
- `η ∈ {2, 3, 5, 8, 12, 20}`. 0.5 ve 1 çıkarıldı, çünkü Kapı 1'de `T = 4`'te bozucu geç gelmeden de
  düşüyorlardı. Bu, en iyi hücre değerini düşürebilir, yükseltemez.
- Delik başına 20 tohum, hücre başına 100 koşu. Aynı tohum aynı yönü verir, `Δ` ve η arasında eşlidir.
- `tf = T + 4 s`. Başarı aynı: birincil `SR_insert(c = 5 mm)`, ikincil `c = 2, 10 mm`.

## Geçerlilik

`h = 0, τ = 0` için en az bir `(T, Δ)` hücresinde `SR(en iyi η) − SR(η = 2) ≥ 0.30` olmalı. Tutmazsa
geç bozucu görevi zorlamıyor demektir, kapı kapanır.

## Karar kuralları

Bütün hücrelerde (`T, h, τ, Δ`), bütün tohumlarla:

- **2a:** en iyi sabit η'nın SR'si, aynı `(T, Δ)` için `h = 0, τ = 0` en iyisinden en az 0.10 düşük ve
  Wilson aralıkları örtüşmüyor.
- **2b:** `η_rob`, ortalama SR'yi en yükselten tek η. En büyük pişmanlık `≥ 0.10` **ve** ortalama pişmanlık
  `≥ 0.03`.

## Politikalar

Kontrolcü bozucunun ne zaman geleceğini bilemez, bu yüzden hiçbir politika `Δ` görmez. Seçimler 0–9
numaralı tohumlarda yapılır, skor 10–19 numaralı tohumlarda ölçülür (hücre başına 50 koşu).

| Politika | η |
|---|---|
| `SABİT` | `η_rob`, bütün koşullarda aynı |
| `KURAL` | `min(η_ideal(T), k / (h + τ))`, log ölçekte en yakın ızgara değeri; `k ∈ {0.5, 1}` seçim yarısında belirlenir |
| `TABLO` | her `(T, h, τ)` için seçim yarısında ortalama SR'si en yüksek η |
| `KAHİN` | her hücrede o hücrenin en iyisi, `Δ`'yı da bilir; yalnızca üst sınır |

`η_ideal(T)`: `h = 0, τ = 0`'da `Δ`'lar üzerinden ortalama SR'yi en yükselten η, eşitlikte en küçüğü.

`TABLO`, `(T, h, τ)`'yı gören herhangi bir η seçicisinin, örneğin bir world model'in, bu görevde ulaşabileceği
pratik tavandır; 20 koşul için ayrı ayrı seçer ve bir model bundan daha iyi genelleyemez. Hücre başına düşen
gürültü onu aşağı çekebilir, bu yüzden `KAHİN` farkı da raporlanır.

Test yarısında ortalama SR: `S(politika)`. **Model payı** `M = S(TABLO) − S(KURAL)`.

## Sonuçların anlamı

| Sonuç | Karar |
|---|---|
| 2b kaldı | Geç bozucuda da tek η yetiyor. Bu benchmark'ta model fikri kapanır |
| 2b geçti, `S(KURAL) − S(SABİT)` pişmanlığı en az yarıya indiriyor ve `M < 0.03` | Seçim gerekli ama analitik kural yeterli. Model gerekmiyor |
| 2b geçti, `M < 0.03`, kural yarıya indiremiyor | Seçimden kazanılacak pay yok. Model gerekmiyor |
| 2b geçti, `M ≥ 0.03` | Kuralın üstünde pay var. Kapı 1 geçildi, Kapı 2 için kullanıcı kararı gerekir |

"Pişmanlığı yarıya indirme": test yarısında `KAHİN`'e göre ortalama pişmanlık, `KURAL` için `SABİT`'in
yarısından küçük veya eşit.

`M` için eşleştirilmiş bootstrap aralığı (delik × tohum üzerinden, 2000 tekrar) raporlanır.

## Sapmalar

1. **Bozucu zamanı değişti, sonuçlar görülmeden.** Yukarıdaki `t_d = t_rim + h + τ − Δ` yanlıştı. Bozucusuz
   pilot: `T = 8, h = 100, τ = 50`'de referans 6.06 s, öngörü 6.21 s, ölçülen 6.40–6.42 s; yani gecikmeli
   hücrelere yaklaşık 0.2 s fazladan süre veriyordu. Yeni tanım: `t_d = t_rim − Δ`, `t_rim` aynı
   `(T, h, τ, η, delik)` için bozucusuz koşuda çubuk ucunun ağzı ilk geçtiği an. Geçmezse eski formül
   kullanılır. Denetçinin keşif sayıları eski hizalamayla ölçüldü, dolayısıyla karşılaştırılabilir değildir.
2. **`analyze_g.py` sahte veriyle sınandı.** Tamamen gürültü olan veride 2b geçiyor (0.21 / 0.062), çünkü
   hücre başına en iyi η yukarı yanlıdır; `M` ise −0.017 çıkıyor. Bu yüzden karar `M` üstünden verilir ve
   2b tek başına kanıt sayılmaz. Kurallar değişmedi.
3. **Denetimde bulundu, sonuçlar görüldükten sonra: `Δ` tam denetlenemiyor.** Bozucu ilerlemeyi de değiştirdiği
   için etkin `Δ`'nın standart sapması `T = 8`'de 0.16–0.17 s, `T = 4`'te 0.08 s. `T = 8, Δ = 0.2`'de koşuların
   %18.2'si doğrudan ağız altına atlıyor; bu, o hücrelerdeki 0.76 tavanını büyük ölçüde açıklıyor. η ve
   gecikme arasında yanlılık ihmal edilebilir (hücre ortalaması sapması ≤ 0.022 s, kararsız η = 20 hariç).
   Deney yeniden koşulmadı, karar kuralları değişmedi.
4. **Keşifsel, karara girmez.** `inspect_g.py`, `k` ızgarasını sonuçlar görüldükten sonra genişletti.
   `η = k / (h + τ)`, `T` kullanmadan, `k = 0.6`: test yarısında `S = 0.840`, `M = 0.027` [0.017, 0.039].
