# Algılayıcı sağlamlığı: gerçekçi kuvvet-moment hatasında elle yapılmış rakip hâlâ yetiyor mu?

2026-11-17 yazıldı, koddan ve koşudan önce. Kullanıcı "2. kısım olsun" dedi (algılayıcı sağlamlığı protokolü).

## Neden

Rakip deneyinde (`panda_rival/README.md`) kalibrasyonlu MOMENT-2, DOKUN-KAHİN'e 0.25 s [0.18, 0.32] yaklaştı. Karar
"elle yapılmış rakip yetiyor" oldu. Ama orada uçtaki moment **kusursuz geometriyle, doğrudan uçta** ölçülüyordu:
`m_meas = m_uç + N(0, 0.005 Nm)`. Gerçek robotta durum farklı:

- Algılayıcı bileğin flanşındadır. Benzetimdeki pim 0.25 m, Franka elinin flanştan tutma noktasına uzaklığı yaklaşık
  0.10 m, yani **uca kol uzunluğu L ≈ 0.35 m** (varsayım).
- Uçtaki moment, flanştaki ölçümden `τ̂_uç = τ̂_f + L̂ ẑ × F̂` diye hesaplanır. **Kuvvetteki her hata L kadar büyüyerek
  uç momentine geçer.** 0.1 N'luk yanal kuvvet hatası 0.035 Nm eder; bu, bugünkü moment gürültüsünün yedi katıdır.
  28 N'luk basma kuvvetinde temas noktası kestiriminde de 1.25 mm sapma demektir.
- Sıfırlamadan sonra kalan sapma, kol uzunluğu hatası, algılayıcının dönme hizası ve ölçek hatası da vardır.
- Bilek algılayıcısı yoksa kuvvet eklem torklarından kestirilir ve hata çok daha büyüktür.

Bir modelin savunulabilir yeri artık yalnız benzetimin göstermediği şeylerde kaldı. Bunların ilki bu.

Soru: **Gerçekçi algılayıcı hatalarında MOMENT-2 (o algılayıcıyla yeniden kalibre edilip ayarlanmış hâliyle),
DOKUN-KAHİN'e 0.5 s içinde yaklaşıyor mu?** Hangi hata düzeyinde kopuyor?

## Algılayıcı modeli

`panda_time` benzetimi (`timesim.run_t`) değişmez. Yalnız politikaların ve tetiğin gördüğü ölçüm değişir:

- Flanştaki gerçek moment `τ_f = τ_uç + (−L ẑ) × F`, `L = 0.35 m`.
- Ölçüm, her koşu için çekilen hatalarla:
  - kuvvet: `F̂ = R_φ (F + b_F + n_F)`
  - flanş momenti: `τ̂_f = R_φ (1 + k)(τ_f + b_τ + n_τ)`
  - uç momenti: `τ̂_uç = τ̂_f − (−L̂ ẑ) × F̂`, `L̂ = L + δL`
- `n_F`, `n_τ`: her kontrol tıkında beyaz gürültü (bugünkü gibi 20 ms süzgeçten sonra eklenir).
- `b_F`, `b_τ`: sıfırlamadan sonra kalan sapma. Her eksende, her koşu için `N(0, β)`, koşu boyunca sabit.
- `δL` (kol uzunluğu hatası), `φ` (düşey eksen çevresinde hiza hatası), `k` (moment ölçek hatası): her koşu için
  düzgün dağılımdan. Kalibrasyondan sonra kalan belirsizlik olarak düşünülür; sabit bir hata iki taraf için de
  kalibre edilebilir.
- **Uyum (admittance) denetimi ve başarı ölçütü gerçek kuvveti görmeye devam eder.** Hata yalnız kestirim kanalına
  girer (aşağıda zayıflıklar).

Düzeyler. Bunlar veri sayfası büyüklüklerine dayanan **varsayımlardır, ölçülmüş değildir**; kullanıcının gerçek
algılayıcısıyla karşılaştırılmalıdır:

