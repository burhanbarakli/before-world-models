# Yeniden sıfırlayan rakip: algılayıcı farkını bir el kuralı kapatıyor mu?

Bu protokol ana koşudan önce yazıldı. Sonradan yapılan her değişiklik sonda "Sapmalar" altına yazılır.

## Neden

Algılayıcı deneyi (`../panda_sensor`) kayıtlı kurala göre her düzeyde "bilgi farkı" verdi. MOMENT-2R'nin
DOKUN-KAHİN'e göre farkı:
- S1 +1.68 s
- S2 +3.15 s
- S3 +4.00 s

Denetim ve keşif şunu gösterdi:
- Kalan hatalar arasında baskın olan, koşu başına sabit sapma.
- Sapma pilotta kalibrasyonu düşürüyor ve rakip sabit adıma geçiyor.
- Benzetimde temastan önce gerçek kuvvet sıfır. Boşta okunan değer bu yüzden sapmanın kendisi.

Temastan hemen önce yeniden sıfırlayan bir rakip, kayıtlı olmayan bir sınamada S1 farkını +0.20 s'ye indirdi. O
sınama yalnız model 0'da, tohum 400–409'da yapılmıştı.

Algılayıcı protokolü kendisi de şunu söylüyordu: öğrenilmiş tahminciden önce başka bir elle yapılmış kural
sınanmalı. Bu protokol o sınamadır.

## Fiziksel varsayım (açık soru)

Benzetimde sapma koşu boyunca sabit, kayma yok. Yeniden sıfırlama bu yüzden sapmayı neredeyse tamamen siler.
- Gerçek algılayıcıda sapma görevin başındaki sıfırlamadan sonra birikiyorsa, temastan hemen önce yeniden
  sıfırlamak sıradan iyi uygulamadır. Bu deneyin sonucu o durumda geçerlidir.
- S1'deki 0.1 N temastan hemen önce de kalıyorsa (ölçüm yapılan sürede kayma ya da histerezis), bu deney benzetimin
  basitleştirmesini sömürür. O durumda algılayıcı deneyinin kayıtlı sonucu geçerli kalır.

Bu deney o soruyu yanıtlamaz, yalnız yanıtın neye bağlı olduğunu gösterir.

## Politikalar

- **DOKUN-KAHİN**: algılayıcı deneyindekiyle aynı. Tetik ham ölçülen `F_z` ile çalışır.
- **MOMENT-2R**: algılayıcı deneyindekiyle aynı (sabit adım, `n_w = 5`, `R_MIN` S1 1 / S2 4 / S3 2 mm).
- **TARE**: MOMENT-2R'nin yeniden sıfırlayan hâli.
  - Boşta (`idle`) ve uç kenarın 3 mm'den fazla üstündeyken son 30 tıkın (0.3 s) kuvvet ve moment ortalaması
    tutulur.
  - Bu ortalama, tetikten sonra her ölçümden çıkarılır.
  - Tetik ham `F_z` ile çalışır, DOKUN-KAHİN'inki gibi. Fark yalnız kestirimde.
  - Kalibrasyon P1'de yeniden ölçülür. `n_w = 5`, `R_MIN = 2 mm`, ayar yok.

## Koşullar

Algılayıcı deneyiyle aynı:
- S1, S2, S3
- modeller 0–2
- `T = 8`, itmesiz
- 3 gecikme
- `e ∈ {3, 6, 10} mm`, `c ∈ {5, 2} mm`
- 5 delik

**Kullanıcının isteğiyle yalnız 2 tohum:** 500–501, hiç kullanılmamış. Üç politika aynı tohumlarda yeniden koşulur.
Toplam 3 × 3 × 3 × 3 × 2 × 3 × 5 × 2 = 4.860 koşu, tahminen 1 saat. Hücre başına 10 koşu var; algılayıcı
deneyinde 100'dü.

## Ölçüt ve karar

- Düzey başına `DT = t(TARE) − t(DOKUN-KAHİN)`. Ortalama varış süresi; başarısız koşu `T + 8 = 16 s` sayılır.
- Bootstrap: modeller × delikler × tohumlar, 2000 tekrar, %98.33 yüzdelik aralık (üç düzey, Bonferroni).
- Karar işlevi algılayıcı deneyiyle aynı (`δ = 0.5 s`, geçerlilik S(DOKUN) ≥ 0.85):
  - `üst < δ`: el kuralı yetiyor;
  - `DT < δ`: küçük pay dışlanamıyor;
  - `alt > 0`: bilgi farkı;
  - değilse karar yok.

**Tohum sayısı az olduğu için tohum ekseni bootstrap'ta zayıf.** İki tohumdan yeniden örnekleme, belirsizliği
olduğundan küçük gösterebilir. Bu yüzden karar, aralığın yanında model × delik hücreleri üzerinden ikinci bir
aralıkla da raporlanır (tohumlar sabit). İkisi farklı karar verirse **tutucu olan**, yani bir modele daha çok yer
bırakan geçerlidir.

**Okuma (veriden önce):**
- **S1 "yetiyor":** algılayıcı deneyinin S1 için açtığı öğrenilmiş tahminci kapısı, yukarıdaki fiziksel varsayım
  altında kapanır.
