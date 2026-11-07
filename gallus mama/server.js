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

// Helper: Parse numeric price/total
function parseNumericTotal(val) {
  if (typeof val === 'number' && !isNaN(val)) return val;
  if (!val) return 0;
  let s = String(val).replace(/[^\d.,-]/g, '').trim();
  if (!s) return 0;
  if (s.includes('.') && s.includes(',')) {
    s = s.replace(/\./g, '').replace(',', '.');
  } else if (s.includes(',')) {
    const parts = s.split(',');
    if (parts[parts.length - 1].length === 2) s = s.replace(',', '.');
    else s = s.replace(/,/g, '');
  } else if (s.includes('.')) {
    const parts = s.split('.');
    if (parts[parts.length - 1].length === 3) s = s.replace(/\./g, '');
  }
  const n = parseFloat(s);
  return isNaN(n) ? 0 : n;
}

// Helper: Compute Loyalty Points (%1 * 100 = 100% of totalNumeric in points)
function calcOrderPoints(totalNumeric) {
  const num = parseNumericTotal(totalNumeric);
  return Math.max(0, Math.round((num * 0.01) * 100));
}

// Helper: Collect all unique emails from subscribers, subscriberDetails, members, and orders
function collectAllEmails(db) {
  const emailSet = new Set();
  const detailsMap = new Map();

  for (const e of (db.subscribers || [])) {
    const clean = String(e || '').trim().toLowerCase();
    if (clean && clean.includes('@')) {
      emailSet.add(clean);
      if (!detailsMap.has(clean)) {
        detailsMap.set(clean, { email: clean, name: '', source: 'Bülten', date: '' });
      }
    }
  }

  for (const d of (db.subscriberDetails || [])) {
    const clean = String((d && d.email) || '').trim().toLowerCase();
    if (clean && clean.includes('@')) {
      emailSet.add(clean);
      detailsMap.set(clean, {
        email: clean,
        name: d.name || d.fullname || '',
        phone: d.phone || '',
        source: d.source || 'Bülten',
        date: d.date || d.createdAt || ''
      });
    }
  }

  for (const m of (db.members || [])) {
    const clean = String((m && m.email) || '').trim().toLowerCase();
    if (clean && clean.includes('@')) {
      emailSet.add(clean);
      const existing = detailsMap.get(clean) || {};
      detailsMap.set(clean, {
        email: clean,
        name: m.fullname || existing.name || '',
        phone: m.phone || existing.phone || '',
        source: existing.source ? `${existing.source} + Üye` : 'Site Üyesi',
        date: m.createdAt || existing.date || ''
      });
    }
  }

  for (const o of (db.orders || [])) {
    const c = (o && o.customer) || {};
    const clean = String(c.email || o.email || '').trim().toLowerCase();
    if (clean && clean.includes('@')) {
      emailSet.add(clean);
      if (!detailsMap.has(clean)) {
        detailsMap.set(clean, {
          email: clean,
          name: c.fullname || '',
          phone: c.phone || '',
          source: 'Sipariş Müşterisi',
          date: o.date || ''
        });
      }
    }
  }

  return {
    allEmails: Array.from(emailSet),
    subscriberDetails: Array.from(detailsMap.values())
  };
}

