# Kapı 1 ön-kayıt protokolü: PyBullet Panda, gecikme altında başarı–η

Sonuçlar görülmeden önce yazıldı (2026-10-31). Sonraki değişiklikler "Sapmalar" bölümüne işlenir.

Soru: gerçekçi gecikme ve lag altında sabit η'nın başarısı anlamlı düşüyor mu, ve tek bir sabit η
bütün koşullara yetiyor mu? Cevap hayırsa bu görevde η seçen bir modele gerek yoktur.

Bu aşamada sinir ağı alanı ve world model yok. Alan analitik GVF'dir, yani öğrenilmiş bir alanın
ulaşabileceğinden iyi olması beklenir.

## Makaleden alınanlar

- SE(3) = SO(3) × R³, metrik `tr(Ṙ⊤Ṙ) + 100 ṗ⊤ṗ`. Dağılma ölçeği bu metrikte kimlikten uzaklık.
- `GVF = MVF + η CVF`, nokta sayısı 501, `θ̇ = J† V`, null-space terimi yok.
- PyBullet ve 7 serbestlikli Panda.
- Bozucu `x ← x · exp(ξ)` sağdan; ölçek 0.5, `t = 1 s`. `tf = 15 s`.
- Makale SR'si: `x(tf)` hedefe 0.2 (SO(3)) ve 0.02 m (R³) içinde.

## Makalede olmayan, bizim kurduğumuz

Şemsiye demonstrasyonları ve tutucunun ölçüleri yayımlanmamış; aramada kod veya veri bulunamadı.
Bu yüzden **sayılar makaleyle birebir karşılaştırılamaz.**

- 5 delik, `x = .40...60`, `y = −.16....16`, ağız yüksekliği 0.25 m, derinlik 0.06 m. (Sapma 1: yerleşim değişti.)
- Çubuk: tutma noktasından 0.25 m uzaklıkta takım çerçevesi, ucu çubuğun ucu.
- Referans: ortak başlangıçtan, deliğin 0.12 m üstünde dikey teğetle varan pürüzsüz eğri, sonra düz
  iniş. Dönme, eğrinin sonuna kadar biter. Hız profili başta sıfır değildir (yoksa `x₀` denge noktası
  olur), hedefte sıfırdır.
- Süre `T = 8 s` (normal), `T = 4 s` (hızlı). Her ikisinde `tf = 15 s`.
- Benzetim 500 Hz, kontrol 100 Hz. `Vmax = 3 · max‖ẋd‖`. Eklem hızı limitleri yön korunarak ölçeklenir.
- Temas benzetimi yok: başarı geometrik olarak denetlenir. Çubuk deliğe çarpıp sıkışmaz.

## Enjekte edilen tesis

- Gecikme `h ∈ {0, 10, 20, 50, 100, 150, 200, 300} ms`: eklem hızı komutu `h` sonra uygulanır.
- Lag `τ ∈ {0, 50, 150} ms`: eklem hızı komutunda birinci derece filtre.
- `η ∈ {0.5, 1, 2, 3, 5, 8, 12, 20}`.

**Gerçekçi küme R:** `h ≤ 100 ms`, `τ ≤ 50 ms`, iki `T` de. Bu sınır bizim varsayımımızdır.

## Bozucular

Delik başına 10 tohum, tüm koşullarda aynı. İki tür:

- `D1`: ölçek 0.5, `t = 1 s` (makale).
- `D2`: ölçek 0.2, `t = 0.6 T` (hedefe yakın).

Hücre başına 5 × 10 × 2 = 100 koşu. Ters kinematik hatası 1 mm üstündeyse tohum yeniden çekilir.

## Başarı

- **Birincil `SR_insert(c = 5 mm)`:** çubuk ucu ağız seviyesinin altındayken her adımda yanal hata
  `≤ c`, eğim `≤ atan(2c / 0.06)`, ve son derinlik hedef derinliğin en az %90'ı.
- İkincil: `c = 2, 10 mm` ve makale SR'si (dönme uzaklığı metrikte, `√2 θ ≤ 0.2`).

## Geçerlilik kontrolü

`h = 0, τ = 0, T = 8` için makale SR'sinde `η = 5`, `η = 0.5`'ten açıkça yüksek olmalı. Tutmazsa görev
tasarımı incelenir, ana analiz yapılmaz.

## Karar kuralları

Birincil ölçütte, hücre başına 100 koşu, Wilson %95 aralığı.

- **1a, sorun var mı:** R içinde en az bir koşulda en iyi sabit η'nın SR'si, aynı `T` için ideal koşulun
  (`h = 0, τ = 0`) en iyi SR'sinden en az 0.10 düşük ve aralıklar örtüşmüyor.
