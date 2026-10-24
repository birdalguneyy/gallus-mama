import os
import sys
import json
import time
import mimetypes
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import threading

# Firebase Admin
import firebase_admin
from firebase_admin import credentials, firestore

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "database.json"
CRED_PATH = BASE_DIR / "firebase_credentials.json"

PORT = int(os.getenv("PORT", 3000))

# Initialize Firebase
if not CRED_PATH.exists():
    fallback_cred = Path(r"C:\Users\birdo\Projects\stok-satis-takip\firebase_credentials.json")
    if fallback_cred.exists():
        CRED_PATH = fallback_cred

if not firebase_admin._apps and CRED_PATH.exists():
    cred = credentials.Certificate(str(CRED_PATH))
    firebase_admin.initialize_app(cred)

db = firestore.client() if firebase_admin._apps else None

# In-memory cached products and categories
in_memory_products = []
in_memory_categories = [
    {"id": "kedi", "slug": "kedi", "name": "Kedi Mamaları ve Ürünleri", "icon": "cat", "description": "Kısırlaştırılmış, yetişkin ve yavru kedi mamaları, doğal bentonit kedi kumları ve koku gidericiler."},
    {"id": "kopek", "slug": "kopek", "name": "Köpek Mamaları ve Ürünleri", "icon": "dog", "description": "Yetişkin ve yavru köpek mamaları, etli konserveler, alıştırma pedleri ve profesyonel köpek şampuanları."},
    {"id": "tavuk-civciv", "slug": "tavuk-civciv", "name": "Tavuk ve Civciv Yemleri", "icon": "wheat", "description": "Doğal gezen tavuk yumurta yemleri ve vitaminli civciv büyütme yemleri."},
    {"id": "guvercin", "slug": "guvercin", "name": "Güvercin Yemleri", "icon": "feather", "description": "Elenmiş 1. sınıf buğday, tane tahıllar ve yüksek kondisyon güvercin yemleri."},
    {"id": "balik-akvaryum", "slug": "balik-akvaryum", "name": "Balık Yemleri ve Akvaryum", "icon": "fish", "description": "Akvaryum balıkları için pul ve granül yemler, su düzenleyiciler."},
    {"id": "kumes-ekipman", "slug": "kumes-ekipman", "name": "Kümes Ekipmanları", "icon": "home", "description": "Evcil hayvan taşıma kafesleri, havalandırmalı kutular, suluk ve yemlikler."},
    {"id": "tarim-bahce", "slug": "tarim-bahce", "name": "Tarım ve Bahçe Ürünleri", "icon": "sprout", "description": "Doğal çiftlik gübreleri, tohumlar ve bahçe bakım ürünleri."},
    {"id": "diger", "slug": "diger", "name": "Diğer Ürünler", "icon": "egg", "description": "Değirmenköy çiftlik gezen tavuk yumurtaları, muhabbet kuşu yemleri ve özel ürünler."}
]

def load_local_db():
    global in_memory_products, in_memory_categories
    try:
        if DB_PATH.exists():
            data = json.loads(DB_PATH.read_text(encoding="utf-8"))
            if data.get("products"):
                in_memory_products = data["products"]
            if data.get("categories"):
                in_memory_categories = data["categories"]
    except Exception as e:
        print(f"[WARN] Local DB read error: {e}")

load_local_db()

# Start background real-time listener on Firestore 'public_products' and 'products'
def start_firestore_listener():
    if not db:
        return

    def on_snapshot(col_snapshot, changes, read_time):
        global in_memory_products
        has_change = False
        for change in changes:
            d = change.document.to_dict()
            doc_id = change.document.id
            if 'updatedAt' in d and hasattr(d['updatedAt'], 'isoformat'):
                d['updatedAt'] = d['updatedAt'].isoformat()
            # Strip cost/purchase_price
            d.pop('purchase_price', None)

            if change.type.name == "REMOVED":
                in_memory_products = [p for p in in_memory_products if p.get("id") != doc_id]
                has_change = True
                print(f"[FIRESTORE LIVE] Ürün silindi: {doc_id}")
            else:
                idx = next((i for i, p in enumerate(in_memory_products) if p.get("id") == doc_id), -1)
                if idx >= 0:
                    old_price = in_memory_products[idx].get("price")
                    old_stock = in_memory_products[idx].get("stock")
                    in_memory_products[idx] = d
                    print(f"[FIRESTORE LIVE] Ürün güncellendi -> {d.get('name')}: {old_price} TL -> {d.get('price')} TL | Stok: {old_stock} -> {d.get('stock')}")
                else:
                    in_memory_products.append(d)
                    print(f"[FIRESTORE LIVE] Yeni ürün eklendi -> {d.get('name')} ({d.get('price')} TL)")
                has_change = True

        if has_change:
            try:
                # Update database.json cache
                current = json.loads(DB_PATH.read_text(encoding="utf-8")) if DB_PATH.exists() else {}
                current["products"] = in_memory_products
                DB_PATH.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass

    try:
        db.collection("public_products").on_snapshot(on_snapshot)
        print("✅ [FIRESTORE LIVE] Firestore 'public_products' gerçek zamanlı dinleyici aktif!")
    except Exception as e:
        print(f"[WARN] Firestore listener başlatılamadı: {e}")

