# Daha iyi elle yapılmış rakip: temas modelinin alabileceği süre kalıyor mu?

2026-11-15 yazıldı, ana koşudan önce. Kullanıcı "daha iyi rakibi sına" dedi.

## Neden

Süre deneyinde (`panda_time/README.md`) A durumunda `t(MOMENT) − t(KAHİN) = +1.21 s` çıktı, kural "model adayı" dedi.
Ama KAHİN deliği temastan önce biliyor, temas okuyan bir model bilemez. Keşifte DOKUN-KAHİN (deliğin yerini ilk
tetikten itibaren tam bilen) ölçüldü: farkın 0.64 s'si hiçbir temas modelinin alamayacağı bedel, alınabilir kısım
`t(MOMENT) − t(DOKUN) = +0.53 s [0.37, 0.67]`, neredeyse tamamı `c = 2, e = 10 mm` hücresinde. Denetim MOMENT'in üç
zayıflığını gösterdi: yolda yeniden nişan almıyor, uzaklık kestirmiyor, yedek spirali başlangıçta ve yalnız kısa
gecikmede ayarlı.

Soru: **Bu zayıflıkları gideren modelsiz bir rakip (MOMENT-2), DOKUN-KAHİN'e 0.5 s içinde yaklaşıyor mu?** Yaklaşırsa
temas sırasındaki konum tahmini için öğrenilmiş bir modelin alabileceği süre kalmamıştır.

Karşılaştırma bilgi üzerindedir: MOMENT-2 ve DOKUN-KAHİN tetikten sonra aynı mekanikle hareket eder (`ŝ` hedefe atlar,
aynı yedek spiral). Aralarındaki tek fark MOMENT-2'nin `e`'yi kestirmesi, DOKUN'un bilmesidir.

## Kurulum

`panda_time` benzetimi (`timesim.run_t`: doğru 20 ms süzgeç, uçta moment, ayrı moment gürültüsü) değişmeden.
Tek ekleme: `run_t`, politikanın bir `see(pos)` yöntemi varsa ona ucun konumunu her tıkta verir (robotun kendi
kinematiği; mevcut politikaların hiçbirinde yok, onları etkilemez). Görev A ile aynıdır: tek atış, hata her
koşuda yeni.

Tohumlar yenidir: ana koşu 300–319, pilot 920–924.

## Politikalar

Tetik, donma (`z < z_rim − 5 mm`) ve yedek spiral (adım `2c`, yarıçap sınırı 15 mm, hızı pilotta gecikmeye göre
ayarlanır) ikisinde aynıdır.

- **DOKUN-KAHİN (ulaşılabilir sınır):** tetiğe kadar `ŝ = 0`. Tetikte `ŝ = e` (atlama). Sonra yeniden tetiklenirse `e`
  çevresinde yedek spiral. `panda_time/explore_bound.py`'deki tanımın aynısı, yalnız yedek spiral hızı ayarlı.