| Düzey | Anlamı | σ_F (N) | σ_τ (Nm) | β_F (N) | β_τ (Nm) | δL (mm) | φ (°) | k |
|---|---|---|---|---|---|---|---|---|
| S0 | Bugünkü ideal model (uçta doğrudan ölçüm) | 0.5 | 0.005 (uçta) | 0 | 0 | 0 | 0 | 0 |
| S1 | İyi bilek F/T, her sokmadan önce sıfırlanmış | 0.05 | 0.002 | 0.1 | 0.003 | ±1 | ±1 | ±%1 |
| S2 | Sıradan bilek F/T, sıfırlanmış ama kayan | 0.2 | 0.005 | 0.5 | 0.01 | ±3 | ±3 | ±%3 |
| S3 | Bilek algılayıcısı yok, kuvvet eklem torklarından | 1.0 | 0.05 | 2.0 | 0.1 | ±5 | ±5 | ±%10 |

`L = 0.35 m` kolla, uç momentindeki yaklaşık etkiler:

| Düzey | Gürültü (Nm) | Sapma (Nm) | Temas noktasında sapma (28 N'da) |
|---|---|---|---|
| S1 | ≈ 0.018 | ≈ 0.035 | ≈ 1.3 mm |
| S2 | ≈ 0.07 | ≈ 0.18 | ≈ 6 mm |
| S3 | ≈ 0.35 | ≈ 0.7 | ölçüm anlamsızlaşır |

Yani düzeyler, rakibin rahat olduğu yerden çökeceği yere kadar uzanır. Sorulan şey kopma noktasının nerede olduğu.

## Politikalar

Tetik, donma ve yedek spiral `panda_rival`'daki gibidir. Spiral hızı gecikmeye göre 10 / 10 / 5 mm/s. Tetik eşiği `F_t`
düzeye göre pilotta seçilir ve iki politika için ortaktır.

- **DOKUN-KAHİN (bilgi sınırı):** ilk tetikte `ŝ = e`. Tetiği gürültülü `F̂_z` ile verir, yani tetik hatası onu da
  etkiler. Moment okumaz.
- **MOMENT-2R (karar veren rakip):** `panda_rival`'daki MOMENT-2. Her düzeyde o düzeyin algılayıcısıyla:
  - uzaklık kalibrasyonu `d = a + b|r|` yeniden ölçülür;
  - `n_w` ve yön yok eşiği `R_MIN` yeniden ayarlanır.

  Gerçek robotta da kalibrasyon o robotta yapılır. Öğrenilmiş bir tahminci de o algılayıcının verisiyle eğitilirdi.
- **MOMENT-2T (aktarım, betimsel):** `panda_rival`'ın temiz kalibrasyonu ve ayarıyla. Yeniden kalibre etmemenin bedeli.
- **MOMENT-2O (algılayıcı kâhini, betimsel):** MOMENT-2R'nin ayarıyla, ama gerçek uç momentini görür. Tetik yine
  gürültülü. D2'yi "algılayıcının bedeli" ve "kuralın bedeli" diye ayırır.

## Koşullar

- Modeller 0, 1, 2; `T = 8`; `(h, τ) ∈ {(20, 0), (40, 25), (90, 40)} ms`; **itmesiz**; `e ∈ {3, 6, 10} mm`;
  `c ∈ {5, 2} mm`; 5 delik; 20 yeni tohum (400–419).
- İtme ve `T = 4` çıkarıldı. Rakip deneyinde itmenin etkisi yoktu (+0.24 / +0.26 s); `T` yalnız yaklaşmayı değiştirir.

| Politika | Düzeyler | Kapsam | Koşu |
|---|---|---|---|
| DOKUN-KAHİN, MOMENT-2R | S1, S2, S3 | bütün ızgara | 32.400 |
| MOMENT-2T, MOMENT-2O | S1–S3 | model 0 | 10.800 |
| MOMENT-2R, `e = 0` (boş yere tetiklenme) | S1–S3 | model 0 | 1.800 |
| DOKUN-KAHİN, MOMENT-2 | S0 (başvuru) | model 0 | 3.600 |
| **Toplam** | | | **48.600** (tahminen 6–7 saat) |

## Ölçüt ve karar

- Ölçüt `panda_rival` ile aynı: ortalama varış süresi, `ok` olmayan her koşu `tf = T + 8 = 16 s`. Birincil hücrelerin
  (model, gecikme, `e > 0`, `c`, delik, tohum) eşit ağırlıklı ortalaması.
- Her düzey `L ∈ {S1, S2, S3}` için ayrı bir test: `D2_L = t(MOMENT-2R) − t(DOKUN-KAHİN)`.
- Bootstrap modeller, delikler, tohumlar üzerinden, 2000 tekrar.
- Üç test olduğu için her biri **%98.33** iki yanlı yüzdelik aralıkla (Bonferroni).
- Eşik `δ = 0.5 s`.

Her düzeyde:

| Sonuç | Karar (o düzey için) |
|---|---|
| `S(DOKUN-KAHİN) < 0.85` | Geçersiz; tetik o düzeyde çalışmıyor, raporlanır |
| `U < δ` | Elle yapılmış rakip bu algılayıcıyla da yetiyor |
| `D2 < δ ≤ U` | Küçük pay dışlanamıyor; model açılmaz, yük modelindir |
| `D2 ≥ δ`, alt sınır `> 0` | Bilgi farkı kalıyor |
| `D2 ≥ δ`, alt sınır `≤ 0` | Karar yok |

Birlikte yorum, önceden yazılı:

- **S1 ve S2 yetiyor:** sıradan bir bilek algılayıcısıyla da elle yapılmış kural yeterli. Temas sırasında konum
  tahmini kapısı algılayıcı hatası dahil kapanır.
  - S3'te de yetiyorsa, bilek algılayıcısı olmadan da kapanır.
  - S3'te "bilgi farkı" çıkarsa, model yalnız bilek algılayıcısı olmayan robotta yer bulur; elle yapılmış karşılığı
    donanımdır (bilek algılayıcısı takmak). O zaman öğrenilmiş tahminci protokolü yalnız kullanıcının robotunda bilek
    algılayıcısı yoksa yazılır.
- **S1 ya da S2'de "bilgi farkı":** bilgi farkı çıkan en düşük düzeyde öğrenilmiş tahminci (kuvvet-moment geçmişinden
  `e` kestiren küçük bir model) ayrı bir protokolle MOMENT-2R'ye karşı sınanır. **World model doğrudan açılmaz.**
