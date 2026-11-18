# Algılayıcı sağlamlığı: gerçekçi kuvvet-moment hatasında elle yapılmış rakip hâlâ yetiyor mu?

Protokol: [PROTOKOL.md](PROTOKOL.md). Ana koşudan önce yazıldı; sapmalar 1–4 sonunda.

Kod:
- `sensor.py`: algılayıcı modeli, politikalar, ana koşu (her işten sonra ara kayıt).
- `pilot_sensor.py`: pilot.
- `analyze_sensor.py`: karar ve betimsel dökümler.
- `explore/components.py`: kayıtlı olmayan keşif.

Çıktılar `results/` altında. Rakip deneyinin (`../panda_rival`) devamıdır.

## Soru

Rakip deneyinde MOMENT-2, DOKUN-KAHİN'in 0.25 s gerisindeydi. Ama moment kusursuz geometriden geliyordu ve ölçüm
doğrudan uçta yapılıyordu. Burada algılayıcı gerçekçi bir yere taşındı: flanşta, ucun `L = 0.35 m` üstünde bir bilek
F/T algılayıcısı. Uç momenti flanş ölçümünden hesaplanıyor.

Hata kaynakları:
- gürültü;
- sıfırlamadan sonra kalan sapma (koşu başına sabit);
- kol uzunluğu hatası;
- düşey eksen çevresinde hiza hatası;
- moment ölçek hatası.

Üç düzey:
- **S1:** iyi bilek algılayıcısı.
- **S2:** sıradan ve kayan bilek algılayıcısı.
- **S3:** bilek algılayıcısı yok, kuvvet eklem torklarından.

Düzeyler veri sayfası büyüklüklerine dayanan varsayımlardır, ölçülmedi.

Koşullar:
- 64.800 koşu: modeller 0–2, `T = 8`, 3 gecikme, itmesiz, `e ∈ {3, 6, 10} mm`, `c ∈ {5, 2} mm`, 5 delik, 20 yeni
  tohum (400–419).
- Karar politikası **MOMENT-2R**: her düzey için pilotta yeniden kalibre edildi ve ayarlandı.
- Ölçüt `D2 = t(M2R) − t(DOKUN-KAHİN)`. Başarısız koşu `T + 8` sayılır.
- Eşik `δ = 0.5 s`, %98.3 aralık (üç düzey, Bonferroni).

## Pilot

- **Kalibrasyon her düzeyde düştü.** R² S1'de 0.36 / 0.38, S2'de 0.01, S3'te 0.00. Kurala göre sabit adım.
- **Neden:** sapma, tetikten hemen sonraki küçük `F_z`'ye (5–10 N) bölünüyor ve 0.35 m'lik kolla büyüyor. İlk
  ölçümde yön hatasının ortancası S1'de 16–22°, S2'de 53–60°, S3'te 77–82°.
- **Ek politika M2C:** zayıf uydurma R²'ye bakılmadan tutuldu ve betimsel olarak koşuldu (Sapma 3).

## Sonuç (kayıtlı kural)

| Düzey | DOKUN t / S | M2R t / S | D2 | %98.3 aralık | Karar |
|---|---|---|---|---|---|
| S1 | 7.68 / 1.000 | 9.36 / 0.923 | **+1.68 s** | [1.49, 1.94] | bilgi farkı |
| S2 | 7.68 / 1.000 | 10.83 / 0.778 | +3.15 s | [2.59, 3.84] | bilgi farkı |
| S3 | 7.68 / 1.000 | 11.68 / 0.686 | +4.00 s | [3.38, 4.69] | bilgi farkı |

- Geçerlilik her düzeyde sağlanıyor: S(DOKUN) 1.000.
- Ortalama kaydırmalı ve pivot aralıklar da aynı kararı veriyor.
- **M2C:** S1'de M2R'den iyi (+0.97 s [0.57, 1.54]), ama o da bilgi farkı veriyor. S2 ve S3'te çok daha kötü
  (+4.58 / +5.71 s; başarı 0.52 / 0.34).
- **Kayıtlı birleşik okuma:** fark S1'de kalıyor. Kural bunun için şunu söylüyor: S1'de öğrenilmiş bir tahminciyi
  M2R'ye karşı sınayan ayrı bir protokol yazılır. Dünya modeli yok.

### Fark nerede (betimsel)

- **Hücreye göre D2 (s):**

  | | c = 5: e = 3 | e = 6 | e = 10 | c = 2: e = 3 | e = 6 | e = 10 |
  |---|---|---|---|---|---|---|
  | S1 | 0.00 | +0.04 | +0.66 | +0.32 | +2.81 | **+6.26** |
  | S2 | 0.00 | +2.19 | +4.16 | +1.22 | +4.21 | +7.10 |
  | S3 | +0.04 | +4.12 | +5.65 | +1.91 | +4.87 | +7.37 |

  S1'de geniş boşlukta rakip hâlâ yetiyor. Fark dar boşlukta ve büyük hatada.
- **Gecikme, S1:** 20 ms +1.24, 65 ms +1.56, 130 ms +2.25 s.
- **Model 0'da ayrıştırma:**

  | Düzey | DOKUN | M2O (gerçek moment) | M2R | M2T (temiz kalibrasyon) |
  |---|---|---|---|---|
  | S1 | 7.71 | 7.81 | 9.34 | 8.94 |
  | S2 | 7.71 | 8.81 | 10.78 | 11.23 |
  | S3 | 7.71 | 7.95 | 11.68 | 11.03 |

  Gerçek momenti gören M2O DOKUN'a yakın. Yani kayıp kuralın kendisinden değil, algılayıcıdan geliyor. Tek istisna
  S2'deki M2O; o da devraldığı `R_MIN = 4 mm` yüzünden (Sapma 4c).
