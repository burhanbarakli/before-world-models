# Yeniden sıfırlayan rakip: algılayıcı farkını bir el kuralı kapatıyor mu?

Protokol: [PROTOKOL.md](PROTOKOL.md). Ana koşudan önce yazıldı; sapmalar 1–2 sonunda.

Kod:
- `tare.py`: TARE politikası ve ana koşu.
- `pilot_tare.py`: pilot.
- `analyze_tare.py`: karar.

Çıktılar `results/` altında. Algılayıcı deneyinin (`../panda_sensor`) devamıdır.

## Soru

Algılayıcı deneyinde yeniden kalibre edilen MOMENT-2R her düzeyde DOKUN-KAHİN'in çok gerisinde kaldı. Denetimin
gösterdiği neden:
1. Koşu başına sabit sapma, pilotta kalibrasyonu düşürüyor.
2. Rakip sabit adıma geçiyor.

Benzetimde temastan önce gerçek kuvvet sıfır. Bu yüzden boşta okunan değer sapmanın kendisi. **TARE**, MOMENT-2R'nin
temastan hemen önce yeniden sıfırlayan hâli:
- uç kenarın 3 mm'den fazla üstündeyken son 30 boşta tıkın ortalamasını alır;
- bu ortalamayı sonraki ölçümlerden çıkarır;
- kalibrasyonu yeniden ölçülür, ayarı yoktur;
- tetiği DOKUN-KAHİN'inkiyle aynıdır.

Koşullar:
- **Kullanıcının isteğiyle yalnız 2 tohum:** 500–501, yeni.
- Algılayıcı deneyinin ızgarası: S1–S3, modeller 0–2, 3 gecikme, `e ∈ {3, 6, 10} mm`, `c ∈ {5, 2} mm`, 5 delik.
- 4.860 koşu. DOKUN-KAHİN, MOMENT-2R ve TARE aynı tohumlarda.
- Karar kuralı algılayıcı deneyindekiyle aynı: `δ = 0.5 s`, %98.3 aralık.
- Tohum az olduğu için ikinci bir aralık da hesaplandı: model-delik hücreleri üzerinden, tohumlar sabit. İkisi
  ayrışırsa bir modele daha çok yer bırakan geçerli.

## Pilot (tohum 930–931)

| Düzey | Kalibrasyon R² (c = 5 / 2) | İlk ölçüm yön hatası | MOMENT-2R'de aynısı |
|---|---|---|---|
| S1 | **0.84 / 0.84**, tutuldu | 3–4° | R² 0.36, 16–22° |
| S2 | 0.28 / 0.32, sabit adım | 12–15° | 53–60° |
| S3 | 0.03 / 0.01, sabit adım | 39–65° | 77–82° |

Yeniden sıfırlama, sapmayı gürültü düzeyine indiriyor: kalan kuvvet hatası sapmanın yaklaşık %13'ü.

## Sonuç (kayıtlı kural)

| Düzey | DOKUN t / S | TARE t / S | M2R t / S | `DT = t(TARE) − t(DOKUN)` | Ana aralık | Hücre aralığı | Karar |
|---|---|---|---|---|---|---|---|
| S1 | 7.69 / 1.000 | 7.93 / 0.987 | 9.37 / 0.931 | **+0.24 s** | [0.08, 0.66] | [0.13, 0.40] | **küçük pay** |
| S2 | 7.69 / 1.000 | 9.41 / 0.939 | 11.47 / 0.713 | +1.72 s | [1.32, 1.98] | [1.58, 1.87] | bilgi farkı |
| S3 | 7.69 / 1.000 | 10.87 / 0.800 | 12.28 / 0.615 | +3.18 s | [2.36, 3.97] | [2.79, 3.61] | bilgi farkı |