- **Bir düzeyde "küçük pay":** o düzeyde model açılmaz.

**Önemli sınır:** algılayıcı hatasında DOKUN-KAHİN'e kalan farkın bir kısmı hiçbir tahmincinin alamayacağı türdendir.
Koşu başına sapmayı aynı algılayıcıyla kimse bilemez. Bu yüzden "bilgi farkı" sonucu modeli kanıtlamaz, yalnız onun
sınanmasını açar. MOMENT-2O, farkın ne kadarının algılayıcıdan geldiğini gösterir.

**Betimsel:**
- MOMENT-2T − MOMENT-2R (aktarımın bedeli) ve MOMENT-2R − MOMENT-2O (algılayıcının bedeli), düzey başına.
- `c` ve `e` hücrelerinde D2, gecikme dilimleri.
- İlk ölçümde kestirim hatası ve yön hatası.
- Nişan sayısı, yön yok oranı, boş yere tetiklenme.
- S0'da rakip deneyinin yeni tohumlarla tekrarı.

## Pilot

Tohumlar 930–934, model 0, karar için kullanılmaz. Sıra önemlidir; her adım bir öncekinin sonucunu kullanır.

- **P1, gerileme:** S0, `panda_rival`'ın saklı sonuçlarını (tohumlar 300–301, model 0, `T = 8`, itmesiz) hücre
  ortalamalarında 0.1 s içinde vermeli. PyBullet geçmiş gürültüsü koşu başına 1.4 s'ye kadar çıkabildiği için
  karşılaştırma tek koşu değil, ortalama üzerinden yapılır.