- **1b, seçim gerekli mi:** `η_rob`, R üzerinde ortalama SR'yi en yükselten tek sabit η. R içinde en büyük
  pişmanlık `max(SR_en_iyi − SR(η_rob)) ≥ 0.10` **ve** ortalama pişmanlık `≥ 0.03`.
- **1c, basit kural yeter mi:** yalnız 1b geçerse bakılır. Kural: `η = min(η_ideal, 1 / (2 (h + τ)))`,
  en yakın ızgara değerine yuvarlanır. Modelsiz bu kural, `η_rob`'un pişmanlığını en az yarıya
  indiriyorsa model için alan daralır.

Sonuçların anlamı:

| Sonuç | Karar |
|---|---|
| 1a kaldı, 1b kaldı | Bu görevde sorun yok. World model bu görevde yapılmaz |
| 1a geçti, 1b kaldı | Gecikme zarar veriyor ama tek η yetiyor. Model gerekmiyor |
| 1b geçti, 1c kural yetti | Seçim gerekli ama analitik kural yeterli. Model gerekmiyor |
| 1b geçti, kural yetmedi | Kapı 1 geçildi. Kapı 2'ye geçilir |

## Sapmalar

1. **Delik yerleşimi değişti, sonuçlar görüldükten sonra.** İlk koşuda (`results/gate1_v1.npz`,
   `analysis_v1.txt`) başarısızlıkların neredeyse tamamı `(0.60, 0.16)` deliğindeydi. `diag.py`: yol orada
   tekilliğe yaklaşıyor (σ_min ≈ 0.01), 4. eklem sınırına dayanıyor ve robot takılıyor. Bu, gecikmenin
   değil bizim yerleşimimizin sonucu. Yeni yerleşim yalnız kinematik paya göre seçildi, başarıya
   bakılmadı (`holes_check.py`: σ_min ≥ 0.12, eklem payı ≥ 0.63):
   `(.38,−.16), (.42,−.08), (.46,0), (.42,.08), (.38,.16)`. Karar kuralları değişmedi. İlk koşuda
   birincil sonuç: 1a geçti, 1b kaldı (en büyük pişmanlık 0.100, ortalama 0.028).
2. **Geçerlilik kontrolü tutmadı, `T = 15` kolu eklendi, `T = 15` sonuçları görülmeden.** İkinci koşuda
   `h = 0, τ = 0, T = 8` için makale SR'si bütün η'larda 1.00. Birincil sonuçlar bu noktada görülmüştü:
   1a kaldı, 1b kaldı. İnceleme (`inspect_sim.py`, keşifsel): `tf − T = 7 s` oturma süresi η = 0.5'in
   başarısızlığını siliyor; `T = 15`'te 20 koşuda η = 0.5 → 0.65, η = 5 → 1.00. Bu yüzden `T = 15`, R
   içinde (5 h × 2 τ × 8 η, hücre başına 100 koşu, `results/gate1_T15.npz`) ölçülür. Kurallar:
   geçerlilik, `T = 15, h = 0, τ = 0` için makale SR'sinde η = 5 ile η = 0.5'in Wilson aralıkları
   örtüşmez. Tutarsa 1a/1b/1c, R'nin `T ∈ {4, 8, 15}` birleşiminde aynı eşiklerle yeniden hesaplanır ve
   karar bu hesaptır. Tutmazsa kapı "geçersiz" kapanır. Karar eşikleri ve R'nin h, τ sınırları değişmedi.
3. **Denetimde bulunan küçük uygulama farkları, karara etkisiz.** Referans 501 değil 1501 noktadır
   (`UPSAMPLE = 3`). Lag filtresi Euler'dir, 50 ms için etkin τ 44.8 ms'dir; 501 nokta ve tam lag ile
   `T = 4, h = 100 ms, τ = 50 ms` hücresinde η = 3, 5, 8 yine 1.00. `analyze_gate.py`, 1c'de log ölçekte
   en yakın değere yuvarlar ve "yarıya indirme" testini içermez; 1b kaldığı için kullanılmadı.
   `test_se3.py` eski delik koordinatını sabit tutuyordu ve ikinci koşuda ilk bu assert'te durdu;
   düzeltilip koşuldu, bütün testler geçti.
4. **`T = 15` kolunda süre sınırı.** `tf = T` olduğundan `t = 1 s` bozucusunda koşuların yaklaşık %40'ı süre
   içinde hedef derinliğe inemiyor. Bu, kolun SR'sini η'dan bağımsız 0.80'e sınırlar. İdeal koşul da aynı
   sınıra takıldığı için 1a ve 1b karşılaştırmasını bozmaz. Yanal ve eğim ölçütleri η = 2–8 için 1.00.
