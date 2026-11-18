# Hız kapısı protokolü

Sonuçlar görülmeden önce yazıldı (2026-11-01). Sonraki değişiklikler "Sapmalar" bölümüne işlenir.

Kuralla sınırlı kalan başarısızlıklar çoğunlukla zamandandır: robot sapmayı kapatmadan ağza varıyor, η bunu
çözmüyor. Burada η'ya dokunulmaz, ilerleme yavaşlatılır. World model için aday görev "şimdi girersem başarır
mıyım?" tahminidir. Önce el yapımı kapı sınanır; model ancak onun bıraktığı pay varsa gündeme gelir.

Fikir yeni değildir: DMP'lerde izleme hatasıyla fazı durdurma (phase stopping, Ijspeert ve ark.) bilinen bir
tekniktir. Atıf bellekten verildi, literatür taraması yapılmadı.

## Kapı

Kol `V = α(x) m(x) + η c(x)`. `d = ‖c(x)‖` metrikte ölçülür; analitik alanda bu tam `D`'dir, öğrenilmiş alanda ek
hesap gerektirmez. Eşik `L` için, yalnız ağzın üstündeki son düz inişte (`0 ≤ z − z_rim ≤ 0.12 m`):

    α = clip((2L − d) / L, 0, 1)

Bant dışında ve ağız altında `α = 1`. η hep `KURAL`'ın değeridir. `m` ölçeklense de kapanma hızı değişmez, çünkü `m` en
yakın noktada `D`'ye teğettir; bu türetme kapalı çevrimde gecikme altında sınanmış değildir, deney bunu da gösterir.

- Sabit kapı `KAPI0`: `L = 0.02`. Metrikte 0.05 yaklaşık 5 mm yanal hataya denk düşer. Yani 2 mm'de tam hız, 4 mm'de dur.
- Izgara: `L ∈ {0.01, 0.02, 0.04, 0.08}`.

## Koşullar

[PROTOKOL.md](PROTOKOL.md) ile aynı kollar, hücreler, delikler, tohumlar ve bozucular. Bozucu anı kapısız bozucusuz
koşudan ölçülür, `KURAL` aynı deneyde kapısız koşulur, böylece seçenekler **eşleştirilmiştir**. Kol başına
`48 × 5 × 100` = 24.000 koşu, toplam 120.000. `tf = T + 4 s` değişmez, kapı süre harcar ve bu bedel ölçüme dahildir.
Birincil ölçüt `SR_insert(c = 5 mm)`. Tohum 0–9 seçim, 10–19 test. Kararlar makale kolunda, üç modelin ortalamasında.

## Politikalar

| Politika | Tanım |
|---|---|
| `KURAL` | kapı yok |
| `KAPI0` | `L = 0.02`, seçim yok |
| `TABLOK` | her model ve `(T, h, τ)` için seçim yarısında en iyi `L` ya da kapısız |
| `KOŞU-KAHİN` | her koşu için en iyi seçenek, test yarısında; koşu başına tahmin eden bir modelin üst sınırı, iyimser yanlı |

## Karar

Bootstrap ve aralık [PROTOKOL.md](PROTOKOL.md) ile aynı: 2000 tekrar, ortalaması nokta değerine kaydırılmış yüzdelik.

- **H, kapı işe yarıyor mu:** `H = S(KAPI0) − S(KURAL)`. Geçmesi için `H ≥ 0.03` ve alt sınır `> 0`.
- **P, tabloya pay:** `P = S(TABLOK) − S(KAPI0)`, üst sınır `U_P`.
- **Q, koşu başına üst sınır:** `Q = S(KOŞU-KAHİN) − S(KAPI0)`.

| Sonuç | Karar |
|---|---|
| H kaldı | El yapımı kapı yetmiyor. Yavaşlatma bu görevde kazanç getirmedi, model bu görev için de açılmaz |
| H geçti, `Q < 0.03` | Kapı yetiyor, koşu başına kusursuz bir tahminci bile kayda değer kazanç bırakmıyor. Model gerekmiyor |
| H geçti, `P ≥ 0.03` | Koşula göre seçim pay bırakıyor. Önce daha basit bir kapı kuralı aranır, sonra model |
| H geçti, `P < 0.03 ≤ Q` | Karar yok, sonraki sınama gerekir: `Q` şansı da toplar. Seçim tohumlarında eğitilen basit bir koşu başına tahminci test tohumlarında `KAPI0`'ı `0.03` geçerse model adayı doğar |