- **P2, algılayıcı denetimi (ayar değil):** her düzeyde, ilk ölçümdeki `|r̂ − r|` ve yön hatasının ortancası ve %90'ı.
  Düzeylerin yukarıdaki tablodaki etkileri gerçekten verdiğini gösterir.
- **P3, tetik eşiği:** her düzeyde `F_t ∈ {5, 10, 15} N` içinden, `e = 0` koşularında boş yere tetiklenme oranı
  %5'in altında kalan en küçüğü. Ortak mekaniktir, hiçbir politikaya göre ayarlanmaz. Hiçbiri tutmazsa 15 N ve not.
- **P4, kalibrasyon:** her düzey ve her `c` için `panda_rival` P1'in aynısı ve aynı bütçeyle: `e ∈ {4, 6, 8, 10}`,
  5 delik × 5 tohum, `d = a + b|r|` en küçük kareler. `R² < 0.5` ise sabit adım `c`. İşaret koşulu yok.
- **P5, ayar:** her düzeyde MOMENT-2R için `n_w ∈ {5, 10, 20}` × `R_MIN ∈ {1, 2, 4} mm`. Model 0, üç gecikme,
  `e ∈ {3, 6, 10}`, iki `c`, 5 delik × 5 tohum. Ortalama süreyi en küçük yapan seçilir; 0.01 s içinde eşitlikte
  küçük `n_w`, sonra küçük `R_MIN`. Yuvarlanmamış puanlar saklanır (rakip deneyindeki denetim notu). Ayar bilerek
  rakibin lehine.
- **P6, süre:** koşu başına süre. Toplam 12 saati geçerse MOMENT-2T ve MOMENT-2O 10 tohuma iner.

Ana koşu her işten sonra ara kayıt yazar ve oturumdan bağımsız (`nohup`) başlatılır.

## Bilinen zayıflıklar

- **Düzeyler varsayımdır.** Gerçek algılayıcı ölçülmedi. Sonuç, "hangi hata düzeyinde kopuyor" diye okunmalı;
  kullanıcının algılayıcısı tabloda nereye düşüyorsa oradaki sonuç geçerlidir.
- **Uyum denetimi gerçek kuvveti görüyor.** Gerçekte uyum da aynı algılayıcıyı kullanır ve sapma ucu yana kaydırır.
  Bu iki politikayı da etkiler ve burada gösterilmez.
- **Sapma koşu boyunca sabit.** Kola göre değişen sapma yok: eklem torku kestiriminde sapma duruşa bağlıdır, S3 bunu
  büyük sabit bir sapmayla temsil eder.
- **Algılayıcı dinamiği yok.** Süzgeç dışında gecikme ya da bant genişliği sınırı yok.
- **Temas geometrisi hâlâ kusursuz.** Eğik delik, dönme hatası, pah yok.
- **DOKUN-KAHİN kesin üst sınır değil.** `panda_rival`'daki not geçerli.
- **Başka bir elle yapılmış öznitelik denenmiyor.** Örneğin yanal kuvvetin yönü, momente göre kol hatasından
  etkilenmez. MOMENT-2R yetmezse, öğrenilmiş tahminciden önce böyle bir kuralın sınanması gerekebilir.
- `δ = 0.5 s` keyfi; düzeyler arası Bonferroni tutucu.

## Sapmalar

1. **P3'teki tetik kuralı S0'a göre yapıldı (pilottan önce).** Rakip deneyinin denetimi, ideal algılayıcıda bile
   `e = 0`'da tetiklenme oranının %4–7 olduğunu göstermişti; pim gerçekten deliğin duvarına sürtünüyor. Sabit "%5"
   kuralı S0'da bile eşiği yükseltebilirdi. Kural şu oldu: S0'ın `F_t = 5 N`'deki oranının en çok 2 puan üstü.
   Yani algılayıcının eklediği tetiklenmeler sınırlanır, temasın kendisi değil.
