# Daha iyi elle yapılmış rakip: temas modelinin alabileceği süre kalıyor mu?

Protokol: [PROTOKOL.md](PROTOKOL.md). Ana koşudan önce yazıldı; sapmalar 1–4 sonunda.

Kod:
- `rival.py`: politikalar ve ana koşu, her işten sonra ara kayıt.
- `pilot_rival.py`: ilk pilot.
- `pilot_rival2.py`: kalibrasyonlu MOMENT-2 için pilot (Sapma 1).
- `analyze_rival.py`: karar ve betimsel dökümler.

Çıktılar `results/` altında. Süre deneyinin (`../panda_time`) devamıdır.

## Soru

Süre deneyinin A durumunda (tek atış) MOMENT, KAHİN'den 1.21 s geç giriyordu. Keşif bu farkı ikiye ayırdı:
- Hiçbir temas modelinin alamayacağı kısım: KAHİN deliği temastan önce biliyor.
- Alınabilir kısım: MOMENT ile DOKUN-KAHİN arasındaki fark. DOKUN-KAHİN deliğin yerini ilk tetikten itibaren tam
  bilir.

Burada MOMENT'in zayıflıklarını gideren modelsiz bir rakip, DOKUN-KAHİN'e karşı sınandı. **MOMENT-2** şunları yapar:
- her oturuşta yeniden nişan alır (en çok 4 nişan);
- uzaklığı moment kolu `|r|`'den kestirir;
- yön çıkmazsa ya da nişanlar biterse o anki kestirimin çevresinde, gecikmeye göre ayarlı bir yedek spiral kullanır.

İki politikanın tetiği, donması ve spirali aynıdır. Fark yalnız bilgidir: biri `e`'yi kestirir, öteki bilir.

Koşullar:
- 81.600 koşu: modeller 0–2, `T ∈ {8, 4}`, 3 gecikme, itmeli ve itmesiz, `e ∈ {3, 6, 10} mm`, `c ∈ {5, 2} mm`, 5 delik,
  20 yeni tohum (300–319).
- Ölçüt ortalama varış süresi; başarısız koşu `tf = T + 8` sayılır.
- Eşik `δ = 0.5 s`, %95 bootstrap aralığı.

## Pilotun beklenmedik bulgusu (Sapma 1)

Uzaklık ile moment kolu arasındaki ilişki çok güçlü (R² 0.97 / 0.94, ortanca hata 0.2 / 0.4 mm), ama ters işaretli:

- `c = 5`: `d = 15.3 mm − 0.97 |r|`
- `c = 2`: `d = 13.6 mm − 1.22 |r|`

Uç delikten uzaklaştıkça yüzünün daha büyük kısmı kenara oturur ve temasın ağırlık merkezi uca yaklaşır. Kayıtlı
kural `b ≤ 0` olunca sabit adım zorunlu tutuyordu; bu koşul yanlış bir işaret tahminine dayanıyordu. Ana koşudan önce
şunlar yapıldı:
- Koşul düşürüldü.
- Kalibrasyonlu MOMENT-2 karar politikası oldu.
- Kayıtlı (sabit adımlı) hâl **MOMENT-2F** adıyla bütün ızgarada ayrıca koşuldu.

## Sonuç

| | Fark | %95 aralık | Karar |
|---|---|---|---|
| **`D2 = t(MOMENT-2) − t(DOKUN-KAHİN)`** | **+0.25 s** | **[0.18, 0.32]** | **Elle yapılmış rakip yetiyor; temas sırasında konum tahmini için model açılmaz** |
| Kayıtlı hâl: `t(MOMENT-2F) − t(DOKUN-KAHİN)` | +1.32 s | [1.21, 1.42] | Bilgi farkı kalıyor |

- Geçerlilik: S(DOKUN-KAHİN) 0.948 ≥ 0.85.
- Süre / başarı: DOKUN 6.40 s / 0.948, MOMENT-2 6.65 / 0.932, MOMENT-2F 7.72 / 0.909.
- Ortalama kaydırmalı aralık [0.18, 0.32], pivot [0.18, 0.31]. Hepsi eşiğin epey altında.

**Karar Sapma 1'e dayanıyor.** Kayıtlı kural harfiyen uygulansaydı sonuç "bilgi farkı kalıyor" olurdu. Sapma ana
veriden önce, pilot tohumlarıyla ve protokolün açıkça yazdığı amaç yönünde yapıldı ("ayar bilerek rakibin lehine";
geri çekilme kalibrasyon zayıfsa). Yine de "elle yapılmış rakip" kendi başına modelsiz değil: her boşluk için iki
sabit (`a_c`, `b_c`) pilotta ölçüldü. Gecikme kuralındaki tek sabit gibi, ama bir ölçme gerektiriyor.

### Model 0'da tablo (betimsel)

| | KAHİN | DOKUN-KAHİN | MOMENT-2 | MOMENT |
|---|---|---|---|---|
| t (s) | 6.12 | 6.41 | 6.64 | 7.26 |
| S | 0.950 | 0.948 | 0.933 | 0.902 |