- **İlk ölçüm (M2R):**

  | Düzey | `|r̂| − |r|` ortancası | Yön hatası ortancası | Son kestirim hatası |
  |---|---|---|---|
  | S1 | 1.8 mm | 13° | 2.1 mm |
  | S2 | 8.3 mm | 49° | 5.1 mm |
  | S3 | 52 mm | 79° | 7.5 mm |
- **S0 (ideal, yeni tohumlar):** D2 +0.21 s. Rakip deneyini tekrarlıyor.

## Denetim ve kararı okumayı değiştiren bulgu (Sapma 4)

Bağımsız bir ajan kodu ve veriyi denetledi; ona sonuç verilmedi.

Doğrulananlar:
- Kararı kendi koduyla aynı buldu.
- Rakiplere gerçek delik ya da gürültüsüz kuvvet sızmıyor.
- Algılayıcı formülü protokolle birebir.
- 648 iş eksiksiz; pilot değerleri kurala uygun.

**Ama protokolün bir iç çelişkisini buldu.** Protokol, koşu başına sapmanın aynı algılayıcıyla bilinemeyeceğini
varsayıyordu. Benzetimde ise sapma sabit ve temastan önce gerçek kuvvet tam sıfır. Yani boşta okunan değer sapmanın
kendisi.

Temastan hemen önce yeniden sıfırlayan bir M2R ("TARE") sınandı. Son 30 boşta tıkın ortalamasını alıyor; pilot
tohumlarında yeniden kalibre edildi, ayarlanmadı.
- S1'de kalibrasyon geri geliyor: R² 0.79, yön hatası 4–5°.
- Model 0, tohum 400–409:

  | Düzey | TARE − DOKUN | M2R − DOKUN |
  |---|---|---|
  | S1 | **+0.20 s** [0.08, 0.35] | +1.58 s |
  | S2 | +1.59 s | +2.87 s |

Kayıtlı değil, yalnız model 0'da ve tohumların yarısıyla yapıldı. Ama bütün ızgarada tutarsa S1, öğrenilmiş bir modelin
değil bir el kuralının yettiği yere döner. S2 ve S3'te fark yeniden sıfırlamadan sonra da büyük kalıyor.

### Keşif: hangi hata bileşeni (kayıtlı değil)

`explore/components.py` M2R'yi S1'de, model 0'da, pilot tohumlarında koşturdu. Her seferinde bir hata grubu
kapatıldı. M2R yeniden ayarlanmadı, yani sabit adımlı kaldı.

| M2R | tam | sapmasız | gürültüsüz | geometri hatasız | yalnız sapma |
|---|---|---|---|---|---|
| D2 (s) | +1.71 | +1.49 | +1.75 | +1.73 | +1.74 |

- **Kalan hatalar arasında baskın olan sapma.** Yalnız sapma bırakılınca D2 tamdaki kadar kalıyor; gürültüyü ya da
  geometriyi kapatmak bir şey değiştirmiyor.
- **Ama sapmayı kapatmak tek başına farkı kapatmıyor.** M2R pilotta kalibrasyonunu kaybetmiş ve sabit adım kullanıyor.
  Asıl kayıp bu.
- **Zincir şu:** sapma → pilotta kalibrasyon düşer → sabit adım → yavaş.
- TARE farkı kapatıyor, çünkü yeniden sıfırlanmış ölçümle kalibrasyon geri geliyor.

## Ne demek, ne demek değil

- **Demek:**
  - Kayıtlı rakip (yeniden kalibre edilmiş MOMENT-2) bilek algılayıcısının gerçekçi hatasında çöküyor. Bu S1'de bile
    geçerli.
  - Çöküşün nedeni tetikten hemen sonraki küçük kuvvete bölünen sapma ve 0.35 m'lik kol.
- **Kesin değil:**
  - S1'deki farkın öğrenilmiş bir modele yer açıp açmadığı. Basit bir yeniden sıfırlama farkın çoğunu kapatıyor
    gibi. Bunun kabul edilebilir olup olmadığı fiziksel bir soruya bağlı: gerçek algılayıcıda 0.1 N'lik kalan sapma
    temastan hemen önce mi kalıyor, yoksa görevin başındaki sıfırlamadan sonra mı birikiyor?
    - İlkinde yeniden sıfırlama benzetimi sömürür.
    - İkincisinde sıradan iyi uygulamadır.
- **S2 ve S3:** yeniden sıfırlamadan sonra da 1.5 s'nin üstünde fark kalıyor (S2, model 0). Öğrenilmiş bir modelin
  savunulabilir ilk yeri burası olabilir. Yine de rakibin bu düzeyde de iyileştirilmesi gerekir: yeniden sıfırlama
  artı bu düzeyin kalibrasyonu ya da yanal kuvvet yönü.
- **Demek değil:**
  - Gerçek robotta bu sayıların çıkacağı. Düzeyler ölçülmedi.
  - Uyum denetimi burada gerçek kuvveti görüyor; gerçekte aynı algılayıcıyı kullanır.
