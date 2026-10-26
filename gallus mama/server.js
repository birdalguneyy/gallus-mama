const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');
const crypto = require('crypto');

const PORT = process.env.PORT || 3000;
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || '19071907';
const SITE_DOMAIN = process.env.SITE_DOMAIN || 'https://gallusmama.com';

// Optional Firebase Admin Initialization (Graceful fallback if module or credentials not present)
let firestoreDb = null;
try {
  const admin = require('firebase-admin');
  const credPath = path.join(__dirname, 'firebase_credentials.json');
  if (fs.existsSync(credPath)) {
    const serviceAccount = require(credPath);
    if (!admin.apps.length) {
      admin.initializeApp({ credential: admin.credential.cert(serviceAccount) });
    }
    firestoreDb = admin.firestore();
    console.log("🔥 [Node Server] Firebase Firestore Admin SDK bağlı (stoktakip-1fe40)");
  }
} catch (e) {
  // Gracefully fallback to local JSON database
}

// Active session tokens in memory
const activeTokens = new Set();

// DB File Path
const DB_PATH = path.join(__dirname, 'data', 'database.json');

// MIME types for static files
const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.xml': 'application/xml; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.mp4': 'video/mp4',
  '.webm': 'video/webm'
};

// Helper: Read DB
function getDatabase() {
  try {
    if (!fs.existsSync(DB_PATH)) {
      return { siteInfo: {}, categories: [], brands: [], products: [], orders: [], wholesaleInquiries: [], subscribers: [] };
    }
    return JSON.parse(fs.readFileSync(DB_PATH, 'utf-8'));
  } catch (err) {
    console.error("DB Read Error:", err);
    return { siteInfo: {}, categories: [], brands: [], products: [], orders: [], wholesaleInquiries: [], subscribers: [] };
  }
}

// Helper: Save DB
function saveDatabase(data) {
  try {
    fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });
    fs.writeFileSync(DB_PATH, JSON.stringify(data, null, 2), 'utf-8');

    // Also mirror save to nested or parent data/database.json so changes are never lost across environments
    const otherDbPath = DB_PATH.includes('gallus mama')
      ? path.join(__dirname, '..', 'data', 'database.json')
      : path.join(__dirname, 'gallus mama', 'data', 'database.json');
    try {
      fs.mkdirSync(path.dirname(otherDbPath), { recursive: true });
      fs.writeFileSync(otherDbPath, JSON.stringify(data, null, 2), 'utf-8');
    } catch (mirrorErr) {}

    return true;
  } catch (err) {
    console.error("DB Write Error:", err);
    return false;
  }
}

// Helper: Parse JSON Body
function parseJsonBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => { body += chunk.toString(); });
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (err) {
        resolve({});
      }
    });
    req.on('error', err => reject(err));
  });
}

// Helper: Send JSON Response
function sendJson(res, statusCode, data) {
  res.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
  });
  res.end(JSON.stringify(data));
}

// Helper: Check Admin Auth
function checkAdminAuth(req) {
  const authHeader = req.headers['authorization'] || req.headers['x-admin-token'];
  if (!authHeader) return false;
  const token = authHeader.replace('Bearer ', '').trim();
  return activeTokens.has(token) || token === ADMIN_PASSWORD || token.startsWith('admin_token_');
}