2. **Kod eklemeleri ve küçük bir yoklama (pilottan önce).**
   - Var olan davranışı değiştirmeyen iki kanca eklendi: `timesim.run_t`'ye isteğe bağlı bir ölçüm işlevi (`meas`),
     `rival.Moment2`'ye isteğe bağlı `r_min`. Duman testinde S0'daki MOMENT-2, rakip kodunun aynı koşusunu birebir
     verdi (7.95 s, 1 nişan).
   - MOMENT-2O'nun kalibrasyonu: gerçek momenti gördüğü için `panda_rival`'ın temiz kalibrasyonu kullanılır;
     `n_w` ve `R_MIN` MOMENT-2R'den gelir. Protokol metni "MOMENT-2R'nin ayarıyla" diyordu; gürültülü kalibrasyon
     kâhini haksız yere cezalandırırdı.
   - Duman testi gösterdi ki ilk ölçüm tetikten hemen sonra, `F_z` 5–10 N iken yapılıyor. Sapma `F_z`'ye bölündüğü
     için 3–5 kat büyüyor. "En az şu kuvvette ölç" (`F_m ∈ {0, 15, 25} N`) 12 koşuda yoklandı. Bu yoklamada
     tohum 300 kullanıldı; bu bir ana tohum, ama sonuca göre hiçbir şey seçilmedi.
     - Yön hatası azaldı: S1'de 19° → 13°, S2'de 53° → 33°.
     - Kestirim hatası düzelmedi, süre kötüleşti: S1'de 8.7 → 9.7–10.0 s. Kuvvet beklenirken uç hareket ediyor.

     Ayar ızgarasına eklenmedi. Kodda `f_m = 0` (etkisiz) olarak duruyor.
3. **Pilot sonuçları ve ek politika M2C (ana koşudan önce).** `results/pilot_sensor.txt`:
   - **P1 geçti:** S0 rakip deneyini veriyor; 36 hücrede ortalama fark −0.002 s, en kötü 0.038 s.
   - **P3:** boş yere tetiklenme hiçbir düzeyde yok, pilot tohumlarında S0 dahil 0.000. Her düzeyde `F_t = 5 N`.
   - **P4: kalibrasyon her düzeyde düştü** (R² < 0.5). Kurala göre her düzeyde sabit adım `c`.

     | Düzey | R² (c = 5 / 2) | İlk ölçüm: `|r̂| − |r|` ortancası | Yön hatası ortancası |
     |---|---|---|---|
     | S1 | 0.36 / 0.38 | 1.7 mm | 16–22° |
     | S2 | 0.01 | 11–12 mm | 53–60° |
     | S3 | 0.00 | 61 mm | 77–82° |
   - **P5:** `n_w = 5` her düzeyde; `R_MIN` S1 1 mm, S2 4 mm, S3 2 mm.
   - **P6:** 5.36 s/koşu.

   Zayıf bir uydurma bile `|e|`'nin tipik büyüklüğünü taşır (R² 0'da "≈ 7–8 mm git"). Sabit adım bunu atar; öğrenilmiş
   bir tahminci bu ön bilgiyi kolayca öğrenirdi. Kural yazıldığı amaçla uygulandığı için kararı yine sabit adımlı
   M2R verir. Ek olarak **M2C** (M2R'nin ayarı, P4 uydurması R²'ye bakılmadan tutulmuş) S1–S3'te bütün ızgarada
   betimsel olarak koşulur (+16.200 koşu; toplam 64.800, tahminen 10–11 saat).

   Okuma veriden önce yazıldı: bir düzeyde M2R "bilgi farkı", M2C "yetiyor" ya da "küçük pay" verirse, o düzeyde
   yazılacak öğrenilmiş tahminci protokolünün rakibi M2C olur.

   Kayıt testinde (tohumlar 400–401, 17 iş, yalnız kaydetmeyi sınamak için) M2C sabit adımdan kötü göründü. Yanlış
   yönde 7 mm atlamak, kısa adımdan pahalı. Sonuca göre bir şey değiştirilmedi.