threading.Thread(target=start_firestore_listener, daemon=True).start()

class GallusMamaHandler(BaseHTTPRequestHandler):
    def send_json(self, status_code: int, data: Any):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        pathname = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. API: Products
        if pathname == "/api/products":
            prods = list(in_memory_products)
            cat = query.get("category", query.get("categoryId", [None]))[0]
            if cat and cat != "all":
                prods = [p for p in prods if p.get("category") == cat or p.get("categoryId") == cat]
            popular = query.get("popular", query.get("featured", [None]))[0]
            if popular == "true":
                prods = [p for p in prods if p.get("isPopular") or p.get("isFeatured") or p.get("isBestSeller")]
            return self.send_json(200, prods)

        # 2. API: Categories
        if pathname == "/api/categories":
            return self.send_json(200, in_memory_categories)

        # 3. API: Site Info
        if pathname == "/api/info":
            info = {}
            if DB_PATH.exists():
                try:
                    info = json.loads(DB_PATH.read_text(encoding="utf-8")).get("siteInfo", {})
                except Exception:
                    pass
            return self.send_json(200, info)

        # 3.1 API: Orders GET
        if pathname == "/api/orders":
            orders = []
            if DB_PATH.exists():
                try:
                    orders = json.loads(DB_PATH.read_text(encoding="utf-8")).get("orders", [])
                except Exception:
                    pass
            return self.send_json(200, orders)

        # 4. Robots.txt
        if pathname == "/robots.txt":
            content = "User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /api/\n\nSitemap: https://gallusmama.com/sitemap.xml\n".encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        # 5. Static files
        clean_path = pathname.lstrip("/")
        file_path = (PUBLIC_DIR / clean_path).resolve()

        if file_path.is_file() and str(file_path).startswith(str(PUBLIC_DIR)):
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type:
                mime_type = "application/octet-stream"
            content = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            self.wfile.write(content)
            return

        # 6. SPA fallback -> index.html
        index_file = PUBLIC_DIR / "index.html"
        if index_file.exists():
            content = index_file.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        pathname = parsed.path

        # Read JSON body
        content_len = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            body = json.loads(raw_body)
        except Exception:
            body = {}

        # Order Placement with Atomic Firestore Transaction
        if pathname == "/api/orders":
            items = body.get("items", [])
            customer = body.get("customer", {})
            if not items or not customer:
                return self.send_json(400, {"success": False, "error": "Sipariş detayları ve ürünler zorunludur."})

            order_id = "GL-" + str(int(time.time()))[-6:]
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")

            # Check and atomically deduct stock in Firestore
            if db:
                try:
                    transaction = db.transaction()

                    @firestore.transactional
                    def process_order_transaction(txn):
                        updated_stocks = {}
                        for item in items:
                            pid = item.get("id") or item.get("productId")
                            qty = float(item.get("qty") or item.get("quantity") or 1.0)
                            
                            # Find matching product ref
                            prod_ref = db.collection("products").document(str(pid))
                            snap = prod_ref.get(transaction=txn)
                            
                            if not snap.exists:
                                # Try with u6_ prefix
                                prod_ref = db.collection("products").document(f"u6_p{pid}")
                                snap = prod_ref.get(transaction=txn)

                            if snap.exists:
                                curr_stock = float(snap.get("stock_quantity") or 0.0)
                                prod_name = snap.get("name") or item.get("name")
                                if curr_stock < qty:
                                    raise ValueError(f"Yetersiz Stok: '{prod_name}' için sadece {curr_stock} adet stok mevcut.")
                                
                                new_stock = max(0.0, curr_stock - qty)
                                txn.update(prod_ref, {
                                    "stock_quantity": new_stock,
                                    "updated_at": now_str,
                                    "synced_to_cloud": 1
                                })
                                updated_stocks[prod_ref.id] = new_stock

                        return updated_stocks

                    updated_stocks = process_order_transaction(transaction)
                    print(f"✅ [TRANSACTION BAŞARILI] Stoklar Firestore'da güvenle düşüldü: {updated_stocks}")

                    # Update public_products with new stocks
                    for doc_id, st in updated_stocks.items():
                        try:
                            db.collection("public_products").document(doc_id).update({
                                "stock_quantity": st,
                                "stock": st,
                                "inStock": st > 0,
                                "updatedAt": firestore.SERVER_TIMESTAMP
                            })
                        except Exception:
                            pass

                    # Write order document to 'orders'
                    order_doc = {
                        "id": order_id,
                        "date": now_str,
                        "createdAt": firestore.SERVER_TIMESTAMP,
                        "customer": customer,
                        "paymentMethod": body.get("paymentMethod", "Kredi Kartı"),
                        "items": items,
                        "total": float(body.get("total", 0)) if isinstance(body.get("total"), (int, float)) else 100.0,
                        "status": "Hazırlanıyor",
                        "source": "web"
                    }
                    db.collection("orders").document(order_id).set(order_doc)

                    # Also create sale record in 'sales' for Stok Satış Takip app reports
                    sale_doc = {
                        "id": int(order_id.replace("GL-", "")),
                        "user_id": 6,
                        "total_amount": float(body.get("total", 0)) if isinstance(body.get("total"), (int, float)) else 100.0,
                        "payment_type": body.get("paymentMethod", "Kredi Kartı"),
                        "created_at": now_str,
                        "note": f"Web Siparişi: {customer.get('fullname', '')} ({customer.get('phone', '')})",
                        "items": items
                    }
                    db.collection("sales").document(f"u6_s{order_id.replace('GL-', '')}").set(sale_doc)

                except ValueError as val_err:
                    return self.send_json(400, {"success": False, "error": str(val_err)})
                except Exception as ex:
                    print(f"[WARN] Firestore order transaction warning: {ex}")

            # Also record in local database.json
            if DB_PATH.exists():
                try:
                    local_db = json.loads(DB_PATH.read_text(encoding="utf-8"))
                    if "orders" not in local_db:
                        local_db["orders"] = []
                    local_db["orders"].insert(0, new_order)
                    DB_PATH.write_text(json.dumps(local_db, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass

            return self.send_json(201, {"success": True, "order": new_order})

        # Wholesale Inquiry POST
        if pathname == "/api/wholesale":
            new_inquiry = {
                "id": "B2B-" + str(int(time.time()))[-6:],
                "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "company": body.get("company", ""),
                "contactName": body.get("contactName", ""),
                "phone": body.get("phone", ""),
                "city": body.get("city", ""),
                "category": body.get("category", ""),
                "estimatedVolume": body.get("estimatedVolume", ""),
                "note": body.get("note", "")
            }
            if DB_PATH.exists():
                try:
                    local_db = json.loads(DB_PATH.read_text(encoding="utf-8"))
                    if "wholesaleInquiries" not in local_db:
                        local_db["wholesaleInquiries"] = []
                    local_db["wholesaleInquiries"].insert(0, new_inquiry)
                    DB_PATH.write_text(json.dumps(local_db, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass
            return self.send_json(200, {"success": True, "message": "Toptan satış talebiniz alındı."})

        # Newsletter POST
        if pathname == "/api/newsletter":
            email = (body.get("email") or "").strip().lower()
            if not email or "@" not in email:
                return self.send_json(400, {"error": "Geçerli bir e-posta adresi giriniz."})
            if DB_PATH.exists():
                try:
                    local_db = json.loads(DB_PATH.read_text(encoding="utf-8"))
                    if "subscribers" not in local_db:
                        local_db["subscribers"] = []
                    if email not in local_db["subscribers"]:
                        local_db["subscribers"].append(email)
                        DB_PATH.write_text(json.dumps(local_db, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass
            return self.send_json(200, {"success": True, "message": "E-bülten kaydınız tamamlandı."})

        # Admin Auth Login
        if pathname == "/api/auth/login":
            pwd = body.get("password", "")
            if pwd == "19071907":
                token = "admin_token_" + str(int(time.time()))
                return self.send_json(200, {"success": True, "token": token})
            return self.send_json(401, {"error": "Hatalı şifre."})

        return self.send_json(404, {"error": "Not Found"})

def run_server():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, GallusMamaHandler)
    print("====================================================")
    print(f"🚀 Gallus Mama Canlı Firestore Sunucusu Başlatıldı! (Port: {PORT})")
    print(f"🌐 Web Sitesi: http://localhost:{PORT}")
    print(f"🔥 Canlı Firestore Senkronizasyonu: AKTİF (stoktakip-1fe40)")
    print("====================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nSunucu kapatıldı.")

if __name__ == "__main__":
    run_server()