- **S1 "küçük pay" ya da "bilgi farkı":** S1'de öğrenilmiş tahminci protokolü açık kalır; rakibi TARE olur.
- **S2, S3:** hangi sonuç çıkarsa çıksın, orada yazılacak bir öğrenilmiş tahminci protokolünün rakibi TARE ile
  MOMENT-2R'den hızlı olanıdır.
- Dünya modeli bu deneyden doğrudan açılmaz.

**Betimsel:**
- MOMENT-2R − DOKUN, aynı yeni tohumlarda. Algılayıcı deneyinin tekrarı.
- Hücreye ve gecikmeye göre DT.
- TARE'nin ilk ölçümü: `|r̂| − |r|`, yön hatası.
- Kestirilen sapma ile gerçek sapma arasındaki fark.

## Pilot

Pilot tohumları 930–931, kullanıcının sınırı nedeniyle 2 tohum.
- **P0, duman testi:** TARE'nin çıkardığı ortalama, algılayıcının o koşudaki gerçek sapmasıyla gürültü düzeyinde
  aynı mı? Bakılan: S1–S3, model 0, birkaç koşu.
- **P1, kalibrasyon:** algılayıcı pilotunun P4 yordamı, TARE ile. Ayrıntılar:
  - düzey ve `c` başına `e ∈ {4, 6, 8, 10} mm`, 5 delik, 2 tohum, 20 ms gecikme;
  - `d = a + b|r|` en küçük kareler uydurması;
  - R² ≥ 0.5 ise kalibrasyon tutulur, değilse sabit adım `c`.

Ayar ızgarası yok. `R_MIN = 2 mm` sabit.

## Bilinen zayıflıklar

- **Yalnız 2 tohum.** Hücre başına 10 koşu, ayrıca PyBullet geçmişine bağlı koşu başına 1.4 s'ye kadar oynama var.
  Sınırda bir sonuç kesin sayılmamalı.
- **Sapmanın sabit olması** yeniden sıfırlamayı olabilecek en iyi duruma koyuyor (yukarıdaki açık soru).
- **TARE ayarlanmadı.** Ayarlı bir TARE daha iyi olabilir, yani sonuç rakip aleyhine tutucu.
- Algılayıcı deneyinin öteki zayıflıkları geçerli: uyum denetimi gerçek kuvveti görüyor, geometri kusursuz, düzeyler
  varsayım.

## Sapmalar

1. **Pilot sonuçları (ana koşudan önce, değişiklik yok).** `results/pilot_tare.txt`, tohumlar 930–931.
   - **P0 geçti:** çıkarılan ortalama, gerçek sapmaya gürültü düzeyinde yakın. Kuvvette ortanca hata S1 0.013 N,
     S2 0.05 N, S3 0.25 N; bunlar sapmanın standart sapmasının yaklaşık %13'ü. Her koşuda 30 tık ortalandı.
   - **P1:**

     | Düzey | R² (c = 5 / 2) | Karar | İlk ölçüm `|r̂| − |r|` ortancası | Yön hatası ortancası |
     |---|---|---|---|---|
     | S1 | 0.84 / 0.84 | kalibrasyon: `d = 14.3 mm − 0.82|r|` / `12.7 mm − 1.06|r|` | 0.6 mm | 3–4° |
     | S2 | 0.28 / 0.32 | sabit adım | 2.1 mm | 12–15° |
     | S3 | 0.03 / 0.01 | sabit adım | 11 mm | 39–65° |

     Karşılaştırma için MOMENT-2R'nin aynı ölçümleri: S1'de R² 0.36 ve yön hatası 16–22°, S2'de 53–60°.
2. **Ana koşudan sonra (karar değişmedi).**
   - Bağımsız denetim yapılmadı.
   - Yapılan öz denetimler:
     - Analiz betiği sahte veride doğru farkları buldu.
     - 4.860 koşunun hepsi tamam.
     - Model 0'daki S1 farkı (+0.17 s), algılayıcı denetiminin aynı kurulumla yaptığı kayıtsız sınamayla uyumlu
       (+0.20 s, tohum 400–409).
   - **S1'de kalan payın kaynağı (betimsel):** TARE 540 koşunun 7'sinde başarısız; DOKUN hiç başarısız değil. 7
     koşunun hepsi `c = 2`, `e = 10` hücresinde.
     - 6'sında ilk `|r|` 0.8–1.8 mm, yani `R_MIN = 2 mm`'nin altında. TARE doğrudan spirale düşüyor.
     - Kalibrasyon ters işaretli (`d = 12.7 mm − 1.06|r|`), yani küçük `|r|` aslında "uzakta" demek. Rakip
       deneyindeki Sapma 2'nin aynısı.
     - `R_MIN` bu protokolde ayarsız olarak 2 mm'ye sabitlendi. MOMENT-2R'nin S1 ayarı 1 mm seçmişti.
     - Yalnız başarılı koşularda fark +0.14 s.
     - Daha küçük bir `R_MIN` ile S1'in "yetiyor"a dönmesi olası görünüyor, ama sınanmadı. Kayıtlı karar "küçük pay"
       olarak kalır.
   - **S1'de iki aralık:** ana aralık [0.08, 0.66] tohum ekseni yüzünden geniş. İki tohumla, aynı tohumun iki kez
     çekildiği örnekler birkaç başarısız koşuyu ikiye katlıyor. Model-delik aralığı [0.13, 0.40] "yetiyor" diyor. Kural
     gereği tutucu olan, yani "küçük pay" geçerli.
