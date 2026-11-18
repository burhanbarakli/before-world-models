# S² / LASA ön-kayıt protokolü

Sonuçlar görülmeden önce yazıldı (2026-10-31). Sonradan yapılan her değişiklik bu dosyanın sonundaki
"Sapmalar" bölümüne işlenir.

Amaç iki soru:

1. Değişken η için türetilen teori sayısal olarak tutuyor mu?
2. Durum/ilerleme bağımlı η, en iyi sabit η'yı, ağırlıklardan bağımsız bir hedefte geçiyor mu?

Bu aşamada yalnızca analitik GVF var. Sinir ağı alanı ve world model yok.

## Kurulum

Makalenin verdiği:

- 30 LASA şeklinden `Multi_Models_*` dışındaki 26 tek şekil.
- GVF: `v = m(x) + η c(x)`, ayrık sistem (20): `x+ = exp_x( v/‖v‖ · min(‖v‖, Vmax) · Δt )`.
- S² gömülü, metrik Öklid iç çarpımı.

Makalenin vermediği, bizim seçtiklerimiz (varsayım):

- Eşleme: her şekil için tüm 7 demonstrasyonun sınır kutusu merkezi alınır, en uzak nokta merkeze
  1.0 rad olacak biçimde tek ölçekle ölçeklenir, kuzey kutbunda üstel haritayla S²'ye taşınır.
  Aynı şeklin demonstrasyonları aynı dönüşümü kullanır, ortak hedefleri korunur.
- Zaman: LASA'nın kendi zamanı. Referans hız merkezi farkla, sonra 5 noktalı hareketli ortalamayla
  alınır; hedef hızı 0 yapılır.
- `Δt = 0.005 s`, `Vmax = 3 · max‖ẋd‖`, rollout üst sınırı `4 T`, durma `d(x, hedef) < 1e-3`.
- Yakın nokta: 1000 tepeli polyline üzerinde büyük çember parçalarına izdüşüm; `m` parça üzerinde
  doğrusal, `x*`'tan `x`'e geodezik boyunca paralel taşınır.

## Teori kontrolleri (T)

Beklenen sonuçlar önceden yazılmıştır. Biri tutmazsa teori veya kod yanlıştır, çizelge deneyine
geçilmeden nedeni bulunur.

| No | Sınanan | Beklenti |
|---|---|---|
| T1 | Sürekli sınır, keyfi η(t) (anahtarlamalı, kaotik, duruma bağlı): `Ḋ + η(t) D ≤ 0` | Kalıntı `O(Δt)`; Δt yarıya inince yarıya iner |
| T2 | Eğri yakını ayrık adım, kırpmasız | `η Δt < 1` monoton, `1 < η Δt < 2` salınımlı sönüm, `η Δt > 2` ıraksama |
| T3 | Uç bölge, `m = 0`, azalan `η_k` | `d_k = d_0 Π(1 − η_k Δt)`. `η_k ∝ 1/k` hedefe gider, `η_k ∝ 1/k²` pozitif bir değerde takılır |
| T4 | Bozulmuş alan `f = m + e_m + η(c + e_c)`, en kötü yön | Tüp `ε_c + ε_m / η_min` sınırı aşılmaz ve sıkıdır; η artınca `ε_c` altına inmez |
| T5 | Komut gecikmesi `h`, Vmax kısıtsız | Eğri yakınında salınım başlangıcı `η h ≈ π/2`; `η h ≤ 1/e` için salınım yok |
| T6 | Sabit η'da makale davranışı | ME ve CR η ile monoton artar |

## Çizelge deneyi

### Birincil hedef

Demonstrasyonlar ayrılır: **referans 0; ayar 1, 2, 3; test 4, 5, 6.** Alan yalnız referansla kurulur.
Rollout, ayrılmış demonstrasyonun başlangıcından başlar ve o demonstrasyonla karşılaştırılır.
Bu, makalenin Fig. 4'teki ayar yöntemidir; hedef bizim ağırlıklarımıza bağlı değildir.

**Birincil ölçüt:** `DTW` — iki yol da yay uzunluğuna göre 200 noktaya örneklenir; geodezik maliyetli
simetrik DTW'nin hizalama yolu başına ortalaması (rad). Rollout hedefe varamazsa ölçüm olduğu gibi
kalır, DTW bunu cezalandırır.

**Doğrulama:** demonstrasyonlar döndürülerek aynı analiz: referans 3; ayar 4, 5, 6; test 0, 1, 2.

### İkincil ölçütler

Birincil karar bunlara bakmaz. Ölçüte bağımlılığı göstermek için raporlanırlar.

- `S`: Fréchet uzaklığı (birincilin duyarlılık kontrolü).
- `E`: fazla yol, `∫(‖ẋ‖ − ⟨ẋ, m̂⟩) dt`; `m ≈ 0` iken `m̂ = 0`. Şekil cezası.
- `Q`: `∫(D² + 0.05 ‖u − m‖²) dt`. Karesel takip cezası.
- Büyük ofset: başlangıç, referans başından 0.3 rad yana kaydırılmış. Ayrılmış demonstrasyon hedefi
  burada yoktur, yalnızca `E` ve `Q` raporlanır.