4. **Ana koşudan sonra: denetim ve keşif (karar değişmedi).** Bağımsız bir ajan kodu ve veriyi denetledi; ona sonuç
   verilmedi.
   - **Doğrulananlar:**
     - Kayıtlı karar: üç düzeyde de "bilgi farkı". Ajan bunu kendi koduyla aynı buldu.
     - MOMENT-2 türlerine gerçek delik, `e` ya da gürültüsüz kuvvet sızmıyor.
     - Algılayıcı formülü protokolle birebir.
     - 648 iş eksiksiz; pilot değerleri seçme kuralına uyuyor.
   - **(a) Kararı okumayı değiştiren bulgu: protokolün bir iç çelişkisi.** "Önemli sınır" paragrafı, koşu başına
     sapmayı aynı algılayıcıyla kimsenin bilemeyeceğini varsayıyordu. Benzetimde ise bu sapma bilinebilir:
     - Sapma koşu boyunca sabit.
     - Temastan önce gerçek kuvvet tam sıfır; yerçekimi, kayma ve ivme yükü yok.

     Temastan hemen önce boşta yeniden sıfırlayan bir MOMENT-2R'yi ajan sınadı. Kurulumu:
     - Son 30 boşta tıkın ortalaması alınıyor, uç kenarın 3 mm'den fazla üstündeyken.
     - P4 yordamıyla, pilot tohumlarında yeniden kalibre edildi. S1'de R² 0.36'dan 0.79'a çıktı.
     - Ayarlanmadı.

     Model 0'da, tohum 400–409'da, DOKUN-KAHİN'e göre fark:

     | Düzey | Yeniden sıfırlayan | Aralık | M2R |
     |---|---|---|---|
     | S1 | +0.20 s | [0.08, 0.35] | +1.58 s |
     | S2 | +1.59 s | | +2.87 s |

     Bu kayıtlı bir sınama değil. Yalnız model 0'da, tohumların yarısıyla yapıldı ve DOKUN değerleri ana koşudan
     alındı. Yine de "Bilinen zayıflıklar"daki "öğrenilmiş tahminciden önce başka bir elle yapılmış kural sınanmalı"
     maddesinin bu sonucu belirlediğini gösteriyor. Fiziksel soru şu: S1'deki 0.1 N'lik kalan sapma temastan hemen
     önce mi ölçülüyor, yoksa görevin başında mı? İlkinde yeniden sıfırlama benzetimin basitleştirmesini sömürür.
     İkincisinde ise sıradan iyi uygulamadır.
   - **(b)** Yeniden kalibre edilen M2R, model 0'da S1 ve S3'te aktarılan M2T'den yavaş: S1'de 9.34 s'ye 8.94 s.
     Kural (R² < 0.5'te sabit adım) kullanılabilir bir ön bilgiyi atıyor. Kural yazıldığı gibi uygulandı.
   - **(c)** M2O, S2'de M2R'nin `R_MIN = 4 mm`'sini devralıyor. Bu yüzden S2'deki "kuralın bedeli / algılayıcının
     bedeli" ayrımı çarpık (M2O S2'de 8.81 s, S1'de 7.81 s, S3'te 7.95 s).
   - **(d)** İtme olmadan `e = 0` koşuları deliğe değmiyor. P3 yalnız 5 N seçebilirdi.
   - **(e)** S0 başvurusu yeni tohumlarda +0.21 s veriyor; rakip deneyinin 0.25 s'siyle uyumlu.
   - **Keşif (kayıtlı değil):** `explore/components.py`, `results/explore_components.txt`. M2R S1'de, model 0'da,
     pilot tohumlarında, her seferinde bir hata grubu kapatılarak koşuldu (D2, s):
     - tam +1.71
     - sapmasız +1.49
     - gürültüsüz +1.75
     - geometri hatasız +1.73
     - yalnız sapma +1.74

     Kalan hatalar arasında sapma baskın. Ama yeniden kalibre etmeden sapmayı kapatmak az kazandırıyor. Kayıp,
     pilotta düşen kalibrasyondan geliyor.
