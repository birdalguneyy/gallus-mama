# 🐓 Gallus Mama & Yumurta - E-Ticaret Web Uygulaması ve Dinamik Stok Paneli (Admin CMS)

`gallusmama.com` ("Gallus Mama & Yumurta") için geliştirilmiş uçtan uca çalışan, ultra-profesyonel, yüksek dönüşüm odaklı (CRO), modern E-Ticaret Web Uygulaması ve Dinamik Ürün/Stok Yönetim Paneli.

---

## 🎨 Marka Kimliği ve Tasarım Dili (UI/UX)
- **Renk Paleti**:
  - Arka Plan (Ana): `#FAF8F5` (Sıcak Kırık Beyaz / Organik Krem)
  - Yüzeyler & Kartlar: `#FFFFFF` (Saf Beyaz, `#E5E7EB` kenarlık ve yumuşak gölgeler)
  - Birincil Renk (Primary): `#1B4332` (Derin Orman Yeşili - Doğallık, güven ve prestij)
  - Vurgu Rengi (Accent / CTA): `#D97706` (Zengin Kehribar / Altın Sarısı - Sepete Ekle & Satın Alım butonları)
  - Tipografi: Plus Jakarta Sans & Inter
- **Teknoloji**: HTML5, Tailwind CSS (CDN), Lucide Icons, Modern Vanilla JavaScript (ES6+), LocalStorage senkronizasyonu.

---

## 🚀 Temel Özellikler

### 1. Müşteri Vitrini (Storefront)
- **Duyuru Bandı & Sticky Header**:
  - 750 TL üzeri ücretsiz kargo, günlük taze yumurta ve mama garantisi bilgi akışı.
  - Anlık çalışan akıllı arama çubuğu (başlık, kategori ve birime göre filtreler).
  - Hızlı kategori butonları (`Tümü`, `Doğal Yumurta`, `Köpek Maması`, `Kedi Maması`, `Kanatlı Yem`).
  - Dinamik ürün rozetli **Sepet Butonu** ve **Yönetici Paneli (Admin)** geçiş butonu.
- **Yüksek Dönüşümlü Hero Alanı**:
  - Split & Bento grid vitrin kartları.
  - Güven rozetleri: *Aynı Gün Kargo, %100 Doğal Üretim, Güvenli Ödeme, Faturalı Orijinal Mama*.
- **Akıllı Ürün Kartları & Dinamik Stok Rozetleri**:
  - **Stok > 10**: Yeşil rozet (`Stokta Var - X Adet`).
  - **1 <= Stok <= 10**: Turuncu uyarı rozeti (`Son X Ürün! - Pulse animasyonlu`).
  - **Stok == 0**: Kırmızı rozet (`Tükendi`), "Sepete Ekle" butonu pasif (`disabled`) ve grileşmiş.
- **Slide-Over Yandan Açılır Dinamik Sepet**:
  - Adet artırma/azaltma (Mevcut stok sınırını aşamayacak şekilde kilitli).
  - 750 TL ücretsiz kargo ilerleme çubuğu.
  - Kupon kodu desteği (`GALLUS10` ile %10 indirim).
  - Ara toplam, kargo ve genel toplam hesabı.
- **Siparişi Tamamla & Canlı Stok Düşümü**:
  - Ad, Soyad, Telefon, Teslimat Adresi ve Sipariş Notu girişi.
  - Ödeme Yöntemi Seçimi: Kredi Kartı / Kapıda Ödeme / WhatsApp ile Hızlı Sipariş.
  - **Kritik:** Sipariş onaylandığında satın alınan ürün adetleri **gerçek zamanlı olarak stoktan düşer** ve tüm vitrinde/yönetim panelinde anında güncellenir.
  - Başarılı sipariş sonrası sipariş özeti ve WhatsApp kargo takip bağlantısı.

### 2. Gelişmiş Yönetim ve Stok Paneli (Admin CMS)
- **Özet Metrik Kartları**:
  - Toplam Ürün Sayısı
  - Toplam Envanter Değeri (TL)
  - Kritik Stoktaki Ürünler (<5 adet)
  - Tükenen Ürünler (0 adet)
- **Canlı Stok & Envanter Tablosu**:
  - Arama ve kategori filtreli tablo.
  - **Tek tıkla hızlı stok artırma/azaltma (`+` / `-`)** ve doğrudan sayısal giriş.
  - Fiyat güncelleme, öne çıkarma toggle'ı ve silme işlemleri.
  - Yapılan değişiklikler anında mağaza vitrinine yansır.
- **Yeni Ürün Ekleme & Düzenleme**:
  - Ürün adı, kategori, birim, fiyat, stok adedi, görsel URL ve açıklama.
  - 6 adet tek tıkla uygulanabilir hazır şablon görsel seçici.
- **Gelen Siparişler**:
  - Mağazadan verilen siparişlerin anlık müşteri, adres ve sepet dökümü.
- **Varsayılan Verileri Geri Yükle**:
  - İstenildiğinde tek tıkla 10 zengin başlangıç ürününe (seed data) dönme olanağı.

---

## 💻 Çalıştırma Yöntemleri

### A. Doğrudan Tarayıcıda Açma (Sunucusuz / Offline)
1. `public/index.html` dosyasına çift tıklayarak herhangi bir modern tarayıcıda (Chrome, Edge, Safari, Firefox) doğrudan açabilirsiniz.
2. Tüm veriler `localStorage` üzerinden gerçek zamanlı çalışır, internet olmadan da yerel kurgu eksiksiz işler.

### B. Node.js Sunucusu ile Çalıştırma
```bash
# 1. Sunucuyu başlatın
node server.js
```
Tarayıcınızda açın:
- **Mağaza Vitrini**: `http://localhost:3000`
- **Yönetici Paneli**: `http://localhost:3000/admin.html` (veya sağ üstteki "Yönetici Paneli" butonu)

---

## 📦 Başlangıç Verileri (Seed Data)
1. **Lohmann Brown Gezen Tavuk Yumurtası (30'lu Organik Viyol)** - 165 ₺ (Stok: 42)
2. **XL Doğal Çift Sarılı Gezen Tavuk Yumurtası (15'li Özel Kutu)** - 95 ₺ (Stok: 7 - *Son 7 Ürün*)
3. **Gallus Gurme Çoban Köpeği & Büyük Irk Maması (15 Kg)** - 980 ₺ (Stok: 18)
4. **Gallus Premium Somonlu Kısırlaştırılmış Kedi Maması (10 Kg)** - 760 ₺ (Stok: 14)
5. **Gallus Puppy & Junior Kuzu Etli Yavru Köpek Maması (12 Kg)** - 840 ₺ (Stok: 4 - *Kritik Stok*)
6. **Gallus Tavuklu & Pirinçli Yetişkin Kedi Maması (15 Kg)** - 890 ₺ (Stok: 0 - *TÜKENDİ Örneği*)
7. **1. Sınıf Gezen Tavuk & Kanatlı Yumurta Yemi (50 Kg Çuval)** - 580 ₺ (Stok: 26)
8. **Pelet Civciv & Piliç Büyütme Geliştirme Yemi (25 Kg)** - 410 ₺ (Stok: 15)
9. **Otomatik Koruyucu Çiftlik Tavuk Yemliği & Nipelli Suluk Seti** - 340 ₺ (Stok: 6 - *Son 6 Ürün*)
10. **Gallus Doğal Dana İlikli Kemik & Kuzu Kulak Ödül Paketi** - 135 ₺ (Stok: 32)