`H` kalsa da `Q` raporlanır: seçeneklerden biri bazı koşularda işe yarıyorsa bu görülmelidir, ama karara girmez.

Betimsel: analitik ve zayıf kol, bozucusuz `SR_insert`, analitik kolda her η'da başarısız olan koşuların kaçının kurtulduğu, `c = 2, 10 mm`,
`T`, `Δ`, `h + τ` dilimleri. Kapının inişi geciktirip süreyi bitirdiği koşular `end_z` ile ayrıca sayılır.

## Sapmalar

1. **Karar tablosu deney başlamadan değişti.** `analyze_speed.py` sahte veriyle sınandı. Seçenekler arasında yalnız
   bağımsız gürültü varken de `KOŞU-KAHİN` 1.00 çıktı, `Q = 0.10` oldu ve ilk tablo "model adayı" diyordu. `Q` en çoğun
   yanlılığını taşıdığı için yalnız kapatıcı kullanılır: `Q < 0.03` kapatır, `Q ≥ 0.03` tek başına hiçbir şey açmaz.
2. **Kural deneyi koşulmadı, kullanıcı kararıyla (2026-11-01).** [PROTOKOL.md](PROTOKOL.md) deneyi başlamadan bırakıldı,
   hiçbir sonucu yok. Yani `η = 0.6 / (h + τ)` kuralının öğrenilmiş alanda sabit η'yı veya tabloyu geçtiği **ölçülmedi**.
   Burada `KURAL` yalnız kapının karşılaştırma tabanıdır. Kapısız koşular bu deneye alındı. Her η'da başarısız koşu
   sayımı yalnız analitik kolda yapılabilir, çünkü öğrenilmiş alanda η ızgarası yok.
3. **Pivot aralık yazdırılmadı.** [PROTOKOL.md](PROTOKOL.md) raporlanmasını istiyor, `analyze_speed.py` yapmıyor.
   Denetimin hesabı: `P` [−0.002, 0.020], `Q` [−0.004, 0.019]. Karara girmez.
4. **Bozucu saatle tetiklendiği için kapı erken yavaşlamadan pay aldı (sonuçtan sonra, denetimde görüldü).** `t_d`
   kapısız koşudan gelir. Alan yanlılığı `d > L` yaptığında kapılı robot `t_d` anında daha yüksektedir: `L = 0.02`'de
   makale kolunda durumların %32'si, `T = 4`, `h + τ = 0.13`'te 25 mm'ye kadar. Bozucu yüksekliğe bağlanıp kurtarılan
   koşular yeniden koşulunca `H` 0.103 [0.074, 0.136], `P` −0.0004, `Q` 0.0015 [0, 0.005]. Yani makale kolundaki
   `P = Q = 0.010` çoğunlukla bu etkidir ve `L = 0.01`'in en iyi görünmesi gerçek değildir. Ön-kayıtlı sonuç değişmedi.
   Bu yeniden koşu ön-kayıtlı değildir, yalnız makale ve analitik kolda, kısmi örnekle yapıldı.
5. **Takılma sayımı eksik kaldı.** `analyze_speed.py` sığ koşuları yalnız `KAPI0` ve makale kolunda sayıyor. Zayıf kolda
   `L = 0.01` gerçekten kilitleniyor (delik 2, z ≈ 0.357, `αm + ηc ≈ 0`): sığ koşu %4.7, kapısız taban %1.7. Taban
   kapıdan değil, `η = 20`, `T = 8`, delik 0 ve 4'te başlangıçtaki bir çökme noktasından geliyor. `KAPI0` hiçbir kolda
   takılma eklemedi.
6. **Kapılı bozucusuz koşu ölçülmedi.** `und` hep kapısız. Bozucusuz gecikme denetimde `T = 4`'te 190 ms'ye ulaştı.