- **MOMENT-2 (rakip):**
  1. Tetikten sonra `n_w` tık kuvvet ve moment ortalanır. Temas noktası `r = (−τ_y/F_z, τ_x/F_z)`, yön `û = −r/|r|`,
     uzaklık `d̂ = a_c + b_c |r|` (pilotta ölçülen kalibrasyon, `[0, 15 mm]`'ye kırpılır).
  2. Hedef, ucun o anki yanal konumuna (nominal deliğe göre) göre: `ŝ = p_uç − h_nom + d̂ û` (atlama).
  3. **Yeniden nişan:** uç oturunca (yanal hızı 5 tık boyunca 2 mm/s'nin altında ya da 0.5 s geçti) ve hâlâ kenarın
     üstünde bastırıyorsa (`F_z ≥ F_t`) 2. adım yeni ölçümle tekrarlanır. `|r| < 2 mm` ise yön yok demektir.
  4. **Yerel yedek:** 4 yeniden nişandan sonra ya da yön yoksa, o anki `ŝ` çevresinde yedek spiral.
  Kalibrasyon pilotta zayıf çıkarsa (aşağıda P1) uzaklık yerine sabit adım `d̂ = c` kullanılır.

Betimsel olarak, yalnız model 0'da, KAHİN ve MOMENT (`panda_time`'daki gibi) de koşulur.

## Koşullar

Modeller 0, 1, 2; `T ∈ {8, 4}`; `(h, τ) ∈ {(20, 0), (40, 25), (90, 40)} ms`; itmesiz ve .25 s önce itmeli;
`e ∈ {3, 6, 10} mm`; `c ∈ {5, 2} mm`; 5 delik; 20 tohum. DOKUN-KAHİN ve MOMENT-2 bütün ızgarada (43.200 koşu).
Model 0'da KAHİN ve MOMENT (14.400) ve MOMENT-2'nin `e = 0` koşuları (boş yere tetiklenme, 1.200). Toplam 58.800,
tahminen 6–7 saat.

## Ölçüt ve karar

Ölçüt `panda_time` ile aynı: ortalama varış süresi, **`ok` olmayan her koşu `tf = T + 8`** (protokol metni, kod da
böyle). Ortalama birincil hücrelerin (model, `T`, gecikme, itme, `e > 0`, `c`, delik, tohum) eşit ağırlıklı ortalaması.

`D2 = t(MOMENT-2) − t(DOKUN-KAHİN)`. Bootstrap modeller, delikler, tohumlar, 2000 tekrar, **%95** yüzdelik (tek test).
Ortalama kaydırması ve pivot da raporlanır. Eşik `δ = 0.5 s` (`panda_time` ile aynı).

| Sonuç | Karar |
|---|---|
| `S(DOKUN-KAHİN) < 0.85` | Geçersiz, sınır politikası incelenir |
| `U < δ` | Elle yapılmış rakip yetiyor. Temas sırasında konum tahmini için model açılmaz |
| `D2 < δ ≤ U` | Küçük bir pay dışlanamıyor. Model açılmaz, yük modelindir |
| `D2 ≥ δ`, alt sınır `> 0` | Bilgi farkı kalıyor. Öğrenilmiş tahminci ayrı protokolle, rakibi MOMENT-2 |
| `D2 ≥ δ`, alt sınır `≤ 0` | Karar yok, raporlanır |

Son satır bile world model'i doğrudan açmaz; önce kuvvet-moment geçmişinden `e` kestiren küçük bir öğrenilmiş
tahminci MOMENT-2'ye karşı sınanır.

**Betimsel:** `c` ve `e`'ye göre `D2` (özellikle `c = 2, e = 10`); model 0'da `t(MOMENT) − t(MOMENT-2)` (iyileşme) ve
`t(DOKUN) − t(KAHİN)` (ulaşılamaz bedel, yeni tohumlarla); MOMENT-2'nin yeniden nişan sayısı, ilk ve son kestirim
hatası; başarı oranları; gecikme, itme, `μ` dilimleri; `e = 0`'da boş yere tetiklenme bedeli.

## Pilot

Tohumlar 920–924, analitik alan ve model 0, karar için kullanılmaz.

- **P1, uzaklık kalibrasyonu:** `e ∈ {4, 6, 8, 10} mm`, iki `c`, itmesiz, `T = 8`, `h = 20 ms`; ilk ölçümdeki `|r|`
  ile gerçek uzaklık. Her `c` için `d = a_c + b_c |r|` en küçük kareler. `R² < 0.5` ya da `b_c ≤ 0` ise o `c` için
  sabit adım `d̂ = c`.
- **P2, gerileme:** DOKUN-KAHİN `panda_time`'ın spiral ayarıyla koşulunca, `explore_bound`'un aynı tohumdaki
  sonucunu 1 mm içinde ve aynı başarıyla vermeli (`see` eklemesinin bir şey bozmadığını gösterir).
- **P3, ayar:** her gecikme için yedek spiral hızı `v_s ∈ {5, 10, 20} mm/s` ve `n_w ∈ {5, 10}`, MOMENT-2 üzerinde,
  `e ∈ {3, 6, 10}`, iki `c`, itmeli ve itmesiz, `T = 8`. Ortalama süreyi en küçük yapan seçilir (0.01 s içinde
  eşitlikte daha yavaş olan). DOKUN-KAHİN aynı spiral hızlarını kullanır. Ayar bilerek rakibin lehine.
- **P4, süre:** koşu başına süre. Toplam 12 saati geçerse betimsel KAHİN ve MOMENT koşuları 10 tohuma iner.

## Bilinen zayıflıklar

- DOKUN-KAHİN kesin bir üst sınır değil: tam bilgili daha akıllı bir hareket (kaldırıp taşıma gibi) daha hızlı olabilir.
  Ama MOMENT-2 de aynı mekaniği kullandığı için `D2` yalnız bilgi farkını ölçer; mekaniğin iyileşmesi ikisini de
  hızlandırır.
- Kalibrasyon pilot verisinden iki sayıdır; gerçek robotta yeniden ölçülmesi gerekir.
- Moment ölçümü benzetimde kusursuz geometriyle. Gerçek algılayıcıda MOMENT-2 daha kötü olabilir, bu modelin
  lehinedir ve benzetim göstermez.
- Hata tek yatay kayma. Eğik delik, dönme hatası yok.
- `δ = 0.5 s` keyfi.

## Sapmalar

1. **P1'deki işaret koşulu düşürüldü; MOMENT-2 kalibrasyonlu, kayıtlı hâli MOMENT-2F olarak ayrıca koşuldu.**
   P1 (`results/pilot_rival_1.txt`) güçlü ama ters işaretli bir ilişki buldu:
   - `c = 5`: `d = 15.31 mm − 0.975 |r|`, R² 0.97, ortanca hata 0.20 mm.
   - `c = 2`: `d = 13.60 mm − 1.223 |r|`, R² 0.94, ortanca hata 0.39 mm.

   Uç delikten uzaklaştıkça yüzünün daha büyük kısmı kenara oturur ve temas ağırlık merkezi uca yaklaşır. Kayıtlı
   kural `b_c ≤ 0` olunca sabit adımı zorunlu tutuyordu. Bu koşul yanlış bir işaret tahminine dayanıyordu; kuralın
   amacı "kalibrasyon zayıfsa geri çekil" idi (`R² < 0.5`). Sabit adım, rakibi bilerek zayıflatırdı ve "ayar bilerek
   rakibin lehine" ilkesine aykırıydı.

   Ana koşudan önce, pilot tohumlarıyla şunlar yapıldı:
   - Koşul `b_c ≠ 0` oldu.
   - P1 ve P3 kalibrasyonlu MOMENT-2 için yeniden koşuldu (`pilot_rival2.py`, `results/pilot_rival2.txt`). Seçilen
     ayar: `v_s = [10, 10, 5] mm/s`, `n_w = 5`. DOKUN-KAHİN aynı `v_s`'yi kullanır.
   - Kararı kalibrasyonlu MOMENT-2 verir.
   - Kayıtlı (sabit adımlı) hâl **MOMENT-2F** adıyla bütün ızgarada koşuldu. Ayarı ilk pilotun P3'ünden:
     `v_s = 10 mm/s`, `n_w = 5`. Analiz kayıtlı kurala göre sonucu da yazar ("as registered").

   Koşu sayısı 58.800'den 81.600'e çıktı. P4 kayıtlı ızgarada geçmişti (8.8 saat), betimsel koşular 20 tohumda kaldı.
2. **`R_MIN = 2 mm` (yön yok eşiği) bilerek değiştirilmedi.** Kayıt testinde (tohumlar 300–301, yalnız kaydetmeyi
   sınamak için) delik 1'de `e = 10, c = 2` için ilk `|r|` 2 mm'nin altında kaldı. MOMENT-2 doğrudan spirale düştü
   (8.7 s; öteki 8 koşuda DOKUN'a 0.1–0.2 s yakındı). Ters işaret yüzünden küçük `|r|` "merkezde" değil "uzakta"
   demektir, yani eşik bu rakip için kötü seçilmiş olabilir. Yine de protokolde yazılı olduğu ve bu gözlem ana
   tohumlardan geldiği için dokunulmadı. Sonuç "bilgi farkı" çıkarsa, öğrenilmiş tahminci protokolünden önce bu eşiğin
   farkı kapatıp kapatmadığına bakılmalıdır.
3. **İlk ana koşu kayboldu, baştan koşuldu.** 2026-11-16 sabahı başlayan koşu, oturum kapanınca 790/816 işte durdu.
   `rival.py` veriyi yalnız sonda yazdığı için hiçbir şey kalmadı; o koşudan sonuç görülmedi. `main` artık her işten
   sonra bir ara dosyaya yazar (`results/rival.npz.partial.pkl`) ve yeniden başlatılınca kaldığı yerden sürer. Koşu
   oturumdan bağımsız (`nohup`) yeniden başlatıldı. Tasarım, tohumlar ve ayar aynı. Yalnız PyBullet'in süreç geçmişine
   bağlılığı yüzünden tek tek koşular ilk denemeden biraz ayrılabilir. Bu fark konumda ≤ 0.4 mm, ama denetime göre
   (Sapma 4c) varış süresinde koşu başına 1.4 s'ye kadar çıkabiliyor.
4. **Denetim bulguları (2026-11-17, bağımsız ajan; kod ve veri verildi, sonuç verilmedi).** D2 `+0.247` ve aralığı
   kendi koduyla yeniden hesaplandı, aynı çıktı. Kararı değiştiren kusur yok.
   - a. **MOMENT-2F tam "kayıtlı" değil.** Kayıtlı kurala göre DOKUN, MOMENT-2F'nin ayarıyla aynı spiral hızını
     (130 ms'de 10 mm/s) kullanmalıydı. Kodda DOKUN, MOMENT-2'nin ayarını kullanıyor (130 ms'de 5 mm/s). Denetim,
     en zor hücrelerde DOKUN'u 10 mm/s ile koştu: 0.056 s daha yavaş. Izgaraya yayınca D2F yaklaşık 0.01 s küçülür
     (1.317 → ~1.31). "Kayıtlı" sonuç değişmez.
   - b. **`N_AIM` bir eksik olabilir.** Protokol "4 yeniden nişandan sonra" diyor (toplam 5 nişan). Kod toplam 4 nişana
     izin veriyor. 4 nişanı dolduran koşular %5.9, D2'ye katkıları +0.055 s. Beşinci nişan U = 0.317'yi 0.5'in üstüne
     taşıyamaz.
   - c. **Tekrarlanabilirlik.** Saklı koşular yeniden koşulunca DOKUN aynı çıktı. MOMENT-2'de 120 koşudan 6'sı 0.05 s'den
     fazla ayrıldı, hepsi `c = 2, e = 10` hücresinde; aynı koşu üç kez 9.15 / 9.77 / 9.68 s verdi. Hücre ortalamaları
     ≤ 0.07 s, D2 ≈ 0.01 s oynuyor.
   - d. **Analiz düzeltmeleri, karar satırı etkilenmedi.**
     - `e = 0` satırı yanlış karşılaştırma öneriyordu. Doğrusu KAHİN'in `e = 3` koşuları: ikisi de `ŝ = e` ile
       başlar. Boş yere tetiklenme bedeli her iki `c`'de +0.033 s.
     - Protokoldeki `μ` dilimleri eksikti, eklendi.
     - D2'nin kaynağı eklendi: yön yokken doğrudan spirale düşen koşular ve nişanları biten koşular.
   - e. **Yöntem notları.**
     - P1, `e`'yi (nominal delikten uzaklık) `|r|`'ye karşı oturtuyor. Politika ise `d̂`'yi o anki uçtan deliğe
       uzaklık olarak kullanıyor. Bu ikisi yalnız ilk nişanda, uç nominal konumdayken çakışır.
     - P3'teki 0.01 s eşitlikleri yuvarlanmış çıktılardan karara bağlandı; yuvarlanmamış puanlar saklanmadı.
     - `n_w` eşitliğinde küçük olanı seçme kuralı protokolde yoktu.
     - Koşu 12.4 saat sürdü. P4 pilot tahminine uygulanır ve geçmişti.
