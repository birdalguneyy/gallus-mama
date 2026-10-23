const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');
const crypto = require('crypto');

const PORT = process.env.PORT || 3000;
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || '19071907';

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
      const defaultData = {
        siteInfo: {
          title: "Gallus Mama",
          slogan: "Lezzetin ve Kalitenin Doğal Adresi",
          aboutText: "Gallus Mama olarak 2018 yılından bu yana taze, kaliteli ve özenle hazırlanan lezzetler sunuyoruz.",
          phone: "+90 (555) 190 70 70",
          email: "iletisim@gallusmama.com",
          address: "Atatürk Caddesi No:1907, Kadıköy / İstanbul",
          workingHours: "Haftanın Her Günü: 09:00 - 23:00"
        },
        categories: [],
        products: []
      };
      fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });
      fs.writeFileSync(DB_PATH, JSON.stringify(defaultData, null, 2), 'utf-8');
      return defaultData;
    }
    return JSON.parse(fs.readFileSync(DB_PATH, 'utf-8'));
  } catch (err) {
    console.error("DB Read Error:", err);
    return { siteInfo: {}, categories: [], products: [] };
  }
}

// Helper: Save DB
function saveDatabase(data) {
  try {
    fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });
    fs.writeFileSync(DB_PATH, JSON.stringify(data, null, 2), 'utf-8');
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
  const authHeader = req.headers['authorization'];
  if (!authHeader) return false;
  const token = authHeader.replace('Bearer ', '').trim();
  return activeTokens.has(token);
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
    if (!checkAdminAuth(req)) {
      return sendJson(res, 401, { error: 'Yetkisiz erişim.' });
    }
    const body = await parseJsonBody(req);
    const db = getDatabase();
    db.siteInfo = { ...db.siteInfo, ...body };
    saveDatabase(db);
    return sendJson(res, 200, { success: true, siteInfo: db.siteInfo });
  }

  // Categories: GET
  if (pathname === '/api/categories' && method === 'GET') {
    const db = getDatabase();
    return sendJson(res, 200, db.categories || []);
  }

  // Categories: POST (Admin)
  if (pathname === '/api/categories' && method === 'POST') {
    if (!checkAdminAuth(req)) {
      return sendJson(res, 401, { error: 'Yetkisiz erişim.' });
    }
    const body = await parseJsonBody(req);
    if (!body.name) {
      return sendJson(res, 400, { error: 'Kategori adı zorunludur.' });
    }
    const db = getDatabase();
    const newCategory = {
      id: 'cat-' + Date.now(),
      name: body.name.trim(),
      slug: body.name.toLowerCase().replace(/[^a-z0-9]/g, '-'),
      icon: body.icon || '🏷️',
      description: body.description || ''
    };
    db.categories.push(newCategory);
    saveDatabase(db);
    return sendJson(res, 201, newCategory);
  }

  // Categories: PUT / DELETE
  if (pathname.startsWith('/api/categories/')) {
    const catId = pathname.replace('/api/categories/', '');

    if (method === 'PUT') {
      if (!checkAdminAuth(req)) return sendJson(res, 401, { error: 'Yetkisiz erişim.' });
      const body = await parseJsonBody(req);
      const db = getDatabase();
      const idx = db.categories.findIndex(c => c.id === catId);
      if (idx === -1) return sendJson(res, 404, { error: 'Kategori bulunamadı.' });

      db.categories[idx] = {
        ...db.categories[idx],
        name: body.name !== undefined ? body.name.trim() : db.categories[idx].name,
        icon: body.icon !== undefined ? body.icon : db.categories[idx].icon,
        description: body.description !== undefined ? body.description : db.categories[idx].description
      };
      saveDatabase(db);
      return sendJson(res, 200, db.categories[idx]);
    }

    if (method === 'DELETE') {
      if (!checkAdminAuth(req)) return sendJson(res, 401, { error: 'Yetkisiz erişim.' });
      const db = getDatabase();
      db.categories = db.categories.filter(c => c.id !== catId);
      db.products = db.products.map(p => p.categoryId === catId ? { ...p, categoryId: '' } : p);
      saveDatabase(db);
      return sendJson(res, 200, { success: true });
    }
  }

  // Products: GET
  if (pathname === '/api/products' && method === 'GET') {
    const db = getDatabase();
    let list = db.products || [];
    if (parsedUrl.query.categoryId) {
      list = list.filter(p => p.categoryId === parsedUrl.query.categoryId);
    }
    if (parsedUrl.query.popular === 'true') {
      list = list.filter(p => p.isPopular);
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
    const newProduct = {
      id: 'prod-' + Date.now(),
      name: body.name.trim(),
      category: body.category || body.categoryId || '',
      categoryId: body.category || body.categoryId || '',
      price: Number(body.price) || 0,
      originalPrice: body.originalPrice !== undefined ? Number(body.originalPrice) : null,
      stock: body.stock !== undefined ? Math.max(0, Number(body.stock)) : 0,
      unit: body.unit ? body.unit.trim() : 'Adet',
      description: body.description || '',
      imageUrl: body.imageUrl || 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80',
      isPopular: Boolean(body.isPopular),
      isFeatured: Boolean(body.isFeatured || body.isPopular)
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
      const idx = db.products.findIndex(p => p.id === prodId);
      if (idx === -1) return sendJson(res, 404, { error: 'Ürün bulunamadı.' });

      db.products[idx] = {
        ...db.products[idx],
        name: body.name !== undefined ? body.name.trim() : db.products[idx].name,
        category: body.category !== undefined ? body.category : (body.categoryId !== undefined ? body.categoryId : db.products[idx].category),
        categoryId: body.category !== undefined ? body.category : (body.categoryId !== undefined ? body.categoryId : db.products[idx].categoryId),
        price: body.price !== undefined ? Number(body.price) : db.products[idx].price,
        originalPrice: body.originalPrice !== undefined ? Number(body.originalPrice) : db.products[idx].originalPrice,
        stock: body.stock !== undefined ? Math.max(0, Number(body.stock)) : (db.products[idx].stock !== undefined ? db.products[idx].stock : 0),
        unit: body.unit !== undefined ? body.unit.trim() : (db.products[idx].unit || 'Adet'),
        description: body.description !== undefined ? body.description : db.products[idx].description,
        imageUrl: body.imageUrl !== undefined ? body.imageUrl : db.products[idx].imageUrl,
        isPopular: body.isPopular !== undefined ? Boolean(body.isPopular) : db.products[idx].isPopular,
        isFeatured: body.isFeatured !== undefined ? Boolean(body.isFeatured) : db.products[idx].isFeatured
      };
      saveDatabase(db);
      return sendJson(res, 200, db.products[idx]);
    }

    if (method === 'DELETE') {
      if (!checkAdminAuth(req)) return sendJson(res, 401, { error: 'Yetkisiz erişim.' });
      const db = getDatabase();
      db.products = db.products.filter(p => p.id !== prodId);
      saveDatabase(db);
      return sendJson(res, 200, { success: true });
    }
  }

  // --- STATIC FILES ROUTING ---
  let reqPath = pathname;
  if (reqPath === '/' || reqPath === '') reqPath = '/index.html';
  if (reqPath === '/admin') reqPath = '/admin.html';

  let filePath = path.join(__dirname, 'public', reqPath);

  // Security check: path traversal
  if (!filePath.startsWith(path.join(__dirname, 'public'))) {
    res.writeHead(403, { 'Content-Type': 'text/plain' });
    return res.end('403 Forbidden');
  }

  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      // Fallback to index.html for unknown HTML paths
      filePath = path.join(__dirname, 'public', 'index.html');
    }

    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';

    fs.readFile(filePath, (err, data) => {
      if (err) {
        res.writeHead(500, { 'Content-Type': 'text/plain' });
        return res.end('500 Server Error');
      }
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(data);
    });
  });
});

server.listen(PORT, () => {
  console.log(`====================================================`);
  console.log(`🚀 Gallus Mama sunucusu ${PORT} portunda başarıyla çalışıyor!`);
  console.log(`🌐 Ana Sayfa: http://localhost:${PORT}`);
  console.log(`🔑 Yönetim Paneli: http://localhost:${PORT}/admin.html`);
  console.log(`====================================================`);
});