Süre deneyindeki MOMENT − KAHİN farkı burada 1.14 s ve üç parçaya ayrılıyor:
- **0.62 s:** MOMENT-2 elle kapattı (yeniden nişan ve kalibrasyon).
- **0.30 s:** hiçbir temas modelinin alamayacağı bedel. Keşifte bu 0.64 s çıkmıştı; DOKUN'un spirali burada daha iyi
  ayarlı.
- **0.23 s:** kalan.

### Kalan 0.25 s nerede

- **Hücreye göre D2 (s):**

  | | e = 3 | e = 6 | e = 10 |
  |---|---|---|---|
  | c = 5 mm | +0.02 | +0.06 | +0.09 |
  | c = 2 mm | +0.21 | +0.10 | **+1.01** |

  MOMENT-2F için aynı tablo: `c = 2`'de +0.42 / +2.29 / +4.83.
- **Gecikme:** 20 ms +0.14, 65 ms +0.19, 130 ms +0.41.
- **İtme ve sürtünme:** itmesiz +0.24, itmeli +0.26. `μ` üçte birlikleri +0.23 / +0.24 / +0.27.
- **Kaynağı:**
  - Koşuların %2.1'inde ilk `|r|` 2 mm'nin altında kalıyor ve MOMENT-2 doğrudan spirale düşüyor. Bunlar D2'nin
    **0.11 s'si**, yani neredeyse yarısı. Ters işaret yüzünden küçük `|r|` "uzakta" demektir; kayıtlı `R_MIN` eşiği
    bu rakip için kötü seçilmiş (Sapma 2, bilerek değiştirilmedi).
  - Nişanları biten koşular (%5.9) 0.06 s'sini oluşturuyor.

  Yani kalanın çoğu iki elle düzeltilebilir kuraldan geliyor gibi görünüyor. Bu sınanmadı.
- **Kestirim hatası:** ortanca son hata 0.25–1.0 mm. Tek kötü hücre `c = 2, e = 10`: ilk nişanda 2.2 mm, sonra 0.96 mm.
- **Boş yere tetiklenme bedeli** (`e = 0`, KAHİN'in `e = 3` koşularıyla karşılaştırma): +0.03 s.

## Denetim

Bağımsız bir ajan kodu ve veriyi denetledi; ona sonuç verilmedi.

Doğrulananlar:
- D2 ve D2F'yi kendi koduyla aynı buldu.
- MOMENT-2'ye gerçek delik ya da `e` sızmıyor: yalnız nominal delik, uç konumu ve gürültülü kuvvet-moment.
- 816 işin hepsi eksiksiz.
- Pilot değerleri seçme kuralına uyuyor.
- DOKUN'un mekaniği D2'yi küçültmüyor. Bunu, MOMENT-2'nin mekaniğiyle `e`'yi bilen bir "kâhin MOMENT-2" koşarak
  gösterdi: DOKUN'dan hızlı değil.

Kararı değiştirmeyen bulgular (Sapma 4):
- MOMENT-2F'nin karşılaştırmasında DOKUN'un 130 ms spirali kayıtlı olandan farklı. D2F yaklaşık 0.01 s küçük kalıyor.
- `N_AIM` protokol metnine göre bir eksik olabilir. Etkisi en çok 0.06 s.
- Tek tek MOMENT-2 koşuları PyBullet süreç geçmişine göre 1.4 s'ye kadar oynuyor. D2 yaklaşık 0.01 s oynuyor.
- `e = 0` karşılaştırması, `μ` dilimleri ve D2'nin kaynağı analize eklendi ya da düzeltildi.

## Ne demek, ne demek değil

- **Demek:** bu benzetimde süre deneyinin "aday" sonucu kapandı. Temas sırasında deliğin yerini kestirmek için
  öğrenilmiş bir modelin alabileceği süre, iki sabitli elle yapılmış bir kuraldan sonra 0.25 s. Bunun da yarısı
  eşik seçiminden.
- **Programın geneli:** bu benzetimde açılan her kapı elle yapılmış bir kuralla kapandı:
  - temassız görevde hız kapısı;
  - temaslı başarıda REFLEKS;
  - süre B'de HAFIZA;
  - süre A'da MOMENT-2.

  Bir modelin savunulabilir yeri artık benzetimin göstermediği şeyler:
  - gerçek kuvvet-moment algılayıcısının sapması ve gürültüsü (burada moment kusursuz geometriyle);
  - eğik delik ve dönme hatası;
  - kalibrasyonun gerçek robotta tutmaması.
- **Demek değil:**
  - Gerçek robotta MOMENT-2'nin bu kadar iyi olacağı. Kalibrasyon benzetim geometrisinden ölçüldü.
  - DOKUN-KAHİN'in kesin bir üst sınır olduğu. Daha akıllı bir tam bilgili hareket daha hızlı olabilir, ama aynı
    mekanik MOMENT-2'yi de hızlandırır.
  - `δ = 0.5 s`'nin doğal bir eşik olduğu. `c = 2, e = 10` hücresinde fark hâlâ 1 s.