**Kayıtlı okuma:**
- **S1:** "küçük pay".
  - Yeniden sıfırlama S1'deki farkı 1.68 s'den 0.24 s'ye indiriyor. Nokta kestirimi eşiğin epey altında.
  - Ama iki tohumla ana aralığın üst ucu 0.5'i aşıyor.
  - Önceden yazılan okumaya göre S1'de öğrenilmiş tahminci protokolü açık kalır ve rakibi TARE olur.
  - Karar sözcüğünün kendi anlamı ise "model yok, kanıt yükü modelde".
- **S2 ve S3:** TARE farkı yarıya indiriyor (S2'de 3.78'den 1.72 s'ye), ama bilgi farkı kalıyor. Oradaki herhangi bir
  öğrenilmiş tahminci protokolünün rakibi TARE.
- Dünya modeli doğrudan açılmaz.

### Fark nerede (betimsel)

- **Hücreye göre DT (s):**

  | | c = 5: e = 3 | e = 6 | e = 10 | c = 2: e = 3 | e = 6 | e = 10 |
  |---|---|---|---|---|---|---|
  | S1 | 0.00 | +0.05 | +0.05 | +0.09 | +0.10 | **+1.18** |
  | S2 | 0.00 | +0.04 | +0.58 | +0.40 | +2.80 | +6.51 |
  | S3 | 0.00 | +1.90 | +3.98 | +1.18 | +4.65 | +7.37 |
- **S1'de kalanın kaynağı:** 540 koşudan 7'si başarısız, hepsi `c = 2`, `e = 10` hücresinde.
  - 6'sında ilk `|r|` 2 mm'lik `R_MIN`'in altında kalıyor ve TARE doğrudan spirale düşüyor.
  - Kalibrasyon ters işaretli olduğu için küçük `|r|` aslında "uzakta" demek. Rakip deneyinde görülen aynı sorun.
  - `R_MIN` bu protokolde ayarsız 2 mm'ye sabitlendi; MOMENT-2R'nin S1 ayarı 1 mm seçmişti.
  - Başarılı koşularda fark yalnız +0.14 s.
  - Daha küçük bir `R_MIN` ile S1'in "yetiyor"a dönmesi olası, ama sınanmadı.
- **İlk ölçüm (TARE):**

  | Düzey | Yön hatası ortancası | Son kestirim hatası |
  |---|---|---|
  | S1 | 4.9° | 0.85 mm |
  | S2 | 20° | 2.65 mm |
  | S3 | 72° | 5.17 mm |

  S2 ve S3'te sıfırlamadan sonra kalan hatalar (hiza, ölçek, kol, gürültü) kalibrasyonu hâlâ bozuyor.

## Ne demek, ne demek değil

- **Demek:**
  - Algılayıcı deneyinin S1'deki büyük farkı (1.68 s) neredeyse tamamen bir el kuralıyla, yani temastan önce yeniden
    sıfırlamayla kapanıyor. Kalan 0.24 s'nin çoğu ayarsız bırakılmış bir eşikten geliyor.
  - S2 ve S3'te sıfırlamadan sonra da 1.7–3.2 s fark var. Öğrenilmiş bir tahmincinin bu benzetimde savunulabilir ilk
    yeri burası.
- **Fiziksel koşul:** bu sonuç, gerçek algılayıcıda temastan hemen önce yeniden sıfırlamanın sapmayı silebileceği
  varsayımına dayanıyor.
  - Sapma görevin başından sonra birikiyorsa, bu sıradan iyi uygulamadır.
  - 0.1 N temastan hemen önce de kalıyorsa, sonuç benzetimin basitleştirmesini sömürür.
- **Demek değil:**
  - S1'in kesin olarak kapandığı. İki tohum ve "küçük pay" kararı var.
  - S2 ve S3'te bir modelin kesin olarak kazanacağı. TARE orada sabit adımla çalışıyor; daha iyi bir el kuralı denenmedi
    (örneğin yanal kuvvet yönü ya da başka bir kalibrasyon).
  - Gerçek robotta bu sayıların çıkacağı. Düzeyler varsayım, uyum denetimi gerçek kuvveti görüyor.
- **Denetim:** bağımsız denetim yapılmadı, yalnız öz denetim (Sapma 2).
