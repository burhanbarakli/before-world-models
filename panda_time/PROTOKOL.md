# Süre protokolü: konum bilgisi süreden ne kazandırıyor, modelsiz bir tahminci bunu alabiliyor mu?

2026-11-14 yazıldı, kod ve koşu yok. Pilot ve ana koşu kullanıcının onayını bekler.

## Neden

Temaslı deneyde (`panda_contact/README.md`) başarı açısından konum bilgisinin değeri küçüktü:
`W = +0.016 [0.002, 0.036]`, karar "model açılmaz". Ama varış süresi maddesi tetiklendi. `KAHİN` deliğe
`REFLEKS`'ten ortalama 1.66 s önce girdi (5.68 s ve 7.34 s). Protokol bu durumda hedefi süre olan ayrı bir protokol
istiyordu. Bu o protokoldür.

Bu farkın büyük kısmı kör spiralin kendisinden geliyor. Spiral başarı için ayarlanmıştı, süre için değil (yavaş spiral
daha iyi başarıyordu). Dolayısıyla soru "konumu bilmek süre kazandırır mı" değil, şudur:
**Konumu bilmek, modelsiz ve ucuz bir tahmincinin alamayacağı kadar süre kazandırıyor mu?**

İki gerçekçi durum var ve model için iki ayrı kapı açarlar:

- **A, tek atış:** her sokmada hata yenidir. Model ancak sokma sırasında, temastan konumu çıkararak yardım edebilir.
  Modelsiz rakip: kuvvet-moment ölçümünden temas noktasının yönünü bulup o yönde düz arama (`MOMENT`).
- **B, kalıcı hata:** hata bir kalibrasyon kaymasıdır, art arda sokmalarda aynı kalır, üstüne küçük bir sapma eklenir.
  Model ancak geçmiş denemelerden öğrenerek yardım edebilir. Modelsiz rakip: önceki başarılı sokmaların bulduğu
  kaymanın ortalaması (`HAFIZA`).

`KAHİN` her iki durumda üst sınırdır. Bir modelin yapabileceği en iyi şey `KAHİN` kadar iyi olmaktır. `KAHİN`
modelsiz rakibi eşik kadar geçemiyorsa, hiçbir model geçemez.

## Kurulum

`panda_contact/` benzetimi değişmeden kullanılır: `contact.py`, uyum iç döngüde (1000 Hz, `A = 4 mm/s/N`, 10 ms süzgeç),
24 kutulu tutucu, çubuk `r = 10 mm`, `F_max = 50 N`, başarı ölçütü, `tf = T + 8`, hız kapısı `L = .02`, gecikme kuralı
`η = min(20, .6/(h+τ))`, itme ölçeği .2, yükseklikle tetiklenen itme. Değişen tek şey politikalar ve B'nin dizi yapısı.

**Tohumlar yenidir:** ana koşu 200–219, pilot 910–914. Temaslı deney 100–119 ve 900 kullandı.

**Ekleme, ölçüm:** `REFLEKS`'in kullandığı süzülmüş kuvvete ek olarak, uca göre moment
`τ = Σ (p_i − p_uç) × F_i` aynı 20 ms süzgeçten ve gürültüyle geçer (`σ_τ = σ_F · r = 0.005 Nm`). Gerçek robotta bu,
bilinen takım geometrisiyle bilekteki kuvvet-moment algılayıcısından hesaplanır. Benzetim bu dönüşümü kusursuz sayar.

## Politikalar

Hepsi yalnız alan kaydırması `ŝ` üzerinden etki eder. Tetik bütün aramalarda aynıdır: kenara yakın
(`z − z_rim ≤ .02`) 5 tık boyunca `F_z ≥ F_t`. `ŝ`, uç kenarın 5 mm altına inince donar.

