# Süre: konum bilgisi süreden ne kazandırıyor, modelsiz bir tahminci bunu alabiliyor mu?

Protokol: [PROTOKOL.md](PROTOKOL.md) (önceden yazıldı, sapmalar 1–8 sonunda). Kod: `timesim.py` (temaslı benzetimin
döngüsü + uçta moment, politikalar), `exp_time.py`, `pilot_time.py`, `analyze_time.py`; keşif `explore_bound.py`,
`explore_bound_report.py`. Çıktılar `results/`. Temaslı deneyin (`../panda_contact`) devamıdır.

## Soru ve kurulum

Temaslı deneyde KAHİN (konumu bilen) kör spiralden 1.6 s önce giriyordu. Burada rakip ucuz ve modelsiz tahmincilerdir:

- **A, tek atış** (hata her sokmada yeni): KAHİN, MOMENT (temas momentinden deliğin yönü, sonra düz arama),
  REFLEKS-H (süre için ayarlı spiral). 79.200 koşu, modeller 0–2.
- **B, kalıcı hata** (5 denemelik dizilerde aynı kayma + 1 mm sapma): KAHİN, HAFIZA (önceki başarılı sokmaların
  bulduğu kaymanın ortalaması). 36.000 koşu, model 0, 10 tohum.

Ölçüt ortalama varış süresi, başarısız koşu `tf = T + 8`. Eşik `δ = 0.5 s`, aralıklar %97.5 (iki test).

## Sonuç (önceden yazılmış kurallar, Sapma 6'daki tanım düzeltmesiyle)

| | Fark | %97.5 aralık | Karar |
|---|---|---|---|
| A: `t(MOMENT) − t(KAHİN)` | +1.21 s | [1.04, 1.39] | **Konum bilgisi pay bırakıyor, A'nın modeli aday** |
| B: `t(HAFIZA) − t(KAHİN)` | +0.45 s | [0.38, 0.54] | **Küçük pay dışlanamıyor, model açılmaz** |

Süre / başarı: A'da KAHİN 6.19 s / 0.940, MOMENT 7.40 / 0.883, REFLEKS-H 9.21 / 0.696. B'de KAHİN 6.21 / 0.942,
HAFIZA 6.66 / 0.917. Fark dar boşlukta toplanıyor: A'da `c = 2` 1.81 s, `c = 5` 0.61 s; B'de 0.78 ve 0.12 s.

Eski süre tanımıyla (yalnız derine inmeyenler `tf`) B "aday" çıkıyordu (+0.53 s). Protokol metni esas alındı.

## A'nın "aday" sonucu ne demek, ne demek değil

Kapı yalnız "bu MOMENT, KAHİN'in 0.5 s'den fazla gerisinde" diyor. "Konum tahmini bir model gerektiriyor" demiyor.

- **Farkın yarısını hiçbir temas modeli alamaz (keşif).** DOKUN-KAHİN, deliğin yerini ilk dokunuştan itibaren tam
  bilen politika. Model 0'da fark +1.17 s; bunun **+0.64 s'si [0.48, 0.81] ulaşılamaz** (dokunmanın ve oraya gitmenin
  bedeli), **ulaşılabilir kısım +0.53 s [0.37, 0.67]**, yani eşik civarında.
- **Ulaşılabilir kısım tek hücrede:** `c = 2, e = 10 mm`'de 2.47 s, öteki hücrelerde 0–0.39 s. Orada MOMENT'in yön
  hatası (ortanca 10.8°) delik konisinin yarı açısına (yaklaşık 11°) eşit, düz arama ıskalıyor ve yedek spirale düşüyor.
- **MOMENT bilerek en iyi halinde değildi:** yol boyunca yönü yeniden ölçmüyor, uzaklığı `|r|`'den kestirmiyor, yedek
  spirali başlangıç noktasında ve yalnız kısa gecikmede ayarlı (REFLEKS-H uzun gecikmede 0.50 / 0.15 başarıya düşüyor).
  Bunların düzeltilmesi muhtemelen ulaşılabilir kısmı kapatır. Sınanmadı.
- DOKUN-KAHİN de kesin bir sınır değil: ani kayma başarıyı düşürüyor (0.900), daha akıllı bir tam bilgili politika
  daha iyi olabilir.

Sonuç: bir öğrenilmiş tahminciye geçmeden önce yapılacak doğru deney, **daha iyi bir elle yapılmış rakip**
(yeniden nişan, uzaklık kestirimi, yerel yedek spiral, gecikmeye göre spiral hızı), ölçüt DOKUN-KAHİN'e karşı.

## B neden model açmıyor

Önceden yazılmış kural zaten "açılmaz" diyor. Keşif de aynı yönde (tohum 200–204):

- 1. deneme (henüz veri yok, ulaşılamaz): +0.22 s.
- O denemenin sapması (SABİT-KAHİN − KAHİN): +0.06 s.
- Denemeler arası mükemmel bir öğrenicinin alabileceği: **+0.21 s [0.13, 0.34]**, eşiğin altında.

HAFIZA'nın kalan hatası (ortanca 2.1 mm) ucun delik duvarına yaslanarak bitmesinden geliyor. Bu da modelsiz bir
düzeltmeyle (duvar temas yönü) muhtemelen küçülür.

## Pilot ve hatalar

- P1 (yön hatası ortanca 1.9°), P2, P3 (düzeltmeden sonra) geçti. P5 yüzünden B'nin tohumları 10'a indi.
- Pilot, eski temaslı koddaki 20 ms süzgeç hatasını buldu (19'a bölüyordu, kuvvetler %5.3 yüksek; temaslı karar
  değişmedi, `panda_contact` Sapma 5).
- Denetim, süre tanımının protokolden saptığını buldu (Sapma 6); B'nin kararı bu yüzden döndü.

## Sınırlar

- Moment ölçümü benzetimde kusursuz geometriyle; gerçek algılayıcıda MOMENT daha kötü olabilir.
- Hata tek bir yatay kayma; eğik delik, dönme hatası yok. Takım gerçek şemsiye değil.
- REFLEKS-H ve MOMENT yalnız `h = 20 ms`'de ayarlandı; uzun gecikmede rakipler en iyi hallerinde değil, bu A'yı
  modelin lehine şişirir.
- `δ = 0.5 s` keyfi; bir hat çevrim süresinden türetilmedi. PyBullet sert teması kaba, aynı koşu süreç geçmişine göre
  0.4 mm'ye kadar değişiyor.
- Keşif ölçümleri ön kayıtlı değil, yalnız model 0 (A) ve 5 tohum (B).