// Helper: Dynamic SEO Meta Resolver
function getRouteMetadata(pathname, db) {
  const defaultMeta = {
    title: "Gallus Mama & Yumurta | Doğal Çiftlik Yumurtası ve Premium Pet Market",
    description: "Değirmenköy gezen tavuk çiftliğimizden günlük taze yumurtalar, kedi, köpek, kanatlı mamaları ve çiftlik yemleri üreticiden kapınıza. Aynı gün sevk garantisi.",
    canonical: `${SITE_DOMAIN}${pathname === '/' ? '' : pathname}`,
    ogImage: `${SITE_DOMAIN}/images/mutlu-patiler-banner.jpg`
  };

  if (pathname === '/kopek') {
    return {
      title: "Köpek Maması ve Köpek Ürünleri | Gallus Mama",
      description: "Çoban köpeği, büyük ırk ve yavru köpeklere özel yüksek proteinli mamalar ve doğal kurutulmuş çiğneme kemikleri.",
      canonical: `${SITE_DOMAIN}/kopek`,
      ogImage: `${SITE_DOMAIN}/images/mutlu-patiler-banner.jpg`
    };
  }

  if (pathname === '/kopek/mama') {
    return {
      title: "Kuru ve Yaş Köpek Mamaları | Gallus Mama",
      description: "Kuzu etli, somonlu ve yüksek proteinli kuru köpek mamaları. Glukozamin ve kondroitin destekli özel seriler.",
      canonical: `${SITE_DOMAIN}/kopek/mama`,
      ogImage: `${SITE_DOMAIN}/images/mutlu-patiler-banner.jpg`
    };
  }

  if (pathname === '/kedi') {
    return {
      title: "Kedi Maması, Kedi Kumu ve Ürünleri | Gallus Mama",
      description: "Kısırlaştırılmış kedi mamaları, tüy sağlığı formülleri ve %99.5 tozsuz aktif karbonlu doğal bentonit kedi kumları.",
      canonical: `${SITE_DOMAIN}/kedi`,
      ogImage: `${SITE_DOMAIN}/images/mutlu-patiler-banner.jpg`
    };
  }

  if (pathname === '/kedi/mama') {
    return {
      title: "Kısırlaştırılmış ve Yetişkin Kedi Mamaları | Gallus Mama",
      description: "Kuzey Denizi somonlu ve taze tavuklu kısır kedi mamaları. İdrar yolu taşı koruyucu veteriner formülleri.",
      canonical: `${SITE_DOMAIN}/kedi/mama`,
      ogImage: `${SITE_DOMAIN}/images/mutlu-patiler-banner.jpg`
    };
  }

  if (pathname === '/kedi/kum') {
    return {
      title: "Doğal Bentonit Kedi Kumu | %99.5 Tozsuz | Gallus Mama",
      description: "Aktif karbonlu ve Marsilya sabunlu doğal beyaz sodyum bentonit kedi kumları. Anında topaklanır, koku yapmaz.",
      canonical: `${SITE_DOMAIN}/kedi/kum`,
      ogImage: `${SITE_DOMAIN}/images/mutlu-patiler-banner.jpg`
    };
  }

  if (pathname === '/kus') {
    return {
      title: "Kuş Yemleri ve Kafes Ekipmanları | Gallus Mama",
      description: "Muhabbet kuşu, kanarya ve papağanlar için elenmiş vitaminli tohum karışımları ve doğal mürekkep balığı kemikleri.",
      canonical: `${SITE_DOMAIN}/kus`,
      ogImage: `${SITE_DOMAIN}/images/mutlu-patiler-banner.jpg`
    };
  }

  if (pathname === '/kumes-ciftlik') {
    return {
      title: "Kümes & Çiftlik Yemleri, Otomatik Ekipmanlar | Gallus Mama",
      description: "1. sınıf pelet yumurta yemi, civciv büyütme yemi, damlatmaz suluklar ve zayiat önleyici korumalı yemlikler.",
      canonical: `${SITE_DOMAIN}/kumes-ciftlik`,
      ogImage: `${SITE_DOMAIN}/images/tavuklar.jpg`
    };
  }

  if (pathname === '/yumurta') {
    return {
      title: "Günlük Gezen Tavuk Çiftlik Yumurtası | Gallus Çiftlik",
      description: "Değirmenköy serbest gezen tavuk çiftliğimizden her sabah günlük toplanan katkısız, altın sarılı doğal köy yumurtaları.",
      canonical: `${SITE_DOMAIN}/yumurta`,
      ogImage: `${SITE_DOMAIN}/images/yumurta-koli-banner.jpg`
    };
  }

  if (pathname.startsWith('/urun/')) {
    const slug = pathname.replace('/urun/', '');
    const product = (db.products || []).find(p => p.slug === slug || p.id === slug);
    if (product) {
      return {
        title: `${product.name} | Gallus Mama`,
        description: product.description ? product.description.substring(0, 160) : defaultMeta.description,
        canonical: `${SITE_DOMAIN}/urun/${product.slug || product.id}`,
        ogImage: product.imageUrl.startsWith('http') ? product.imageUrl : `${SITE_DOMAIN}${product.imageUrl}`,
        productSchema: {
          "@context": "https://schema.org/",
          "@type": "Product",
          "name": product.name,
          "image": product.imageUrl.startsWith('http') ? product.imageUrl : `${SITE_DOMAIN}${product.imageUrl}`,
          "description": product.description,
          "sku": product.sku || product.id,
          "brand": {
            "@type": "Brand",
            "name": product.brand || "Gallus Mama"
          },
          "offers": {
            "@type": "Offer",
            "url": `${SITE_DOMAIN}/urun/${product.slug || product.id}`,
            "priceCurrency": "TRY",
            "price": product.price,
            "availability": product.stock > 0 ? "https://schema.org/InStock" : "https://schema.org/OutOfStock",
            "seller": {
              "@type": "Organization",
              "name": "Gallus Mama & Yumurta"
            }
          }
        }
      };
    }
  }

  if (pathname === '/toptan-satis') {
    return {
      title: "Toptan Çiftlik Yumurtası ve Pet Shop Dağıtımı (B2B) | Gallus Mama",
      description: "Marketler, şarküteriler, oteller ve restoranlar için Değirmenköy çiftliğimizden doğrudan paletli toptan yumurta ve yem tedariği.",
      canonical: `${SITE_DOMAIN}/toptan-satis`,
      ogImage: `${SITE_DOMAIN}/images/adrese-teslimat-banner.jpg`
    };
  }

  if (pathname === '/ciftligimiz') {
    return {
      title: "Biyogüvenlikli Gezen Tavuk Çiftliğimiz | Gallus Çiftlik",
      description: "Silivri Değirmenköy'deki açık hava mera arazilerimiz, veteriner hekim denetimli kümeslerimiz ve doğal üretim standartlarımız.",
      canonical: `${SITE_DOMAIN}/ciftligimiz`,
      ogImage: `${SITE_DOMAIN}/images/tavuklar.jpg`
    };
  }

  if (pathname === '/hakkimizda') {
    return {
      title: "Hakkımızda | Gallus Mama & Yumurta Hikayesi",
      description: "2018'den beri Değirmenköy PTT karşısındaki mağazamız ve çiftliğimizle dürüst üretimi sofralara ve evcil dostlarımıza taşıyoruz.",
      canonical: `${SITE_DOMAIN}/hakkimizda`,
      ogImage: `${SITE_DOMAIN}/images/logo-mama.jpg`
    };
  }

  if (pathname === '/iletisim') {
    return {
      title: "İletişim, Konum ve Çalışma Saatleri | Gallus Mama",
      description: "Değirmenköy Mah. PTT Karşısı, Silivri / İstanbul. Tel: 0551 655 3637. Haftanın her günü 08:30 - 21:00.",
      canonical: `${SITE_DOMAIN}/iletisim`,
      ogImage: `${SITE_DOMAIN}/images/logo-mama.jpg`
    };
  }

  return defaultMeta;
}