- **`KAHİN`:** `ŝ = e` (B'de o denemenin gerçek hatası, sapma dahil). Tetik gelirse `REFLEKS-H` spirali `e`'nin
  çevresinde çalışır. Serbest parametresi yoktur.
- **`REFLEKS-H`:** temaslı deneyin spirali, bu kez süre için ayarlanmış. Pilot hız `v_s ∈ {10, 20, 40} mm/s` ve adım
  `∈ {2c, 1.5c, c}` arasından ortalama süreyi en küçük yapanı seçer. Yarıçap sınırı 15 mm.
- **`MOMENT` (A'nın modelsiz rakibi):** tetikten sonra `n_w` tık boyunca süzülmüş kuvvet ve moment ortalanır. Temas
  noktası `r = (−τ_y / F_z, τ_x / F_z)`. Çubuk tabanının deliğe taşan kısmı yük taşımadığı için temas, deliğin ters
  tarafındadır, delik yönü `û = −r / |r|`. Sonra `ŝ` bu yönde `v_l` hızıyla düz ilerler, 15 mm'de durur ve oradan
  `REFLEKS-H` spirali başlar. `|r| < 2 mm` ise (simetrik temas, yön yok) doğrudan spirale geçer. Pilot
  `v_l ∈ {10, 20, 40} mm/s` ve `n_w ∈ {5, 10, 20}` arasından ortalama süreyi en küçük yapanı seçer.
- **`HAFIZA` (B'nin modelsiz rakibi):** dizinin ilk denemesi `MOMENT`'tir. Her başarılı denemenin sonunda, ucun yanal
  konumu eksi nominal delik, o denemenin kayma tahminidir. Sonraki denemede `ŝ` geçmiş tahminlerin ortalamasıdır,
  tetik gelirse `MOMENT` yine çalışır. Başarısız denemeler tahmin vermez. Serbest parametresi yoktur.

Pilot ayarı bilerek modelin aleyhinedir. Modelsiz rakipler en iyi hallerinde, `KAHİN` ayarsız.

## Koşullar

**A, tek atış:** modeller 0, 1, 2 (makale tarifi), `T ∈ {8, 4}`,
`(h, τ) ∈ {(20, 0), (40, 25), (90, 40)} ms`, itmesiz ve kenardan .25 s önce itmeli, `e ∈ {0, 3, 6, 10} mm` rastgele
yönde, `c ∈ {5, 2} mm`, 5 delik, 20 tohum. Politikalar `KAHİN`, `REFLEKS-H`, `MOMENT`. `e = 0`'da `KAHİN`
koşulmaz, `REFLEKS-H` ve `MOMENT` yalnız boş yere tetiklenme bedelini betimlemek için koşar. 79.200 koşu.

**B, kalıcı hata:** yalnız model 0 (temaslı deneyde öğrenme bedeli görünmedi), A'nın öteki eksenleri aynı,
`e ∈ {3, 6, 10} mm`. Her (delik, tohum) bir dizidir: `N = 5` deneme, `e` ve yönü dizi boyunca sabit, `μ` dizi boyunca
sabit, her denemede deliğe ayrıca `σ_j = 1 mm` (eksen başına Gauss) sapma ve yeni bir itme çekilir. Politikalar
`KAHİN` ve `HAFIZA`. 72.000 koşu.

Toplam 151.200 koşu. Temaslı deneyin hızıyla (2.5 s/koşu, 9 süreç) yaklaşık 11.7 saat.

## Ölçüt

Birincil ölçüt **ortalama varış süresi** `t`: çubuğun %90 derinliğe ilk ulaştığı an, başarısız koşular `tf = T + 8`
sayılır. Başarı ve süre böylece tek sayıda birleşir. Geçiş süresi bütün politikalarda aynı alan ve aynı `T` ile
olduğu için farklar arama süresidir. B'de `t`, beş denemenin ortalamasıdır.

Ortalama, birincil hücrelerin (model, `T`, gecikme, itme, `e > 0`, `c`, delik, tohum) eşit ağırlıklı ortalamasıdır.
İki `c` birlikte ortalanır, `c`'ye göre ayrı değerler de raporlanır.

## Karar

- `D_A = t(MOMENT) − t(KAHİN)`, `D_B = t(HAFIZA) − t(KAHİN)`, saniye.
- Bootstrap: A'da modeller, delikler ve tohumlar, B'de delikler ve tohumlar (diziler bütün olarak) yeniden örneklenir,
  2000 tekrar. İki test olduğu için aralıklar **%97.5** yüzdeliktir (Bonferroni). Ortalama kaydırması ve pivot da
  raporlanır, karar yüzdeliktedir.
- **Eşik `δ = 0.5 s`.** Gerekçe: `KAHİN`'in temaslı deneydeki süresinin yaklaşık %9'u ve tetiklenen maddenin
  (1 s) yarısı. Eşik bilerek düşük tutuldu: kapıyı açmak kolay olsun ki "açılmadı" sonucu güçlü olsun.

| Sonuç | Karar |
|---|---|
| G: `S(KAHİN) < 0.85` (A ya da B) | Geçersiz. Kurulum incelenir |
| `U < δ` | Bu durumda modelsiz rakip süre için de yetiyor. Model açılmaz |
| `D < δ ≤ U` | Küçük bir pay dışlanamıyor. Model açılmaz, yük modelindir |
| `D ≥ δ`, alt sınır `> 0` | Konum bilgisi modelsiz rakibin alamadığı süre bırakıyor. O durumun modeli aday olur |
| `D ≥ δ`, alt sınır `≤ 0` | Karar yok, raporlanır |

Her durum kendi kapısını açar. A geçerse aday, temas sırasındaki kuvvet-moment geçmişinden `ŝ` tahmin eden öğrenilmiş
bir tahmincidir. B geçerse aday, denemeler arası öğrenen bir modeldir. İkisi de ayrı bir protokolle, rakibi
`MOMENT` ya da `HAFIZA` olarak sınanır. World model ancak o protokolde de geçerse gündeme gelir.

**Betimsel, karara girmez:**

- `t(REFLEKS-H) − t(KAHİN)`: temaslı deneydeki 1.66 s'nin süre için ayarlanmış spiralle yeniden ölçümü.
- `t(MOMENT) − t(REFLEKS-H)`: yön bilgisinin değeri.
- Başarı oranları (`S`), politikalar arası `W` benzeri farklar, kuvvet aşımları.
- `MOMENT`'in yön hatası (açı) dağılımı, `e` ve `c`'ye göre.
- B'de deneme sırasına göre süre (1. deneme ve 2–5), `HAFIZA`'nın kayma tahmini hatası.
- `e = 0`'da boş yere tetiklenme: `REFLEKS-H` ve `MOMENT`'in `e = 0` süresi.
- `T`, gecikme, itme, `e`, `c`, `μ` dilimleri.

## Pilot

Tohumlar 910–914, analitik alan ve model 0, sonuçlar karar için kullanılmaz.

- **P1, moment yönü:** `e ∈ {6, 10} mm`, `c = 5`, itmesiz, 40 koşu. `MOMENT`'in tetikteki yön hatasının ortancası
  45°'den büyükse kod hatalı sayılır ve düzeltilir. Bu bir ayar değil, doğruluk denetimidir.
- **P2, hafıza tahmini:** başarılı sokmaların sonundaki kayma tahmininin hatası. Ortanca `c`'den büyükse kod
  hatalı sayılır.
- **P3, gerileme:** `REFLEKS-H` temaslı deneyin ayarıyla (`v_s = 10 mm/s`, adım `2c`) koşulunca, temaslı deneyin
  aynı tohumdaki sonuçlarını 1 mm içinde vermelidir. Moment eklemesi bir şeyi bozmadığını gösterir.
- **P4, ayar:** `REFLEKS-H` ve `MOMENT` ızgaraları `e ∈ {3, 6, 10}`, iki `c`, `T = 8`, `h = 20 ms`, itmeli ve itmesiz.
  Ortalama süreyi en küçük yapan seçilir, eşitlikte daha yavaş olan.
- **P5, süre:** koşu başına süre ölçülür. Toplam 14 saati geçerse B'nin tohumları 10'a iner. Bu tek önceden
  izin verilen küçültmedir.

Pilot bir ölçütte kalırsa ve protokol ne yapılacağını söylemiyorsa, karar "Sapmalar"a gerekçesiyle yazılır.

## Bilinen zayıflıklar

- Moment ölçümü benzetimde kusursuz geometriyle hesaplanır. Gerçek algılayıcıda kayma, takım kütlesi ve kablolar
  vardır. `MOMENT` gerçekte daha kötü olabilir, bu `D_A`'yı büyütür, yani modelin lehinedir ama benzetim bunu göstermez.
- Hata tek bir yatay kaymadır. Eğik delik, dönme hatası, değişken geometri yoktur. Modelin değeri bunlarda olabilir,
  bu deney göstermez.
- B'nin kalıcılık varsayımı (`σ_j = 1 mm`) seçilmiş bir değerdir. Sapma büyürse `HAFIZA` zayıflar.
- Süre ölçütü `tf`'ye bağlıdır: başarısızlığın bedeli `tf − t`'dir. Daha uzun `tf` başarısızlığı daha pahalı yapar.
- `δ = 0.5 s` keyfidir. Gerçek bir hat çevrim süresinden türetilmedi.
- PyBullet sert teması kabadır, `panda_contact` zayıflıkları aynen geçerlidir.

## Sapmalar

1. **P3 önce kaldı, iki nedenle; düzeltmeden sonra geçti (2026-11-15).**
   - Eski `contact.py`'nin 20 ms süzgeci 20 yerine 19'a bölüyordu (`panda_contact` Sapma 5). Yeni döngü doğru böler,
     kuvvetler eskisinden tam 20/19 düşük. Bu protokolde "değişmeden kullanılır" denen benzetimden tek bilinçli fark
     budur: doğru süzgeç. P3, eski `f_max` 19/20 ile ölçeklenince yeniden denendi: 20 koşuda en kötü `end_z` farkı
     0.40 mm, sonuçlar aynı, kuvvet farkı %0.13 → geçti.
   - Moment gürültüsü kuvvet gürültüsüyle aynı rastgele akıştan çekiliyordu, bu kuvvet gürültüsü dizisini kaydırıyordu.
     Moment gürültüsüne ayrı akış verildi. Aynı fonksiyonun iki kez koşulması da 0.4 mm'ye kadar fark veriyor
     (PyBullet'in geçmişe bağlılığı), P3'teki 1 mm eşiği bunu kapsıyor.
2. **P4'ten sonra kod değişti, P4 yeniden koşulmadı.** Gürültü akışının ayrılması ve moment hesabının hızlandırılması
   (aynı sayılar, 1.66 s yerine 1.15 s/koşu) P4'ten sonra yapıldı. Gürültünün dağılımı aynı, yalnız çekilişler farklı.
   `REFLEKS-H` seçimi açık farkla (9.53 s, sonraki 10.05 s), `MOMENT` seçimi küçük farkla (`n_w` 5: 8.37 s, 10: 8.41 s)
   yapıldı. Seçilen: `REFLEKS-H` `v_s = 20 mm/s`, adım `2c`; `MOMENT` `v_l = 10 mm/s`, `n_w = 5`.
3. **`MOMENT`'in yedek spirali `s0` çevresinde başlar.** Protokol "15 mm'de durur ve oradan spiral başlar" diyor;
   düz arama deliği geçmiş olacağı için spiral, başlangıç kaymasının (`MOMENT`'te 0, `HAFIZA`'da hatırlanan kayma)
   çevresinde başlatıldı. Bu bir yorumdur.
4. **P5: B'nin tohumları 10'a indi.** Pilotta 5.2 s/koşu ölçüldü (9 süreç, `T = 8`), A + B 21 saat. Hızlandırmadan
   sonra tahmin yaklaşık 14.7 saat, yine 14'ün üstünde. Önceden izin verilen tek küçültme uygulandı: B 200–209.
   A + B 115.200 koşu, tahminen 11 saat.
5. **Pilotun öteki sonuçları:** P1 geçti (40 koşu, yön her koşuda bulundu, açı hatası ortanca 1.9°, %90'ı 8.8°).
   P2 geçti (kayma tahmini hatası ortanca `c = 5`'te 2.84 mm, `c = 2`'de 1.14 mm). Ayar koşularında `MOMENT`
   ortalama süresi 8.37 s, `REFLEKS-H` 9.53 s oldu; bunlar pilot tohumlarıdır, karar için kullanılmaz.
6. **Süre tanımı protokolden saptı, denetim yakaladı, düzeltildi (2026-11-15, ana koşudan sonra).** Protokol
   "başarısız koşular `tf` sayılır" diyor. Çözümleyici `t_in`'i kullanıyordu: yalnız derinliğe hiç inmeyen koşular `tf`
   sayılıyordu, derine inip `F_max`'ı aşanlar gerçek varış süresini koruyordu (KAHİN'de %5.8, MOMENT'te %5.0). Protokol
   metni esastır; çözümleyici `ok` olmayan her koşuyu `tf` sayacak biçimde düzeltildi, eski tanımın sayıları da basılıyor.
   - A: `D_A` +1.336 → **+1.210 [1.041, 1.388]**, karar değişmedi (aday).
   - B: `D_B` +0.528 → **+0.450 [0.377, 0.535]**, karar **"aday"dan "küçük pay dışlanamıyor, model açılmaz"a** döndü.
   Aynı tanım hatası `panda_contact`'ın betimsel varış süresinde de var (1.66 s, düzeltilmiş 1.63 s); orada süre maddesi
   yine tetiklenir.
7. **P3'ün düzeltmeden sonraki geçişi** pilot dosyasına sonradan eklendi; ilk satırdaki FAIL ilk denemedir.
8. **Keşif, karara girmez: KAHİN ulaşılabilir bir sınır değil.** Protokol KAHİN'i "modelin yapabileceği en iyi şey"
   saydı. A'da KAHİN konumu temastan önce biliyor, B'de o denemenin sapmasını da biliyor. `explore_bound.py` iki
   ulaşılabilir sınır ölçtü (`results/explore_bound.txt`): DOKUN-KAHİN (A, model 0: `e`'yi ilk tetikten itibaren tam
   bilir) ve SABİT-KAHİN (B, tohum 200–204: kalıcı kaymayı tam bilir, sapmayı bilmez). Sonuçlar README'dedir.
