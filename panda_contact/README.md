# Temaslı sokma: konum bilgisi model açıyor mu?

Protokol: [PROTOKOL.md](PROTOKOL.md) (önceden yazıldı, sapmalar 1–4 sonunda). Kod: `contact.py` (benzetim),
`exp_contact.py` (ana koşu), `pilot.py`, `analyze_contact.py`. Çıktılar `results/`, denetim `audit/`.
Ortam: proje kökündeki `.pbenv` (conda-forge pybullet 3.25).

## Soru

Gerçek delikli tutucuda, deliğin konumu `e` kadar yanlış bilinirken, konumu bilen bir politika (`KAHİN`) kör spiral
aramadan (`REFLEKS`) ne kadar iyi? Karar `W = S(KAHİN) − S(REFLEKS)` ile, eşik 0.03.

105.600 koşu: 4 alan (makale tarifiyle öğrenilmiş 3 model + analitik), `T ∈ {8, 4}`, üç gecikme, itmeli/itmesiz,
`e ∈ {0, 3, 6, 10} mm`, `c ∈ {5, 2} mm`, 5 delik, 20 tohum. Hız kapısı (`L = .02`) ve gecikme kuralı açık.

## Sonuç (birincil: makale kolu, `c = 5 mm`, `e > 0`)

| | Değer | Yüzdelik aralık |
|---|---|---|
| S: TABAN / REFLEKS / KAHİN | 0.618 / 0.942 / 0.959 | |
| G, `e = 0`'da TABAN | 0.958 | [0.929, 0.981] |
| K, konum hatasının bedeli | +0.340 | [0.319, 0.360] |
| R, refleksin katkısı | +0.324 | [0.309, 0.338] |
| W, konum bilgisinin değeri | +0.016 | [0.002, 0.036] (pivot [−0.003, 0.031]) |

**Önceden yazılmış karar: "Küçük bir pay dışlanamıyor. Model açılmaz, yük modelindir."** `W < 0.03 ≤ U`.

**Varış süresi maddesi tetiklendi:** `REFLEKS` 7.34 s, `KAHİN` 5.68 s, fark 1.66 s. Protokole göre bu başarı açısından
modeli açmaz. Hedefi süre olan ayrı bir protokol gerekir.

## Ne anlama geliyor

- Konum hatası gerçek bir sorun: refleksiz taban `e = 10 mm`'de %0.6 başarıyor.
- 15 satırlık bir spiral arama bunu neredeyse kapatıyor. Kalan pay `e = 6 mm`'de 0.019, `e = 10 mm`'de 0.030, `e = 3 mm`'de 0.
- İtmesiz yarıda `W` 0.009. Payın kalanı, yanlış hizalı aranırken itme gelince oluşan fazladan darbelerden geliyor.
- `KAHİN`'in kalan %4 hatası konumla ilgili değil: yalnız itmeli koşularda, itme çubuğu tutucunun üstüne vurduruyor
  (`F_max` aşımı). Uzun gecikme ve `T = 8`'de en sık (en çok %20).
- Öğrenme bedeli görünmez: analitik alan `W` +0.013, modeller +0.013–0.021.

## İkincil: `c = 2 mm`

`W = +0.171 [0.141, 0.198]`. Karara girmez. Denetimin tanısı: `REFLEKS` sıkışmıyor, zamanı yetmiyor. `e = 10 mm`'de
spiralin o yarıçapa varması yaklaşık 8 s, delik açısına gelmesi bir tur daha. Ayrıca uç `ŝ`'yi yaklaşık 2.3 mm geriden
izliyor, bu `c`'den büyük, yani `2c` adımlı spiral boşluk bırakıyor. Spiral hızı `c = 5`'te ayarlandı. Dar boşlukta
konum bilgisinin değeri büyük olabilir, ama bu sonuç arama tasarımına (hız, adım, `tf`) bağlıdır, sınanmış bir iddia
değildir.

## Denetim

Bağımsız denetim (`audit/`) bütün birincil sayıları kendi koduyla aynen buldu. Başka bootstrap düzenleri
(tohumlar deliklere iç içe: U 0.032; modeller sabit: 0.035) karar satırını değiştirmedi. `e`'nin uygulanması ve
`KAHİN`'in işareti, paylaşılan rastgelelik, itme, başarı ölçütü, spiral ayrıntıları doğrulandı. İki raporlama açığı
düzeltildi (Sapma 4).

**Sonradan bulunan hata (Sapma 5):** 20 ms kuvvet süzgeci 20 yerine 19'a bölüyordu, kuvvetler %5.3 yüksek okundu.
Düzeltilmiş ölçütle karar aynı: W +0.018 [0.004, 0.036].

## Sınırlar

- PyBullet sert temas kabadır; sürtünme ve sıkışma gerçek robota nicel taşınmaz.
- Konum hatası yapay ve tek bir yatay kayma; gerçek algı hatası ölçülmedi. Takım gerçek şemsiye değil.
- `W` spiral hızına, adımına ve `tf`'ye bağlıdır; `REFLEKS` bilerek iyi ayarlandı (modelin aleyhine).
- Refleksin kuvvet ölçümü gecikmesiz; bu `REFLEKS`'i biraz kayırır.
- Pilotta M4'ün kodlanmış ölçütü yavaş yapış-kay yüzünden kaldı (Sapma 3).
- `KAHİN` yalnız konum bilgisini ölçer. Başka bir bilginin (sürtünme, sıkışma, süre) değeri bu deneyde ölçülmedi.
