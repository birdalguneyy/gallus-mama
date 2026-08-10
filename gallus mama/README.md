# 🐓 Gallus Mama - Web Sitesi & Yönetim Paneli

Gallus Mama için hazırlanmış modern, hızlı ve **Render.com** üzerinde kolayca yayınlanabilir (deploy edilebilir) web uygulaması.

---

## 🌟 Özellikler

- **Büyüleyici Ön Yüz (Ana Sayfa)**:
  - **Hero Alanı**: Dikkat çekici başlık, slogan ve CTA butonları.
  - **Biz Kimiz (Hakkımızda)**: Hikaye, vizyon ve kalite değerleri.
  - **Popüler Ürünler**: Admin paneli üzerinden öne çıkarılan lezzetlerin sergilendiği bölüm.
  - **Ürün Kataloğu & Kategori Filtreleme**: Anlık filtreleme desteği sunan dinamik ürün kataloğu.
  - **İletişim & Lokasyon**: Adres, telefon, e-posta ve çalışma saatleri.

- **Güvenli Yönetim Paneli (`/admin.html`)**:
  - **Giriş Şifresi**: `19071907` (Kullanıcı isteğine özel).
  - **Ürün Yönetimi**: Ürün ekleme, düzenleme, silme, popülerlik durumu (Ana sayfada öne çıkar) ve görsel belirleme.
  - **Kategori Yönetimi**: Yeni kategori ekleme, ikon ve açıklama düzenleme, silme.
  - **Site Bilgileri**: İletişim detayları ve sloganı anında panelden güncelleyebilme.
  - **Gerçek Zamanlı İstatistikler**: Ürün, kategori ve popüler öge sayaçları.

- **Render Uyumlu Backend (Express.js)**:
  - Harici veritabanı gerektirmeyen, otomatik yedeklemeli ve tohumlamalı (seeded) JSON veri yapısı (`data/database.json`).
  - Ortam değişkeni (Environment Variables) desteği: `PORT`, `ADMIN_PASSWORD`.

---

## 🚀 Yerel Çalıştırma (Local Development)

Projeyi bilgisayarınızda çalıştırmak için aşağıdaki adımları izleyin:

```bash
# 1. Bağımlılıkları yükleyin
npm install

# 2. Sunucuyu başlatın
npm start
```

Tarayıcınızda açın:
- **Ana Sayfa**: `http://localhost:3000`
- **Yönetim Paneli**: `http://localhost:3000/admin.html` (veya `http://localhost:3000/admin`)
- **Şifre**: `19071907`

---

## 🌐 Render.com Üzerinde Yayınlama (Deploy Rehberi)

Gallus Mama uygulamasını **Render.com** üzerinde ücretsiz yayınlamak çok kolaydır:

### Adım 1: Projeyi GitHub'a Yükleyin
1. GitHub hesabınızda `gallus-mama` isimli yeni bir repository oluşturun.
2. Bu klasördeki tüm kodları repository'nize push edin:
   ```bash
   git init
   git add .
   git commit -m "Gallus Mama initial release"
   git remote add origin https://github.com/KULLANICI_ADINIZ/gallus-mama.git
   git push -u origin main
   ```

### Adım 2: Render.com Üzerinde Web Service Oluşturun
1. [Render Dashboard](https://dashboard.render.com/)'a giriş yapın.
2. **New +** butonuna basıp **Web Service** seçin.
3. GitHub hesabınızı bağlayıp `gallus-mama` deposunu seçin.
4. Ayarları şu şekilde yapın:
   - **Name**: `gallus-mama`
   - **Environment**: `Node`
   - **Build Command**: `npm install`
   - **Start Command**: `npm start`
5. **Environment Variables** (Opsiyonel):
   - `ADMIN_PASSWORD`: `19071907` (Farklı bir şifre vermek isterseniz buradan değiştirebilirsiniz)
6. **Create Web Service** butonuna tıklayın!

🎉 Uygulamanız birkaç dakika içinde `https://gallus-mama.onrender.com` adresinde yayında olacaktır!

---

## 📁 Proje Yapısı

```
gallus mama/
├── data/
│   └── database.json    # Ürün, kategori ve site bilgileri veritabanı
├── public/
│   ├── css/
│   │   └── style.css    # Premium CSS Tasarım Sistemi (Glassmorphism, Responsive)
│   ├── js/
│   │   ├── app.js       # Ana sayfa dinamik içerik & filtreleme JS
│   │   └── admin.js     # Yönetim paneli auth & CRUD JS
│   ├── index.html       # Müşteri Ana Sayfası
│   └── admin.html       # Şifreli Yönetim Paneli
├── package.json         # Node.js bağımlılıkları ve scriptler
├── render.yaml          # Render otomatik yapılandırması
├── server.js            # Express REST API & Statik Dosya Sunucusu
└── README.md            # Kullanım ve kurulum kılavuzu
```
