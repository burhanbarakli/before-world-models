# Öğrenilmiş alan protokolü

Başarı sonuçları görülmeden önce yazıldı (2026-11-01). Sonraki değişiklikler "Sapmalar" bölümüne işlenir.

**Durum: bu deney koşulmadı.** Kullanıcı kararıyla başlamadan bırakıldı, bkz. [PROTOKOL_KAPI.md](PROTOKOL_KAPI.md).
Alan eğitimi kısmı hız kapısı deneyinde kullanılıyor.

Şimdiye kadar bütün deneyler analitik alanla yapıldı. Tüp sınırı `ε_c + ε_m / η` η'yı aşağı çekmeyi cezalandırır,
kural ise gecikme büyüdükçe η'yı aşağı çeker. Gerçek bir alanda η gecikme dışında alan hatasına da bağlı olabilir.
World model için kalan tek ciddi yer burasıdır.

Soru: makalenin tarifiyle öğrenilmiş alanda `η = min(20, 0.6 / (h + τ))` hâlâ yetiyor mu, yoksa alan hatası
modelin kapatabileceği yeni bir pay açıyor mu?

Bu protokolden önce görülen: `panda_gate1` sonuçları, model 0'ın ve genişlik seçiminin **yalnız alan hatası**
(`field_error.py`). Öğrenilmiş alanla hiçbir kapalı çevrim koşusu yapılmadı, yalnız süre ölçümü için iki bozucusuz
koşu yapıldı, sonuçlarına bakılmadı.

## Alan

Makale C-B: beş yörünge, delik başına 100.000 düzgün ve 900.000 GMM örnek (std 0.05 R³, 0.1 SO(3)), ek olarak
referans noktalarında MSE. DeepOVec, 6 katman ReLU, iç çarpım boyutu 64, çıktı `T_x SE(3)`'e izdüşürülür.

Makaleden farklar, fark edilenler:

- Makalede "branch 6 × 1024" yazıyor, trunk ve parametre sayısı (12M) birbirini tutmuyor. Burada hem branch hem
  trunk 6 × 512, toplam 13M. Genişlik 1024 yarıda bırakıldı: daha yavaş, çalışma anında 4 kat pahalı.
- Toplu boyut 2048, 20.000 adım, Adam 3e-4 kosinüs. Makale bunları vermiyor.
- Eğitim `T = 8` referansında. Hız profili `t / T`'nin fonksiyonu olduğu için MVF tam olarak `1 / T` ile ölçeklenir
  (sayısal olarak doğrulandı, fark 0).
- Yörüngeler insan gösterimi değil, `panda_gate1`'in yeniden kurgulanmış referansları.

Modeller, her biri kendi verisinde:

| Kol | Model | Adım |
|---|---|---|
| Makale | 0, 1, 2 | 20.000 |
| Zayıf | 3 | 4.000 |
| Analitik | yok | |

Model 0'ın taze örneklerdeki hatası: makale örneklemesinde c rms 0.118, m rms 0.023; bozucu bölgesinde c rms 0.0079,
m rms 0.0026; aşağı inişte referans üstünde `|c_v|` 0.3–0.4 mm. Makalenin normalize MVF hatasına göre m/hız 0.028.

## Koşullar

Hücreler `panda_gate1/gate_rule.py` ile aynı delikler, tohum akışı ve bozucular, böylece kollar **eşleştirilmiştir**.
Taze değildir: bu koşulların analitik sonuçları görüldü. Sınanan şey yeni olan alandır.

- `h ∈ {20, 40, 70, 90} ms`, gerçek gecikmeler. `τ ∈ {0, 25, 40} ms`, `T ∈ {8, 4}`, `Δ ∈ {0.4, 0.25}`.
- η ızgarası `{4, 5, 6.5, 8, 10, 12, 16, 20}` ve kural. Kural gerçek `h` ile hesaplanır, `k` ve tavan ayarlanmaz.
- Delik başına 20 tohum. Hücre ve η başına 100 koşu, kol başına 43.200 koşu, toplam 216.000. `tf = T + 4 s`.
- Her iş için `t_rim` o alanla bozucusuz ölçülür, `t_d = t_rim − Δ`. Bozucusuz koşunun ölçümleri de saklanır.
- Birincil ölçüt `SR_insert(c = 5 mm)`, ikincil `c = 2, 10 mm`. Tohum 0–9 seçim, 10–19 test.