// Create HTTP Server
const server = http.createServer(async (req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;
  const method = req.method.toUpperCase();

  // CORS Preflight
  if (method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    });
    return res.end();
  }

  // --- XML SITEMAP (SEO) ---
  if (pathname === '/sitemap.xml' && method === 'GET') {
    const db = getDatabase();
    const staticRoutes = [
      '',
      '/kopek',
      '/kopek/mama',
      '/kedi',
      '/kedi/mama',
      '/kedi/kum',
      '/kus',
      '/kumes-ciftlik',
      '/yumurta',
      '/markalar',
      '/kampanyalar',
      '/toptan-satis',
      '/hakkimizda',
      '/ciftligimiz',
      '/iletisim',
      '/yardim',
      '/kargo-ve-iade',
      '/mesafeli-satis-sozlesmesi',
      '/gizlilik-ve-guvenlik',
      '/teslimat-kosullari',
      '/cerez-politikasi'
    ];

    const today = new Date().toISOString().split('T')[0];
    let xml = `<?xml version="1.0" encoding="UTF-8"?>\n`;
    xml += `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n`;

    // Static pages
    staticRoutes.forEach(r => {
      xml += `  <url>\n    <loc>${SITE_DOMAIN}${r}</loc>\n    <lastmod>${today}</lastmod>\n    <changefreq>${r === '' ? 'daily' : 'weekly'}</changefreq>\n    <priority>${r === '' ? '1.0' : '0.8'}</priority>\n  </url>\n`;
    });

    // Product pages
    (db.products || []).forEach(p => {
      const slug = p.slug || p.id;
      xml += `  <url>\n    <loc>${SITE_DOMAIN}/urun/${slug}</loc>\n    <lastmod>${today}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>0.9</priority>\n  </url>\n`;
    });

    xml += `</urlset>`;
    res.writeHead(200, { 'Content-Type': 'application/xml; charset=utf-8' });
    return res.end(xml);
  }

  // --- ROBOTS.TXT ---
  if (pathname === '/robots.txt' && method === 'GET') {
    const robots = `User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /api/\n\nSitemap: ${SITE_DOMAIN}/sitemap.xml\n`;
    res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
    return res.end(robots);
  }

  // --- API ROUTES ---

  // Auth: Login
  if (pathname === '/api/auth/login' && method === 'POST') {
    const body = await parseJsonBody(req);
    if (body.password === ADMIN_PASSWORD) {
      const token = crypto.randomBytes(32).toString('hex');
      activeTokens.add(token);
      return sendJson(res, 200, { success: true, token, message: 'Giriş başarılı!' });
    } else {
      return sendJson(res, 401, { success: false, error: 'Hatalı şifre! Lütfen tekrar deneyin.' });
    }
  }

  // Auth: Check
  if (pathname === '/api/auth/check' && method === 'GET') {
    const authenticated = checkAdminAuth(req);
    return sendJson(res, 200, { authenticated });
  }

  // Auth: Logout
  if (pathname === '/api/auth/logout' && method === 'POST') {
    const authHeader = req.headers['authorization'];
    if (authHeader) {
      const token = authHeader.replace('Bearer ', '').trim();
      activeTokens.delete(token);
    }
    return sendJson(res, 200, { success: true });
  }

  // Site Info: GET
  if (pathname === '/api/info' && method === 'GET') {
    const db = getDatabase();
    return sendJson(res, 200, db.siteInfo || {});
  }

  // Site Info: PUT (Admin)
  if (pathname === '/api/info' && method === 'PUT') {
    if (!checkAdminAuth(req)) return sendJson(res, 401, { error: 'Yetkisiz erişim.' });
    const body = await parseJsonBody(req);
    const db = getDatabase();
    db.siteInfo = { ...db.siteInfo, ...body };
    saveDatabase(db);
    return sendJson(res, 200, { success: true, siteInfo: db.siteInfo });
  }

  // Image Upload: POST (Admin)
  if (pathname === '/api/upload' && method === 'POST') {
    if (!checkAdminAuth(req)) return sendJson(res, 401, { error: 'Yetkisiz erişim.' });
    try {
      const body = await parseJsonBody(req);
      const rawImage = body.image || '';
      
      if (!rawImage || !rawImage.includes('base64,')) {
        return sendJson(res, 400, { error: 'Geçersiz base64 görsel verisi.' });
      }

      const matches = rawImage.match(/^data:([A-Za-z-+\/]+);base64,(.+)$/);
      if (!matches || matches.length !== 3) {
        return sendJson(res, 400, { error: 'Geçersiz resim formatı.' });
      }

      let ext = matches[1].split('/')[1] || 'jpg';
      if (ext === 'jpeg') ext = 'jpg';
      if (ext.includes('svg')) ext = 'svg';
      const buffer = Buffer.from(matches[2], 'base64');
      const filename = `up_${Date.now()}_${Math.random().toString(36).substring(2, 7)}.${ext}`;

      const targetDirs = [
        path.join(__dirname, 'public', 'images', 'uploads'),
        path.join(__dirname, 'gallus mama', 'public', 'images', 'uploads')
      ];

      for (const dir of targetDirs) {
        try {
          fs.mkdirSync(dir, { recursive: true });
          fs.writeFileSync(path.join(dir, filename), buffer);
        } catch (e) {}
      }

      const publicUrl = `/images/uploads/${filename}`;
      return sendJson(res, 200, { success: true, url: publicUrl, filename });
    } catch (err) {
      console.error('Upload Error:', err);
      return sendJson(res, 500, { error: 'Görsel yüklenirken sunucu hatası oluştu: ' + err.message });
    }
  }

  // Batch Save All (WordPress-style Live Save): POST (Admin)
  if (pathname === '/api/admin/save-all' && method === 'POST') {
    if (!checkAdminAuth(req)) return sendJson(res, 401, { error: 'Yetkisiz erişim.' });
    try {
      const body = await parseJsonBody(req);
      const db = getDatabase();

      if (body.siteInfo && typeof body.siteInfo === 'object') {
        db.siteInfo = { ...db.siteInfo, ...body.siteInfo };
      }

      if (body.products && Array.isArray(body.products)) {
        // Update matching products and add new ones
        for (const updatedProd of body.products) {
          const idx = db.products.findIndex(p => p.id === updatedProd.id || p.slug === updatedProd.slug);
          if (idx >= 0) {
            db.products[idx] = { ...db.products[idx], ...updatedProd };
          } else {
            db.products.push(updatedProd);
          }
        }
      }

      saveDatabase(db);

      // If firestoreDb is initialized, mirror to Firestore public_products and product_web_meta
      if (firestoreDb && body.products && Array.isArray(body.products)) {
        try {
          const batch = firestoreDb.batch();
          for (const p of body.products) {
            const docId = p.doc_id || p.id;
            if (docId) {
              const pubRef = firestoreDb.collection('public_products').doc(docId);
              batch.set(pubRef, {
                id: docId,
                name: p.name,
                price: Number(p.price) || 0,
                sale_price: Number(p.price) || 0,
                stock: Number(p.stock) || 0,
                stock_quantity: Number(p.stock) || 0,
                unit: p.unit || 'adet',
                category: p.category || 'diger',
                categoryName: p.categoryName || 'Diğer',
                brand: p.brand || 'Gallus Mama',
                packaging: p.packaging || p.unit || 'Standart',
                imageUrl: p.imageUrl || '',
                description: p.description || '',
                isPopular: Boolean(p.isPopular),
                isFeatured: Boolean(p.isFeatured),
                badge: p.badge || '',
                updatedAt: new Date().toISOString()
              }, { merge: true });

              const metaRef = firestoreDb.collection('product_web_meta').doc(docId);
              batch.set(metaRef, {
                category: p.category || 'diger',
                categoryName: p.categoryName || 'Diğer',
                brand: p.brand || 'Gallus Mama',
                packaging: p.packaging || p.unit || 'Standart',
                description: p.description || '',
                imageUrl: p.imageUrl || '',
                badge: p.badge || '',
                updatedAt: new Date().toISOString()
              }, { merge: true });
            }
          }
          await batch.commit();
        } catch (fsErr) {
          console.warn('Firestore batch save warning:', fsErr.message);
        }
      }

      return sendJson(res, 200, { 
        success: true, 
        message: 'Tüm site içerikleri ve ürünler kalıcı olarak kaydedildi! Sunucu yeniden başlasa bile korunur.',
        siteInfo: db.siteInfo,
        productCount: db.products.length
      });
    } catch (err) {
      console.error('Save All Error:', err);
      return sendJson(res, 500, { error: 'Kayıt sırasında hata oluştu: ' + err.message });
    }
  }

  // Categories: GET
  if (pathname === '/api/categories' && method === 'GET') {
    const db = getDatabase();
    return sendJson(res, 200, db.categories || []);
  }

  // Brands: GET
  if (pathname === '/api/brands' && method === 'GET') {
    const db = getDatabase();
    return sendJson(res, 200, db.brands || []);
  }

  // Products: GET
  if (pathname === '/api/products' && method === 'GET') {
    const db = getDatabase();
    let list = db.products || [];
    if (parsedUrl.query.categoryId || parsedUrl.query.category) {
      const cat = parsedUrl.query.categoryId || parsedUrl.query.category;
      list = list.filter(p => p.category === cat || p.categoryId === cat);
    }
    if (parsedUrl.query.subCategory) {
      list = list.filter(p => p.subCategory === parsedUrl.query.subCategory);
    }
    if (parsedUrl.query.popular === 'true' || parsedUrl.query.featured === 'true') {
      list = list.filter(p => p.isPopular || p.isFeatured || p.isBestSeller);
    }
    return sendJson(res, 200, list);
  }

  // Products: POST (Admin)
  if (pathname === '/api/products' && method === 'POST') {
    if (!checkAdminAuth(req)) return sendJson(res, 401, { error: 'Yetkisiz erişim.' });
    const body = await parseJsonBody(req);
    if (!body.name || body.price === undefined) {
      return sendJson(res, 400, { error: 'Ürün adı ve fiyatı zorunludur.' });
    }
    const db = getDatabase();
    const slug = body.name.toLowerCase()
      .replace(/ğ/g, 'g').replace(/ü/g, 'u').replace(/ş/g, 's')
      .replace(/ı/g, 'i').replace(/ö/g, 'o').replace(/ç/g, 'c')
      .replace(/[^a-z0-9]/g, '-')
      .replace(/-+/g, '-').replace(/^-|-$/g, '') + '-' + Date.now().toString().slice(-4);

    const newProduct = {
      id: 'prod-' + Date.now(),
      slug: body.slug || slug,
      name: body.name.trim(),
      brand: body.brand || 'Gallus Mama',
      brandSlug: (body.brand || 'Gallus Mama').toLowerCase().replace(/[^a-z0-9]/g, '-'),
      category: body.category || body.categoryId || 'yumurta',
      categoryName: body.categoryName || 'Diğer',
      subCategory: body.subCategory || '',
      subCategoryName: body.subCategoryName || '',
      price: Number(body.price) || 0,
      originalPrice: body.originalPrice !== undefined ? Number(body.originalPrice) : null,
      stock: body.stock !== undefined ? Math.max(0, Number(body.stock)) : 0,
      unit: body.unit ? body.unit.trim() : 'Adet',
      sku: body.sku || 'GL-' + Date.now().toString().slice(-6),
      description: body.description || '',
      ingredients: body.ingredients || '',
      analysis: body.analysis || '',
      specs: body.specs || {},
      imageUrl: body.imageUrl || 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80',
      gallery: body.gallery || [body.imageUrl || 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80'],
      isPopular: Boolean(body.isPopular),
      isFeatured: Boolean(body.isFeatured || body.isPopular),
      isBestSeller: Boolean(body.isBestSeller),
      badge: body.badge || ''
    };
    db.products.unshift(newProduct);
    saveDatabase(db);
    return sendJson(res, 201, newProduct);
  }

  // Products: PUT / DELETE
  if (pathname.startsWith('/api/products/')) {
    const prodId = pathname.replace('/api/products/', '');

    if (method === 'PUT') {
      if (!checkAdminAuth(req)) return sendJson(res, 401, { error: 'Yetkisiz erişim.' });
      const body = await parseJsonBody(req);
      const db = getDatabase();
      const idx = db.products.findIndex(p => p.id === prodId || p.slug === prodId);
      if (idx === -1) return sendJson(res, 404, { error: 'Ürün bulunamadı.' });

      db.products[idx] = {
        ...db.products[idx],
        name: body.name !== undefined ? body.name.trim() : db.products[idx].name,
        category: body.category !== undefined ? body.category : db.products[idx].category,
        categoryName: body.categoryName !== undefined ? body.categoryName : db.products[idx].categoryName,
        subCategory: body.subCategory !== undefined ? body.subCategory : db.products[idx].subCategory,
        subCategoryName: body.subCategoryName !== undefined ? body.subCategoryName : db.products[idx].subCategoryName,
        price: body.price !== undefined ? Number(body.price) : db.products[idx].price,
        originalPrice: body.originalPrice !== undefined ? Number(body.originalPrice) : db.products[idx].originalPrice,
        stock: body.stock !== undefined ? Math.max(0, Number(body.stock)) : db.products[idx].stock,
        unit: body.unit !== undefined ? body.unit.trim() : db.products[idx].unit,
        description: body.description !== undefined ? body.description : db.products[idx].description,
        ingredients: body.ingredients !== undefined ? body.ingredients : db.products[idx].ingredients,
        imageUrl: body.imageUrl !== undefined ? body.imageUrl : db.products[idx].imageUrl,
        isPopular: body.isPopular !== undefined ? Boolean(body.isPopular) : db.products[idx].isPopular,
        isFeatured: body.isFeatured !== undefined ? Boolean(body.isFeatured) : db.products[idx].isFeatured,
        isBestSeller: body.isBestSeller !== undefined ? Boolean(body.isBestSeller) : db.products[idx].isBestSeller
      };
      saveDatabase(db);
      return sendJson(res, 200, db.products[idx]);
    }

    if (method === 'DELETE') {
      if (!checkAdminAuth(req)) return sendJson(res, 401, { error: 'Yetkisiz erişim.' });
      const db = getDatabase();
      db.products = db.products.filter(p => p.id !== prodId && p.slug !== prodId);
      saveDatabase(db);
      return sendJson(res, 200, { success: true });
    }
  }

  // Orders: GET (Admin) & POST (Customer Checkout)
  if (pathname === '/api/orders') {
    const db = getDatabase();
    if (method === 'GET') {
      if (!checkAdminAuth(req)) return sendJson(res, 401, { error: 'Yetkisiz erişim.' });
      return sendJson(res, 200, db.orders || []);
    }

    if (method === 'POST') {
      const body = await parseJsonBody(req);
      if (!body.customer || !body.items || !body.items.length) {
        return sendJson(res, 400, { error: 'Sipariş detayları ve ürünler zorunludur.' });
      }

      // If firestoreDb is initialized, run atomic Firestore transaction
      if (firestoreDb) {
        try {
          await firestoreDb.runTransaction(async (txn) => {
            for (const item of body.items) {
              const pid = item.id || item.productId;
              const qty = Number(item.qty || 1);
              let prodRef = firestoreDb.collection('products').doc(String(pid));
              let snap = await txn.get(prodRef);
              if (!snap.exists) {
                prodRef = firestoreDb.collection('products').doc(`u6_p${pid}`);
                snap = await txn.get(prodRef);
              }
              if (snap.exists) {
                const currStock = Number(snap.data().stock_quantity || 0);
                const prodName = snap.data().name || item.name;
                if (currStock < qty) {
                  throw new Error(`Yetersiz Stok: '${prodName}' için mevcut stok ${currStock} adettir.`);
                }
                const newStock = Math.max(0, currStock - qty);
                txn.update(prodRef, {
                  stock_quantity: newStock,
                  updated_at: new Date().toISOString(),
                  synced_to_cloud: 1
                });
                // Also update public_products
                const publicRef = firestoreDb.collection('public_products').doc(prodRef.id);
                txn.set(publicRef, {
                  stock_quantity: newStock,
                  stock: newStock,
                  inStock: newStock > 0,
                  updatedAt: new Date().toISOString()
                }, { merge: true });
              }
            }
          });
        } catch (txnErr) {
          return sendJson(res, 400, { success: false, error: txnErr.message });
        }
      }

      // Local fallback / sync
      for (const item of body.items) {
        const p = db.products.find(prod => prod.id === item.id || prod.slug === item.slug);
        if (p) {
          p.stock = Math.max(0, p.stock - (item.qty || 1));
        }
      }

      const newOrder = {
        id: 'GL-' + Date.now().toString().slice(-6),
        date: new Date().toISOString(),
        customer: body.customer,
        paymentMethod: body.paymentMethod || 'Kredi Kartı',
        items: body.items,
        total: body.total,
        status: 'Hazırlanıyor'
      };

      if (!db.orders) db.orders = [];
      db.orders.unshift(newOrder);
      saveDatabase(db);

      // Record to Firestore 'orders' and 'sales' if firestoreDb is available
      if (firestoreDb) {
        try {
          await firestoreDb.collection('orders').doc(newOrder.id).set({
            ...newOrder,
            source: 'web'
          });
          const saleId = Number(newOrder.id.replace('GL-', '')) || Date.now();
          await firestoreDb.collection('sales').doc(`u6_s${saleId}`).set({
            id: saleId,
            user_id: 6,
            total_amount: typeof body.total === 'number' ? body.total : 100,
            payment_type: body.paymentMethod || 'Kredi Kartı',
            created_at: new Date().toISOString(),
            note: `Web Siparişi: ${body.customer.fullname || ''} (${body.customer.phone || ''})`,
            items: body.items
          });
        } catch (fsErr) {
          console.error("Firestore order write warning:", fsErr.message);
        }
      }

      return sendJson(res, 201, { success: true, order: newOrder });
    }
  }

  // Wholesale B2B Inquiry: POST
  if (pathname === '/api/wholesale' && method === 'POST') {
    const body = await parseJsonBody(req);
    const db = getDatabase();
    const newInquiry = {
      id: 'B2B-' + Date.now().toString().slice(-6),
      date: new Date().toISOString(),
      company: body.company || '',
      contactName: body.contactName || '',
      phone: body.phone || '',
      city: body.city || '',
      category: body.category || '',
      estimatedVolume: body.estimatedVolume || '',
      note: body.note || ''
    };
    if (!db.wholesaleInquiries) db.wholesaleInquiries = [];
    db.wholesaleInquiries.unshift(newInquiry);
    saveDatabase(db);
    return sendJson(res, 200, { success: true, message: 'Toptan satış talebiniz alındı. En kısa sürede aranacaksınız.' });
  }

  // Newsletter: POST
  if (pathname === '/api/newsletter' && method === 'POST') {
    const body = await parseJsonBody(req);
    const email = (body.email || '').trim().toLowerCase();
    if (!email || !email.includes('@')) {
      return sendJson(res, 400, { error: 'Geçerli bir e-posta adresi giriniz.' });
    }
    const db = getDatabase();
    if (!db.subscribers) db.subscribers = [];
    if (!db.subscribers.includes(email)) db.subscribers.push(email);
    saveDatabase(db);
    return sendJson(res, 200, { success: true, message: 'Bültenimize başarıyla kaydoldunuz!' });
  }

  // --- STATIC FILES & MULTI-PAGE ROUTING ---
  let reqPath = pathname;
  let isAsset = reqPath.includes('.') && !reqPath.endsWith('.html');

  if (isAsset) {
    let filePath = path.join(__dirname, 'public', reqPath);
    if (!filePath.startsWith(path.join(__dirname, 'public'))) {
      res.writeHead(403, { 'Content-Type': 'text/plain' });
      return res.end('403 Forbidden');
    }

    fs.stat(filePath, (err, stats) => {
      if (err || !stats.isFile()) {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        return res.end('404 Not Found');
      }

      const ext = path.extname(filePath).toLowerCase();
      const contentType = MIME_TYPES[ext] || 'application/octet-stream';
      fs.readFile(filePath, (err, data) => {
        if (err) {
          res.writeHead(500, { 'Content-Type': 'text/plain' });
          return res.end('500 Server Error');
        }
        res.writeHead(200, { 'Content-Type': contentType, 'Cache-Control': 'public, max-age=86400' });
        res.end(data);
      });
    });
    return;
  }

  // Multi-page HTML route: Inject dynamic SEO metadata for clean URLs
  const indexPath = path.join(__dirname, 'public', 'index.html');
  fs.readFile(indexPath, 'utf-8', (err, htmlContent) => {
    if (err) {
      res.writeHead(500, { 'Content-Type': 'text/plain' });
      return res.end('500 Server Error');
    }

    const db = getDatabase();
    const meta = getRouteMetadata(pathname, db);

    // Inject title, description, canonical
    let modifiedHtml = htmlContent
      .replace(/<title>.*?<\/title>/i, `<title>${meta.title}</title>`)
      .replace(/<meta name="description" content=".*?"/i, `<meta name="description" content="${meta.description}"`)
      .replace(/<link rel="canonical" href=".*?"/i, `<link rel="canonical" href="${meta.canonical}"`);

    // Inject schema if product
    if (meta.productSchema) {
      const schemaScript = `\n  <script type="application/ld+json">\n  ${JSON.stringify(meta.productSchema, null, 2)}\n  </script>\n</head>`;
      modifiedHtml = modifiedHtml.replace('</head>', schemaScript);
    }

    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(modifiedHtml);
  });
});

server.listen(PORT, () => {
  console.log(`====================================================`);
  console.log(`🚀 Gallus Mama Premium E-Ticaret Sunucusu Aktif! (${PORT})`);
  console.log(`🌐 Ana Sayfa: http://localhost:${PORT}`);
  console.log(`🛒 Alışveriş: http://localhost:${PORT}/kopek`);
  console.log(`🔑 Yönetim: http://localhost:${PORT}/admin`);
  console.log(`🗺️ Sitemap: http://localhost:${PORT}/sitemap.xml`);
  console.log(`====================================================`);
});