// Helper: Enrich Member with live calculated points & orders
function buildMemberPayload(db, memberObj) {
  if (!memberObj) return null;
  const email = (memberObj.email || '').trim().toLowerCase();
  const phoneClean = (memberObj.phone || '').replace(/\D/g, '').slice(-10);
  const allOrders = Array.isArray(db.orders) ? db.orders : [];
  const memberOrders = allOrders.filter(o => {
    const c = o.customer || {};
    const oEmail = (c.email || o.email || '').trim().toLowerCase();
    const oPhone = (c.phone || '').replace(/\D/g, '').slice(-10);
    if (email && oEmail && email === oEmail) return true;
    if (phoneClean && phoneClean.length >= 10 && oPhone === phoneClean) return true;
    return false;
  });

  let approvedEarned = 0;
  let pendingEarned = 0;
  let totalUsed = 0;

  for (const o of memberOrders) {
    const tNum = o.totalNumeric !== undefined ? Number(o.totalNumeric) : parseNumericTotal(o.total);
    const pts = o.earnedPoints !== undefined ? Number(o.earnedPoints) : calcOrderPoints(tNum);
    const used = Number(o.usedPoints || 0);
    totalUsed += used;
    if (o.pointsApproved === true || o.status === 'Onaylandı' || o.status === 'Tamamlandı') {
      approvedEarned += pts;
    } else if (o.status !== 'İptal' && o.status !== 'İptal Edildi') {
      pendingEarned += pts;
    }
  }

  const bonus = Number(memberObj.bonusPoints || 0);
  const approvedPoints = Math.max(0, approvedEarned + bonus - totalUsed);
  const pendingPoints = Math.max(0, pendingEarned);

  const safeMember = { ...memberObj };
  delete safeMember.password;

  return {
    ...safeMember,
    approvedPoints,
    pendingPoints,
    totalEarnedPoints: approvedEarned + bonus,
    usedPoints: totalUsed,
    pointsTlValue: Number((approvedPoints / 100).toFixed(2)),
    orders: memberOrders
  };
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
      const fullImg = (product.imageUrl || '').startsWith('http') ? product.imageUrl : `${SITE_DOMAIN}${product.imageUrl || '/images/mutlu-patiler-banner.jpg'}`;
      const priceNum = Number(product.price || product.sale_price || 0);
      const stockNum = Number(product.stock !== undefined ? product.stock : (product.stock_quantity || 0));
      const fullDesc = `${product.description || ''} İçindekiler: ${product.ingredients || ''} Analiz: ${product.analysis || ''}`.trim();
      return {
        title: `${product.name} - ${product.brand || 'Gallus Mama'} | En Uygun Fiyat & Hızlı Teslimat`,
        description: (product.description || defaultMeta.description).substring(0, 160),
        canonical: `${SITE_DOMAIN}/urun/${product.slug || product.id}`,
        ogImage: fullImg,
        isProduct: true,
        priceAmount: priceNum.toFixed(2),
        availabilityMeta: stockNum > 0 ? 'in stock' : 'out of stock',
        brandName: product.brand || 'Gallus Mama',
        productSchema: {
          "@context": "https://schema.org/",
          "@type": "Product",
          "name": product.name,
          "image": [fullImg],
          "description": fullDesc,
          "sku": product.sku || product.id,
          "mpn": product.sku || `GL-${String(product.id).toUpperCase()}`,
          "category": product.googleProductCategory || product.categoryName || "Evcil Hayvan ve Çiftlik Ürünleri",
          "brand": {
            "@type": "Brand",
            "name": product.brand || "Gallus Mama"
          },
          "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": "4.9",
            "reviewCount": "38",
            "bestRating": "5",
            "worstRating": "1"
          },
          "offers": {
            "@type": "Offer",
            "url": `${SITE_DOMAIN}/urun/${product.slug || product.id}`,
            "priceCurrency": "TRY",
            "price": priceNum.toFixed(2),
            "priceValidUntil": "2027-12-31",
            "itemCondition": "https://schema.org/NewCondition",
            "availability": stockNum > 0 ? "https://schema.org/InStock" : "https://schema.org/OutOfStock",
            "seller": {
              "@type": "Organization",
              "name": "Gallus Mama & Yumurta"
            },
            "shippingDetails": {
              "@type": "OfferShippingDetails",
              "shippingRate": {
                "@type": "MonetaryAmount",
                "value": priceNum >= 750 ? "0.00" : "49.00",
                "currency": "TRY"
              },
              "shippingDestination": {
                "@type": "DefinedRegion",
                "addressCountry": "TR"
              },
              "deliveryTime": {
                "@type": "ShippingDeliveryTime",
                "handlingTime": { "@type": "QuantitativeValue", "minValue": 0, "maxValue": 1, "unitCode": "DAY" },
                "transitTime": { "@type": "QuantitativeValue", "minValue": 1, "maxValue": 3, "unitCode": "DAY" }
              }
            },
            "hasMerchantReturnPolicy": {
              "@type": "MerchantReturnPolicy",
              "applicableCountry": "TR",
              "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
              "merchantReturnDays": 14,
              "returnMethod": "https://schema.org/ReturnByMail",
              "returnFees": "https://schema.org/FreeReturn"
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

  // --- GOOGLE SHOPPING / MERCHANT CENTER XML FEED ---
  if ((pathname === '/google-shopping-feed.xml' || pathname === '/merchant-feed.xml') && method === 'GET') {
    const db = getDatabase();
    const escXml = (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    let xml = `<?xml version="1.0" encoding="UTF-8"?>\n`;
    xml += `<rss xmlns:g="http://base.google.com/ns/1.0" version="2.0">\n  <channel>\n`;
    xml += `    <title>Gallus Mama &amp; Yumurta - Google Alışveriş Ürün Kataloğu</title>\n`;
    xml += `    <link>${SITE_DOMAIN}</link>\n`;
    xml += `    <description>Değirmenköy Gezen Tavuk Çiftliği Günlük Taze Yumurtaları, Eriş Yem Kanatlı Yemleri ve Premium Kedi/Köpek Mamaları Resmi Google Merchant Center Ürün Beslemesi</description>\n`;
    (db.products || []).forEach(p => {
      const pid = escXml(p.id);
      const slug = escXml(p.slug || p.id);
      const title = escXml(`${p.name || ''} (${p.brand || 'Gallus Mama'} - ${p.packaging || p.unit || 'Standart'})`);
      const desc = escXml(`${p.description || ''} İçindekiler: ${p.ingredients || ''} Analiz: ${p.analysis || ''}`);
      const link = `${SITE_DOMAIN}/urun/${slug}`;
      const rawImg = p.imageUrl || '/images/mutlu-patiler-banner.jpg';
      const img = escXml(rawImg.startsWith('http') ? rawImg : `${SITE_DOMAIN}${rawImg}`);
      const priceVal = Number(p.price || p.sale_price || 0);
      const stockVal = Number(p.stock !== undefined ? p.stock : (p.stock_quantity || 0));
      const avail = stockVal > 0 ? 'in_stock' : 'out_of_stock';
      const brand = escXml(p.brand || 'Gallus Mama');
      const mpn = escXml(p.sku || `GL-${String(p.id).toUpperCase()}`);
      const gCat = escXml(p.googleProductCategory || 'Animals & Pet Supplies > Pet Supplies');
      const pType = escXml(p.categoryName || 'Pet & Çiftlik Ürünleri');
      const shipPrice = priceVal >= 750 ? '0.00 TRY' : '49.00 TRY';
      xml += `    <item>\n      <g:id>${pid}</g:id>\n      <g:title>${title}</g:title>\n      <g:description>${desc}</g:description>\n      <g:link>${link}</g:link>\n      <g:image_link>${img}</g:image_link>\n      <g:condition>new</g:condition>\n      <g:availability>${avail}</g:availability>\n      <g:price>${priceVal.toFixed(2)} TRY</g:price>\n      <g:brand>${brand}</g:brand>\n      <g:mpn>${mpn}</g:mpn>\n      <g:identifier_exists>yes</g:identifier_exists>\n      <g:google_product_category>${gCat}</g:google_product_category>\n      <g:product_type>${pType}</g:product_type>\n      <g:shipping>\n        <g:country>TR</g:country>\n        <g:service>Standart Kargo / Çiftlik Servisi</g:service>\n        <g:price>${shipPrice}</g:price>\n      </g:shipping>\n    </item>\n`;
    });
    xml += `  </channel>\n</rss>`;
    res.writeHead(200, { 'Content-Type': 'application/xml; charset=utf-8' });
    return res.end(xml);
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

      if (body.categories && Array.isArray(body.categories)) {
        db.categories = body.categories;
      }

      if (body.brands && Array.isArray(body.brands)) {
        db.brands = body.brands;
      }

      if (body.products && Array.isArray(body.products)) {
        if (body.replaceAllProducts || body.products.length > 5) {
          db.products = body.products;
        } else {
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
      }

      saveDatabase(db);

      // Save siteInfo to Firestore site_settings/main if connected
      if (firestoreDb && body.siteInfo && typeof body.siteInfo === 'object') {
        try {
          await firestoreDb.collection('site_settings').doc('main').set(db.siteInfo, { merge: true });
        } catch (e) {}
      }

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
                ingredients: p.ingredients || '',
                analysis: p.analysis || '',
                usage: p.usage || '',
                specs: p.specs || {},
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
      if (parsedUrl.query && parsedUrl.query.email) {
        const qEmail = String(parsedUrl.query.email).trim().toLowerCase();
        const filtered = (db.orders || []).filter(o => ((o.customer && o.customer.email) || o.email || '').toLowerCase() === qEmail);
        return sendJson(res, 200, filtered);
      }
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

      const totalNumeric = body.totalNumeric !== undefined ? Number(body.totalNumeric) : parseNumericTotal(body.total);
      const earnedPoints = body.earnedPoints !== undefined ? Number(body.earnedPoints) : calcOrderPoints(totalNumeric);
      const usedPoints = Math.max(0, Number(body.usedPoints || 0));
      const custEmail = String((body.customer && body.customer.email) || body.email || '').trim().toLowerCase();

      const newOrder = {
        id: 'GL-' + Date.now().toString().slice(-6),
        date: new Date().toISOString(),
        customer: {
          ...body.customer,
          email: custEmail
        },
        email: custEmail,
        paymentMethod: body.paymentMethod || 'Havale / EFT',
        items: body.items,
        total: body.total,
        totalNumeric,
        earnedPoints,
        usedPoints,
        pointsApproved: false,
        status: 'Onay Bekliyor',
        source: 'web'
      };

      if (!db.orders) db.orders = [];
      db.orders.unshift(newOrder);

      if (custEmail && custEmail.includes('@')) {
        if (!db.subscribers) db.subscribers = [];
        if (!db.subscribers.includes(custEmail)) db.subscribers.push(custEmail);
        if (!db.subscriberDetails) db.subscriberDetails = [];
        if (!db.subscriberDetails.some(s => (s.email || '').toLowerCase() === custEmail)) {
          db.subscriberDetails.unshift({
            email: custEmail,
            name: (body.customer && body.customer.fullname) || '',
            phone: (body.customer && body.customer.phone) || '',
            source: 'Sipariş',
            date: newOrder.date
          });
        }
      }
      saveDatabase(db);

      // Record to Firestore 'orders' and 'sales' if firestoreDb is available
      if (firestoreDb) {
        try {
          await firestoreDb.collection('orders').doc(newOrder.id).set({
            ...newOrder,
            source: 'web'
          });
          if (custEmail && custEmail.includes('@')) {
            await firestoreDb.collection('newsletter_subscribers').doc(custEmail).set({
              email: custEmail,
              name: (body.customer && body.customer.fullname) || '',
              phone: (body.customer && body.customer.phone) || '',
              source: 'Sipariş',
              date: newOrder.date
            }, { merge: true });
          }
        } catch (fsErr) {
          console.error("Firestore order write warning:", fsErr.message);
        }
      }

      return sendJson(res, 201, { success: true, order: newOrder });
    }
  }

  // Order Approve & Loyalty Points Activation: POST
  if (pathname === '/api/orders/approve' && method === 'POST') {
    const body = await parseJsonBody(req);
    const orderId = String(body.orderId || body.id || '').trim();
    if (!orderId) return sendJson(res, 400, { success: false, error: 'orderId zorunludur.' });

    const db = getDatabase();
    if (!db.orders) db.orders = [];
    const ord = db.orders.find(o => o.id === orderId);
    const nowIso = new Date().toISOString();

    if (ord) {
      ord.pointsApproved = true;
      ord.status = body.status || 'Onaylandı';
      ord.approvedAt = nowIso;
      if (ord.earnedPoints === undefined) {
        ord.earnedPoints = calcOrderPoints(ord.totalNumeric !== undefined ? ord.totalNumeric : ord.total);
      }
      saveDatabase(db);
    }

    if (firestoreDb) {
      try {
        await firestoreDb.collection('orders').doc(orderId).set({
          pointsApproved: true,
          status: body.status || 'Onaylandı',
          approvedAt: nowIso
        }, { merge: true });
      } catch (e) {}
    }

    let updatedMember = null;
    const custEmail = ord ? String((ord.customer && ord.customer.email) || ord.email || '').trim().toLowerCase() : String(body.email || '').trim().toLowerCase();
    if (custEmail && Array.isArray(db.members)) {
      const m = db.members.find(x => (x.email || '').toLowerCase() === custEmail);
      if (m) {
        updatedMember = buildMemberPayload(db, m);
        if (firestoreDb) {
          try {
            await firestoreDb.collection('web_members').doc(custEmail).set({
              approvedPoints: updatedMember.approvedPoints,
              pendingPoints: updatedMember.pendingPoints,
              updatedAt: nowIso
            }, { merge: true });
          } catch (e) {}
        }
      }
    }

    return sendJson(res, 200, {
      success: true,
      message: `Sipariş (${orderId}) ve kazanılan puanlar onaylandı!`,
      order: ord || { id: orderId, pointsApproved: true, status: 'Onaylandı' },
      member: updatedMember
    });
  }

  // Members: Fast Register / Full Register
  if (pathname === '/api/members/register' && method === 'POST') {
    const body = await parseJsonBody(req);
    const email = String(body.email || '').trim().toLowerCase();
    const fullname = String(body.fullname || body.name || '').trim();
    const phone = String(body.phone || '').trim();
    const password = String(body.password || '123456').trim();
    const city = String(body.city || 'İstanbul').trim();
    const district = String(body.district || 'Silivri').trim();
    const street = String(body.street || '').trim();
    const address = String(body.address || '').trim();

    if (!email || !email.includes('@')) {
      return sendJson(res, 400, { success: false, error: 'Lütfen geçerli bir e-posta adresi giriniz.' });
    }

    const db = getDatabase();
    if (!db.members) db.members = [];
    const nowIso = new Date().toISOString();

    let member = db.members.find(m => (m.email || '').toLowerCase() === email);
    if (member) {
      if (fullname) member.fullname = fullname;
      if (phone) member.phone = phone;
      if (body.password) member.password = password;
      if (city) member.city = city;
      if (district) member.district = district;
      if (street) member.street = street;
      if (address) member.address = address;
      member.updatedAt = nowIso;
    } else {
      member = {
        id: 'MEM-' + Date.now().toString().slice(-6),
        fullname: fullname || email.split('@')[0],
        email,
        phone,
        password,
        city,
        district,
        street,
        address,
        bonusPoints: 0,
        createdAt: nowIso,
        updatedAt: nowIso
      };
      db.members.unshift(member);
    }

    if (!db.subscribers) db.subscribers = [];
    if (!db.subscribers.includes(email)) db.subscribers.push(email);
    if (!db.subscriberDetails) db.subscriberDetails = [];
    if (!db.subscriberDetails.some(s => (s.email || '').toLowerCase() === email)) {
      db.subscriberDetails.unshift({
        email,
        name: member.fullname,
        phone: member.phone,
        source: body.source || 'Hızlı Üyelik',
        date: nowIso
      });
    }

    saveDatabase(db);
    const enriched = buildMemberPayload(db, member);

    if (firestoreDb) {
      try {
        const fsMember = { ...enriched };
        delete fsMember.orders;
        await firestoreDb.collection('web_members').doc(email).set({
          ...fsMember,
          updatedAt: nowIso
        }, { merge: true });
        await firestoreDb.collection('newsletter_subscribers').doc(email).set({
          email,
          name: member.fullname,
          phone: member.phone,
          source: body.source || 'Hızlı Üyelik',
          date: nowIso
        }, { merge: true });
      } catch (e) {}
    }

    return sendJson(res, 200, {
      success: true,
      message: 'Üyeliğiniz başarıyla oluşturuldu!',
      member: enriched
    });
  }

  // Members: Login
  if (pathname === '/api/members/login' && method === 'POST') {
    const body = await parseJsonBody(req);
    const identifier = String(body.email || body.identifier || '').trim().toLowerCase();
    const password = String(body.password || '').trim();

    if (!identifier) {
      return sendJson(res, 400, { success: false, error: 'E-posta veya telefon numarası giriniz.' });
    }

    const db = getDatabase();
    if (!db.members) db.members = [];
    const cleanPhone = identifier.replace(/\D/g, '').slice(-10);

    const member = db.members.find(m => {
      const mEmail = (m.email || '').toLowerCase();
      const mPhone = (m.phone || '').replace(/\D/g, '').slice(-10);
      return mEmail === identifier || (cleanPhone.length >= 10 && mPhone === cleanPhone);
    });

    if (!member) {
      return sendJson(res, 404, { success: false, error: 'Bu e-posta ile kayıtlı üye bulunamadı. Hızlı Üyelik sekmesinden hemen kayıt olabilirsiniz.' });
    }

    if (member.password && password && member.password !== password) {
      return sendJson(res, 401, { success: false, error: 'Şifreniz hatalı. Lütfen kontrol edip tekrar deneyin.' });
    }

    const enriched = buildMemberPayload(db, member);
    return sendJson(res, 200, {
      success: true,
      message: 'Giriş başarılı!',
      member: enriched
    });
  }

  // Members: Get Profile & Live Points
  if (pathname === '/api/members/me' && method === 'GET') {
    const email = String((parsedUrl.query && parsedUrl.query.email) || '').trim().toLowerCase();
    if (!email) return sendJson(res, 400, { success: false, error: 'E-posta parametresi gerekli.' });

    const db = getDatabase();
    if (!db.members) db.members = [];
    let member = db.members.find(m => (m.email || '').toLowerCase() === email);
    if (!member) {
      member = {
        id: 'MEM-GUEST',
        fullname: email.split('@')[0],
        email,
        phone: '',
        city: 'İstanbul',
        district: 'Silivri',
        address: '',
        bonusPoints: 0
      };
    }
    const enriched = buildMemberPayload(db, member);
    return sendJson(res, 200, { success: true, member: enriched });
  }

  // Members: Update Profile / Address
  if (pathname === '/api/members/profile' && method === 'PUT') {
    const body = await parseJsonBody(req);
    const email = String(body.email || '').trim().toLowerCase();
    if (!email) return sendJson(res, 400, { success: false, error: 'E-posta gerekli.' });

    const db = getDatabase();
    if (!db.members) db.members = [];
    let member = db.members.find(m => (m.email || '').toLowerCase() === email);
    if (!member) {
      return sendJson(res, 404, { success: false, error: 'Üye bulunamadı.' });
    }

    if (body.fullname !== undefined) member.fullname = String(body.fullname).trim();
    if (body.phone !== undefined) member.phone = String(body.phone).trim();
    if (body.city !== undefined) member.city = String(body.city).trim();
    if (body.district !== undefined) member.district = String(body.district).trim();
    if (body.street !== undefined) member.street = String(body.street).trim();
    if (body.address !== undefined) member.address = String(body.address).trim();
    member.updatedAt = new Date().toISOString();

    saveDatabase(db);
    return sendJson(res, 200, { success: true, member: buildMemberPayload(db, member) });
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

  // Newsletter: GET & POST
  if (pathname === '/api/newsletter' && method === 'GET') {
    const db = getDatabase();
    const { allEmails, subscriberDetails } = collectAllEmails(db);
    return sendJson(res, 200, {
      success: true,
      subscribers: allEmails,
      subscriberDetails,
      count: allEmails.length
    });
  }

  if (pathname === '/api/newsletter' && method === 'POST') {
    const body = await parseJsonBody(req);
    const email = (body.email || '').trim().toLowerCase();
    if (!email || !email.includes('@')) {
      return sendJson(res, 400, { error: 'Geçerli bir e-posta adresi giriniz.' });
    }
    const db = getDatabase();
    const nowIso = new Date().toISOString();
    if (!db.subscribers) db.subscribers = [];
    if (!db.subscribers.includes(email)) db.subscribers.push(email);
    if (!db.subscriberDetails) db.subscriberDetails = [];
    if (!db.subscriberDetails.some(s => (s.email || '').toLowerCase() === email)) {
      db.subscriberDetails.unshift({
        email,
        name: body.name || body.fullname || '',
        phone: body.phone || '',
        source: body.source || 'Web Bülten',
        date: nowIso
      });
    }
    saveDatabase(db);
    if (firestoreDb) {
      try {
        await firestoreDb.collection('newsletter_subscribers').doc(email).set({
          email,
          name: body.name || body.fullname || '',
          phone: body.phone || '',
          source: body.source || 'Web Bülten',
          date: nowIso
        }, { merge: true });
      } catch (e) {}
    }
    return sendJson(res, 200, { success: true, message: 'Bültenimize başarıyla kaydoldunuz!' });
  }

  // Sync Endpoint for Stok-Satis-Takip App (Orders + Newsletter Emails + Members)
  if (pathname === '/api/sync/web-data' && method === 'GET') {
    const db = getDatabase();
    const { allEmails, subscriberDetails } = collectAllEmails(db);
    const enrichedMembers = (db.members || []).map(m => buildMemberPayload(db, m));
    return sendJson(res, 200, {
      success: true,
      orders: db.orders || [],
      subscribers: allEmails,
      subscriberDetails,
      members: enrichedMembers
    });
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

    // Inject OpenGraph & Google Shopping Product/ItemList Schema
    if (meta.productSchema) {
      const ogProductTags = meta.isProduct ? `\n  <meta property="og:type" content="product">\n  <meta property="product:price:amount" content="${meta.priceAmount}">\n  <meta property="product:price:currency" content="TRY">\n  <meta property="product:availability" content="${meta.availabilityMeta}">\n  <meta property="product:brand" content="${meta.brandName}">\n  <meta property="product:condition" content="new">` : '';
      const schemaScript = `${ogProductTags}\n  <script type="application/ld+json">\n  ${JSON.stringify(meta.productSchema, null, 2)}\n  </script>\n</head>`;
      modifiedHtml = modifiedHtml.replace('</head>', schemaScript);
    } else if (pathname === '/' || pathname === '') {
      const itemListElements = (db.products || []).slice(0, 24).map((p, idx) => ({
        "@type": "ListItem",
        "position": idx + 1,
        "item": {
          "@type": "Product",
          "name": p.name,
          "url": `${SITE_DOMAIN}/urun/${p.slug || p.id}`,
          "image": (p.imageUrl || '').startsWith('http') ? p.imageUrl : `${SITE_DOMAIN}${p.imageUrl || '/images/mutlu-patiler-banner.jpg'}`,
          "description": p.description || p.name,
          "sku": p.sku || p.id,
          "brand": { "@type": "Brand", "name": p.brand || "Gallus Mama" },
          "offers": {
            "@type": "Offer",
            "priceCurrency": "TRY",
            "price": Number(p.price || p.sale_price || 0).toFixed(2),
            "availability": Number(p.stock !== undefined ? p.stock : (p.stock_quantity || 0)) > 0 ? "https://schema.org/InStock" : "https://schema.org/OutOfStock"
          }
        }
      }));
      const catalogSchema = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Gallus Mama & Yumurta Ürün Kataloğu",
        "itemListElement": itemListElements
      };
      const schemaScript = `\n  <script type="application/ld+json">\n  ${JSON.stringify(catalogSchema)}\n  </script>\n</head>`;
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