## Politikalar

Skorlar makale kolunun üç modelinin ortalaması, test yarısında.

| Politika | Tanım |
|---|---|
| `KURAL` | formül, seçim yok |
| `SABİT8` | η = 8 |
| `SABİT*` | üç modelin seçim yarısında en iyi tek η; modele bakmaz |
| `TABLO` | **her model** ve her `(T, h, τ)` için seçim yarısında en iyi η |
| `KAHİN` | model ve hücre başına test yarısının en iyisi; üst sınır, iyimser yanlı |

`TABLO` modelin kendi hatasını da görür. Bu nedenle `M`, η seçen bir modelin alacağı payın üst sınırına yakındır.

## Karar

Bootstrap: modeller, delikler, seçim ve test tohumları yeniden örneklenir, seçimler her tekrarda yenilenir, 2000 tekrar.
[Önceki deneyde](../panda_gate1/PROTOKOL_KURAL.md) yüzdelik üst sınırın aşağı yanlı olduğu görüldü (Sapma 3). Bu yüzden
burada **ortalaması nokta değerine kaydırılmış** yüzdelik aralık kullanılır: `q + (nokta − bootstrap ortalaması)`.
Pivot aralık da raporlanır, karara girmez. Üç modelle model belirsizliği kabadır.

- **A, alan yeterliliği:** `KURAL`'ın bozucusuz `SR_insert` değeri, makale kolunda bütün hücrelerin ortalamasında `≥ 0.90`.
- **G, geçerlilik:** `S(KAHİN) − S(SABİT8) ≥ 0.03`.
- **B, üstünlük:** `KURAL − SABİT8` ve `KURAL − SABİT*` için alt sınır `> 0`.
- **Y, yeterlilik:** `M = S(TABLO) − S(KURAL)`, üst sınır `U`.

| Sonuç | Karar |
|---|---|
| A kaldı | Alan bu görev için yetersiz. Kural sorusu sonuçsuz, önce alan iyileştirilir |
| G kaldı | Sonuçsuz. Bu koşullarda tek η yetiyor |
| B kaldı | Kural öğrenilmiş alana taşınmadı |
| B geçti, `M ≥ 0.03` | Kural yardımcı ama yetmiyor. Alan hatası pay açıyor, modelin yeri var, Kapı 2'nin gerekçesi doğar |
| B geçti, `M < 0.03 ≤ U` | Kural destekleniyor, küçük bir pay dışlanamıyor |
| B geçti, `U < 0.03` | Kural öğrenilmiş alanda da yetiyor. η seçen model gerekmiyor |

Betimsel olarak raporlanır, karara girmez:

- Öğrenme bedeli: analitik kol ile makale kolunun eşleştirilmiş `S` farkı, politika başına.
- Zayıf kol: aynı skorlar ve `M`, alan hatasıyla birlikte. Burada `M` büyürse bu bir hipotezdir, sonuç değildir.
- Model başına `M`, `T` ve `h + τ` dilimleri, `c = 2, 10 mm`, yer değiştirmiş yarılar.
- Analitik kolun `gate_rule.npz` ile aynı koşulda birebir tuttuğu denetlenir; tutmazsa deney geçersizdir.

## Sapmalar

1. **`analyze_learned.py` deney öncesi sahte veriyle sınandı, kurallar değişmedi.** Kural optimumdaysa "yetiyor",
   modele özgü en iyi η varsa ve kural bunu bilemiyorsa "taşınmadı", saf gürültüde "taşınmadı" sonucu verdi.
   Saf gürültüde G yine geçiyor, yani G tek başına kanıt sayılmaz. Önceden sabitlenmiş bir eksik kaldı: `M ≥ 0.03` ile
   B'nin kalması durumunda karar "taşınmadı"dır, ama bu durumda da `M` alan hatasının açtığı payı gösterebilir;
   `M` ayrıca raporlanır.