Analitik öngörü (düz uzay, sonuçlardan önce):

- `E` yalnız yan hız `y = η D` üzerinden konveks olduğundan, `D`'ye doğrudan bağlı olmayan her ceza
  için en iyi çözüm **sabit yaklaşma açısıdır**: `y ∝ ‖m‖`. Yani `η = ρ ‖m‖ / D`.
- `Q` LQR biçimindedir: en iyi çözüm **sabit η**'dır.

Bu yüzden A ailesinin `E`'de sabit η'yı geçmesi, `Q`'da geçmemesi beklenir. Öngörü `E`/`Q` için
tutmazsa türetme veya uygulama gözden geçirilir.

### Politikalar

Sabit ızgara: `η ∈ {0.25, 0.5, 1, 2, 3, 5, 8, 12, 20, 30}`.

| Ad | Tanım | Ayar |
|---|---|---|
| `F_global` | Tek sabit η, tüm şekiller | Ayar demolarında ortalama DTW |
| `F_letter` | Şekil başına sabit η (**karşılaştırma tabanı**, Fig. 4) | Şeklin ayar demoları |
| `A` | `η = clip(ρ ‖m‖ / D, 1, 30)`, `ρ ∈ {.02,.05,.1,.2,.3,.5,.8,1.2,2,4}` | Şeklin ayar demoları |
| `P` | `η = a + (b − a) s²`, `s` yay uzunluğu oranı, `a ≤ b`, `a,b ∈ {.25,.5,1,2,5,10}` | Şeklin ayar demoları |
| `F_oracle` | Şekil başına test setinde en iyi sabit η (tavan, politika değil) | Test |

Her politikanın η'sı `[0.25, 30]` içindedir, yani T1 ve ortak Lyapunov sonucu kapsamındadır.

### Karar kuralları

Birim şekildir (n = 26). Her şekilde test demolarının ortalaması alınır.

- **Pay kapısı:** medyan `(en kötü ızgara − en iyi ızgara) / en iyi ızgara ≥ 0.20`. Sağlanmazsa
  LASA'nın ayrılmış demoları η'ya duyarsızdır; çizelge sonucu "ölçülemedi" sayılır, "başarısız" değil.
- **Çizelge kazancı:** `A` veya `P` için, `F_letter`'a göre medyan göreli iyileşme `≥ %10` **ve**
  tek yönlü Wilcoxon, Holm ile `p < 0.01`, **ve** döndürülmüş ayrımda aynı yönde medyan iyileşme `> 0`.
- **Bu aşamanın sonucu:** çizelge kazancı gelirse LASA/S² şekil görevi çizelgelemenin birincil
  bulgularından olur. Gelmezse çizelge iddiası bu görevde düşer; PyBullet kapısı 1 yine yapılır, çünkü
  o gecikme altındaki soruyu ölçer.

Sonuçlara bakıp politika ailesi veya ızgara eklenirse, eklenenler keşifsel diye etiketlenir ve karar
kuralına girmez.

## Sapmalar

Hepsi sonuçlar görüldükten sonra işlendi.

1. **dt hatası düzeltildi.** İlk çalıştırmada `Field`, referans demonstrasyonun kendi zamanı yerine
   şeklin ortalama `dt`'sini kullandı; bu, "LASA'nın kendi zamanı" ifadesine aykırıydı (referans 0
   için medyan %12 ölçek farkı). Düzeltilip her şey yeniden çalıştırıldı. Denetçinin aynı düzeltmeyle
   yaptığı tam tekrar karar sonucunu değiştirmedi.
2. **Rollout kaydı.** Döngü erken bitince son 1-3 adım yola eklenmiyordu; düzeltildi.
3. **Pay kapısı tanımı.** Protokol hangi demoların kullanılacağını açıkça yazmıyordu. `analyze.py`
   3 test demosunu kullanır. Denetçi: 20T ufkuyla ve 6 demonun tümüyle değer 0.1985 oluyor, yani
   0.20 eşiğinin hemen altında. Pay kapısı bu yüzden sınırda sayılmalı.
4. **T1 beklentisi tutmadı.** LASA'da kalıntı Δt ile düşmedi. `t1b.py` nedeni gösterdi: düzgün eğride
   kalıntı Δt ve nokta aralığıyla sıfıra gider, yani LASA kalıntısı referansın pürüzünden gelir.
5. **E öngörüsü ilk haliyle tutmadı.** `A` için η tabanı 1 seçilmişti, bu da onu sabit açı bölgesinin
   dışında bıraktı; bu protokol tasarım hatasıdır. `explore.py` tabanı 0.25 yapan `A2`'yi ve 0.25
   altındaki sabit η'yı keşifsel olarak dener; karar kuralına girmez.
