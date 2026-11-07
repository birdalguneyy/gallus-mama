import os
import sys
import json
import time
import mimetypes
from typing import Any, Dict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import urllib.parse
import threading
import base64

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


def parse_numeric_total(val: Any) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    if not val:
        return 0.0
    import re
    s = re.sub(r"[^\d.,-]", "", str(val)).strip()
    if not s:
        return 0.0
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        parts = s.split(",")
        if len(parts[-1]) == 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "." in s:
        parts = s.split(".")
        if len(parts[-1]) == 3:
            s = s.replace(".", "")
    try:
        return float(s)
    except Exception:
        return 0.0


def calc_order_points(total_numeric: Any) -> int:
    num = parse_numeric_total(total_numeric)
    return max(0, int(round((num * 0.01) * 100)))


def load_local_db() -> Dict[str, Any]:
    if DB_PATH.exists():
        try:
            return json.loads(DB_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_local_db(data: Dict[str, Any]) -> None:
    for db_file in [
        BASE_DIR / "data" / "database.json",
        BASE_DIR / "gallus mama" / "data" / "database.json"
    ]:
        try:
            db_file.parent.mkdir(parents=True, exist_ok=True)
            db_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass


def collect_all_emails(local_db: Dict[str, Any]) -> Dict[str, Any]:
    email_set = []
    details_map: Dict[str, Dict[str, Any]] = {}

    def add_email(em: str, name: str = "", phone: str = "", source: str = "Bülten", date_str: str = ""):
        clean = str(em or "").strip().lower()
        if not clean or "@" not in clean:
            return
        if clean not in email_set:
            email_set.append(clean)
        prev = details_map.get(clean, {})
        details_map[clean] = {
            "email": clean,
            "name": name or prev.get("name", ""),
            "phone": phone or prev.get("phone", ""),
            "source": source if not prev.get("source") else prev.get("source"),
            "date": date_str or prev.get("date", "")
        }

    for e in local_db.get("subscribers", []):
        add_email(e, source="Web Bülten")
    for d in local_db.get("subscriberDetails", []):
        if isinstance(d, dict):
            add_email(d.get("email", ""), d.get("name", ""), d.get("phone", ""), d.get("source", "Web Bülten"), d.get("date", ""))
    for m in local_db.get("members", []):
        if isinstance(m, dict):
            add_email(m.get("email", ""), m.get("fullname", ""), m.get("phone", ""), "Site Üyesi", m.get("createdAt", ""))
    for o in local_db.get("orders", []):
        if isinstance(o, dict):
            c = o.get("customer", {}) or {}
            add_email(c.get("email") or o.get("email", ""), c.get("fullname", ""), c.get("phone", ""), "Sipariş Müşterisi", o.get("date", ""))

    return {
        "allEmails": email_set,
        "subscriberDetails": list(details_map.values())
    }


def build_member_payload(local_db: Dict[str, Any], member_obj: Dict[str, Any]) -> Dict[str, Any]:
    if not member_obj:
        return {}
    import re
    email = str(member_obj.get("email") or "").strip().lower()
    phone_clean = re.sub(r"\D", "", str(member_obj.get("phone") or ""))[-10:]
    all_orders = local_db.get("orders", [])
    member_orders = []
    for o in all_orders:
        c = o.get("customer") or {}
        o_email = str(c.get("email") or o.get("email") or "").strip().lower()
        o_phone = re.sub(r"\D", "", str(c.get("phone") or ""))[-10:]
        if (email and o_email and email == o_email) or (len(phone_clean) >= 10 and o_phone == phone_clean):
            member_orders.append(o)

    approved_earned = 0
    pending_earned = 0
    total_used = 0
    for o in member_orders:
        t_num = o.get("totalNumeric") if o.get("totalNumeric") is not None else parse_numeric_total(o.get("total"))
        pts = int(o.get("earnedPoints")) if o.get("earnedPoints") is not None else calc_order_points(t_num)
        used = int(o.get("usedPoints") or 0)
        total_used += used
        if o.get("pointsApproved") is True or o.get("status") in ["Onaylandı", "Tamamlandı"]:
            approved_earned += pts
        elif o.get("status") not in ["İptal", "İptal Edildi"]:
            pending_earned += pts

    bonus = int(member_obj.get("bonusPoints") or 0)
    approved_points = max(0, approved_earned + bonus - total_used)
    pending_points = max(0, pending_earned)

    safe_member = dict(member_obj)
    safe_member.pop("password", None)
    safe_member.update({
        "approvedPoints": approved_points,
        "pendingPoints": pending_points,
        "totalEarnedPoints": approved_earned + bonus,
        "usedPoints": total_used,
        "pointsTlValue": round(approved_points / 100.0, 2),
        "orders": member_orders
    })
    return safe_member


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

        # 2.5 API: Brands
        if pathname == "/api/brands":
            brands = []
            if DB_PATH.exists():
                try:
                    brands = json.loads(DB_PATH.read_text(encoding="utf-8")).get("brands", [])
                except Exception:
                    pass
            return self.send_json(200, brands)

        # 2.6 API: Auth Check
        if pathname == "/api/auth/check":
            return self.send_json(200, {"authenticated": True})

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
            local_db = load_local_db()
            orders = local_db.get("orders", [])
            q_email = str(query.get("email", [""])[0] or "").strip().lower()
            if q_email:
                orders = [o for o in orders if str((o.get("customer") or {}).get("email") or o.get("email") or "").strip().lower() == q_email]
            return self.send_json(200, orders)

        # 3.2 API: Newsletter GET
        if pathname == "/api/newsletter":
            local_db = load_local_db()
            em_data = collect_all_emails(local_db)
            return self.send_json(200, {
                "success": True,
                "subscribers": em_data["allEmails"],
                "subscriberDetails": em_data["subscriberDetails"],
                "count": len(em_data["allEmails"])
            })

        # 3.3 API: Members ME GET
        if pathname == "/api/members/me":
            email = str(query.get("email", [""])[0] or "").strip().lower()
            if not email:
                return self.send_json(400, {"success": False, "error": "E-posta parametresi gerekli."})
            local_db = load_local_db()
            members = local_db.get("members", [])
            member = next((m for m in members if str(m.get("email") or "").lower() == email), None)
            if not member:
                member = {
                    "id": "MEM-GUEST",
                    "fullname": email.split("@")[0],
                    "email": email,
                    "phone": "",
                    "city": "İstanbul",
                    "district": "Silivri",
                    "address": "",
                    "bonusPoints": 0
                }
            return self.send_json(200, {"success": True, "member": build_member_payload(local_db, member)})

        # 3.4 API: Sync Web Data GET (For Stok Satis Takip App)
        if pathname == "/api/sync/web-data":
            local_db = load_local_db()
            em_data = collect_all_emails(local_db)
            enriched_members = [build_member_payload(local_db, m) for m in local_db.get("members", [])]
            return self.send_json(200, {
                "success": True,
                "orders": local_db.get("orders", []),
                "subscribers": em_data["allEmails"],
                "subscriberDetails": em_data["subscriberDetails"],
                "members": enriched_members
            })

        # 4. Robots.txt, Sitemap.xml & Google Shopping XML Feed
        if pathname == "/robots.txt":
            content = "User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /api/\n\nSitemap: https://gallusmama.com/sitemap.xml\n# Google Merchant Center Feed: https://gallusmama.com/google-shopping-feed.xml\n".encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if pathname in ["/google-shopping-feed.xml", "/merchant-feed.xml"]:
            feed_file = PUBLIC_DIR / "google-shopping-feed.xml"
            if feed_file.exists():
                content = feed_file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/xml; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        if pathname == "/sitemap.xml":
            sm_file = PUBLIC_DIR / "sitemap.xml"
            if sm_file.exists():
                content = sm_file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/xml; charset=utf-8")
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

        # 6. SPA fallback -> index.html (with dynamic Google Shopping Product JSON-LD injection)
        index_file = PUBLIC_DIR / "index.html"
        if index_file.exists():
            html_str = index_file.read_text(encoding="utf-8")
            if pathname.startswith("/urun/"):
                slug = pathname.replace("/urun/", "").strip("/")
                prod = next((p for p in in_memory_products if p.get("slug") == slug or p.get("id") == slug), None)
                if prod:
                    img_u = str(prod.get("imageUrl") or "/images/mutlu-patiler-banner.jpg")
                    full_img = img_u if img_u.startswith("http") else f"https://gallusmama.com{img_u}"
                    price_val = float(prod.get("price") or prod.get("sale_price") or 0.0)
                    stock_val = float(prod.get("stock") if prod.get("stock") is not None else (prod.get("stock_quantity") or 0.0))
                    prod_schema = {
                        "@context": "https://schema.org/",
                        "@type": "Product",
                        "name": prod.get("name"),
                        "image": [full_img],
                        "description": f"{prod.get('description', '')} İçindekiler: {prod.get('ingredients', '')} Analiz: {prod.get('analysis', '')}".strip(),
                        "sku": prod.get("sku") or prod.get("id"),
                        "mpn": prod.get("sku") or f"GL-{str(prod.get('id')).upper()}",
                        "category": prod.get("googleProductCategory") or prod.get("categoryName") or "Evcil Hayvan ve Çiftlik Ürünleri",
                        "brand": {"@type": "Brand", "name": prod.get("brand") or "Gallus Mama"},
                        "aggregateRating": {"@type": "AggregateRating", "ratingValue": "4.9", "reviewCount": "38", "bestRating": "5", "worstRating": "1"},
                        "offers": {
                            "@type": "Offer",
                            "url": f"https://gallusmama.com/urun/{prod.get('slug') or prod.get('id')}",
                            "priceCurrency": "TRY",
                            "price": f"{price_val:.2f}",
                            "priceValidUntil": "2027-12-31",
                            "itemCondition": "https://schema.org/NewCondition",
                            "availability": "https://schema.org/InStock" if stock_val > 0 else "https://schema.org/OutOfStock",
                            "seller": {"@type": "Organization", "name": "Gallus Mama & Yumurta"}
                        }
                    }
                    inject_block = (
                        f'\n  <meta property="og:type" content="product">'
                        f'\n  <meta property="product:price:amount" content="{price_val:.2f}">'
                        f'\n  <meta property="product:price:currency" content="TRY">'
                        f'\n  <script type="application/ld+json">{json.dumps(prod_schema, ensure_ascii=False)}</script>\n</head>'
                    )
                    html_str = html_str.replace("</head>", inject_block, 1)
            content = html_str.encode("utf-8")
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
            customer = body.get("customer", {}) or {}
            if not items or not customer:
                return self.send_json(400, {"success": False, "error": "Sipariş detayları ve ürünler zorunludur."})

            order_id = "GL-" + str(int(time.time() * 1000))[-6:]
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            total_numeric = float(body.get("totalNumeric")) if body.get("totalNumeric") is not None else parse_numeric_total(body.get("total"))
            earned_points = int(body.get("earnedPoints")) if body.get("earnedPoints") is not None else calc_order_points(total_numeric)
            used_points = max(0, int(body.get("usedPoints") or 0))
            cust_email = str(customer.get("email") or body.get("email") or "").strip().lower()
            customer["email"] = cust_email
            payment_method = body.get("paymentMethod") or "Havale / EFT"

            new_order = {
                "id": order_id,
                "date": now_str,
                "customer": customer,
                "email": cust_email,
                "paymentMethod": payment_method,
                "items": items,
                "total": body.get("total") or f"{total_numeric:.2f} ₺",
                "totalNumeric": total_numeric,
                "earnedPoints": earned_points,
                "usedPoints": used_points,
                "pointsApproved": False,
                "status": "Onay Bekliyor",
                "source": "web"
            }

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
                            
                            prod_ref = db.collection("products").document(str(pid))
                            snap = prod_ref.get(transaction=txn)
                            
                            if not snap.exists:
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

                    order_doc = dict(new_order)
                    order_doc["createdAt"] = firestore.SERVER_TIMESTAMP
                    db.collection("orders").document(order_id).set(order_doc)

                    if cust_email and "@" in cust_email:
                        try:
                            db.collection("newsletter_subscribers").document(cust_email).set({
                                "email": cust_email,
                                "name": customer.get("fullname", ""),
                                "phone": customer.get("phone", ""),
                                "source": "Sipariş",
                                "date": now_str
                            }, merge=True)
                        except Exception:
                            pass

                    sale_doc = {
                        "id": int(order_id.replace("GL-", "")),
                        "user_id": 6,
                        "total_amount": total_numeric or 100.0,
                        "payment_type": payment_method,
                        "created_at": now_str,
                        "note": f"Web Siparişi ({order_id}): {customer.get('fullname', '')} ({customer.get('phone', '')}) - {cust_email}",
                        "items": items
                    }
                    db.collection("sales").document(f"u6_s{order_id.replace('GL-', '')}").set(sale_doc)

                except ValueError as val_err:
                    return self.send_json(400, {"success": False, "error": str(val_err)})
                except Exception as ex:
                    print(f"[WARN] Firestore order transaction warning: {ex}")

            # Record in local database.json
            local_db = load_local_db()
            if "orders" not in local_db:
                local_db["orders"] = []
            local_db["orders"].insert(0, new_order)

            if cust_email and "@" in cust_email:
                if "subscribers" not in local_db:
                    local_db["subscribers"] = []
                if cust_email not in local_db["subscribers"]:
                    local_db["subscribers"].append(cust_email)
                if "subscriberDetails" not in local_db:
                    local_db["subscriberDetails"] = []
                if not any(str(s.get("email") or "").lower() == cust_email for s in local_db["subscriberDetails"]):
                    local_db["subscriberDetails"].insert(0, {
                        "email": cust_email,
                        "name": customer.get("fullname", ""),
                        "phone": customer.get("phone", ""),
                        "source": "Sipariş",
                        "date": now_str
                    })

            save_local_db(local_db)
            return self.send_json(201, {"success": True, "order": new_order})

        # Order Approve & Loyalty Points Activation POST
        if pathname == "/api/orders/approve":
            order_id = str(body.get("orderId") or body.get("id") or "").strip()
            if not order_id:
                return self.send_json(400, {"success": False, "error": "orderId zorunludur."})
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            local_db = load_local_db()
            orders = local_db.get("orders", [])
            ord_obj = next((o for o in orders if o.get("id") == order_id), None)
            if ord_obj:
                ord_obj["pointsApproved"] = True
                ord_obj["status"] = body.get("status") or "Onaylandı"
                ord_obj["approvedAt"] = now_str
                if ord_obj.get("earnedPoints") is None:
                    ord_obj["earnedPoints"] = calc_order_points(ord_obj.get("totalNumeric") or ord_obj.get("total"))
                save_local_db(local_db)

            if db:
                try:
                    db.collection("orders").document(order_id).set({
                        "pointsApproved": True,
                        "status": body.get("status") or "Onaylandı",
                        "approvedAt": now_str
                    }, merge=True)
                except Exception:
                    pass

            updated_member = None
            cust_email = ""
            if ord_obj:
                cust_email = str((ord_obj.get("customer") or {}).get("email") or ord_obj.get("email") or "").strip().lower()
            if not cust_email:
                cust_email = str(body.get("email") or "").strip().lower()

            if cust_email:
                m_obj = next((m for m in local_db.get("members", []) if str(m.get("email") or "").lower() == cust_email), None)
                if m_obj:
                    updated_member = build_member_payload(local_db, m_obj)
                    if db:
                        try:
                            db.collection("web_members").document(cust_email).set({
                                "approvedPoints": updated_member["approvedPoints"],
                                "pendingPoints": updated_member["pendingPoints"],
                                "updatedAt": now_str
                            }, merge=True)
                        except Exception:
                            pass

            return self.send_json(200, {
                "success": True,
                "message": f"Sipariş ({order_id}) ve kazanılan puanlar onaylandı!",
                "order": ord_obj or {"id": order_id, "pointsApproved": True, "status": "Onaylandı"},
                "member": updated_member
            })

        # Members Register (Fast & Standard) POST
        if pathname == "/api/members/register":
            email = str(body.get("email") or "").strip().lower()
            fullname = str(body.get("fullname") or body.get("name") or "").strip()
            phone = str(body.get("phone") or "").strip()
            password = str(body.get("password") or "123456").strip()
            city = str(body.get("city") or "İstanbul").strip()
            district = str(body.get("district") or "Silivri").strip()
            street = str(body.get("street") or "").strip()
            address = str(body.get("address") or "").strip()

            if not email or "@" not in email:
                return self.send_json(400, {"success": False, "error": "Lütfen geçerli bir e-posta adresi giriniz."})

            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            local_db = load_local_db()
            if "members" not in local_db:
                local_db["members"] = []

            member = next((m for m in local_db["members"] if str(m.get("email") or "").lower() == email), None)
            if member:
                if fullname: member["fullname"] = fullname
                if phone: member["phone"] = phone
                if body.get("password"): member["password"] = password
                if city: member["city"] = city
                if district: member["district"] = district
                if street: member["street"] = street
                if address: member["address"] = address
                member["updatedAt"] = now_str
            else:
                member = {
                    "id": "MEM-" + str(int(time.time() * 1000))[-6:],
                    "fullname": fullname or email.split("@")[0],
                    "email": email,
                    "phone": phone,
                    "password": password,
                    "city": city,
                    "district": district,
                    "street": street,
                    "address": address,
                    "bonusPoints": 0,
                    "createdAt": now_str,
                    "updatedAt": now_str
                }
                local_db["members"].insert(0, member)

            if "subscribers" not in local_db:
                local_db["subscribers"] = []
            if email not in local_db["subscribers"]:
                local_db["subscribers"].append(email)
            if "subscriberDetails" not in local_db:
                local_db["subscriberDetails"] = []
            if not any(str(s.get("email") or "").lower() == email for s in local_db["subscriberDetails"]):
                local_db["subscriberDetails"].insert(0, {
                    "email": email,
                    "name": member["fullname"],
                    "phone": member["phone"],
                    "source": body.get("source") or "Hızlı Üyelik",
                    "date": now_str
                })

            save_local_db(local_db)
            enriched = build_member_payload(local_db, member)

            if db:
                try:
                    fs_member = dict(enriched)
                    fs_member.pop("orders", None)
                    db.collection("web_members").document(email).set(fs_member, merge=True)
                    db.collection("newsletter_subscribers").document(email).set({
                        "email": email,
                        "name": member["fullname"],
                        "phone": member["phone"],
                        "source": body.get("source") or "Hızlı Üyelik",
                        "date": now_str
                    }, merge=True)
                except Exception:
                    pass

            return self.send_json(200, {
                "success": True,
                "message": "Üyeliğiniz başarıyla oluşturuldu!",
                "member": enriched
            })

        # Members Login POST
        if pathname == "/api/members/login":
            import re
            identifier = str(body.get("email") or body.get("identifier") or "").strip().lower()
            password = str(body.get("password") or "").strip()
            if not identifier:
                return self.send_json(400, {"success": False, "error": "E-posta veya telefon numarası giriniz."})

            local_db = load_local_db()
            clean_phone = re.sub(r"\D", "", identifier)[-10:]
            member = None
            for m in local_db.get("members", []):
                m_email = str(m.get("email") or "").lower()
                m_phone = re.sub(r"\D", "", str(m.get("phone") or ""))[-10:]
                if m_email == identifier or (len(clean_phone) >= 10 and m_phone == clean_phone):
                    member = m
                    break

            if not member:
                return self.send_json(404, {"success": False, "error": "Bu e-posta ile kayıtlı üye bulunamadı. Hızlı Üyelik sekmesinden hemen kayıt olabilirsiniz."})

            if member.get("password") and password and member.get("password") != password:
                return self.send_json(401, {"success": False, "error": "Şifreniz hatalı. Lütfen kontrol edip tekrar deneyin."})

            return self.send_json(200, {
                "success": True,
                "message": "Giriş başarılı!",
                "member": build_member_payload(local_db, member)
            })

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
            local_db = load_local_db()
            if "wholesaleInquiries" not in local_db:
                local_db["wholesaleInquiries"] = []
            local_db["wholesaleInquiries"].insert(0, new_inquiry)
            save_local_db(local_db)
            return self.send_json(200, {"success": True, "message": "Toptan satış talebiniz alındı."})

        # Newsletter POST
        if pathname == "/api/newsletter":
            email = (body.get("email") or "").strip().lower()
            if not email or "@" not in email:
                return self.send_json(400, {"error": "Geçerli bir e-posta adresi giriniz."})
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            local_db = load_local_db()
            if "subscribers" not in local_db:
                local_db["subscribers"] = []
            if email not in local_db["subscribers"]:
                local_db["subscribers"].append(email)
            if "subscriberDetails" not in local_db:
                local_db["subscriberDetails"] = []
            if not any(str(s.get("email") or "").lower() == email for s in local_db["subscriberDetails"]):
                local_db["subscriberDetails"].insert(0, {
                    "email": email,
                    "name": body.get("name") or body.get("fullname") or "",
                    "phone": body.get("phone") or "",
                    "source": body.get("source") or "Web Bülten",
                    "date": now_str
                })
            save_local_db(local_db)
            if db:
                try:
                    db.collection("newsletter_subscribers").document(email).set({
                        "email": email,
                        "name": body.get("name") or body.get("fullname") or "",
                        "phone": body.get("phone") or "",
                        "source": body.get("source") or "Web Bülten",
                        "date": now_str
                    }, merge=True)
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

        # Image Upload POST
        if pathname == "/api/upload":
            raw_img = body.get("image", "")
            if not raw_img or "base64," not in raw_img:
                return self.send_json(400, {"error": "Geçersiz base64 görsel verisi."})
            
            try:
                header, data = raw_img.split("base64,", 1)
                ext = "jpg"
                if "png" in header: ext = "png"
                elif "webp" in header: ext = "webp"
                elif "svg" in header: ext = "svg"
                
                img_bytes = base64.b64decode(data)
                filename = f"up_{int(time.time())}_{os.urandom(3).hex()}.{ext}"
                
                for upload_dir in [
                    BASE_DIR / "public" / "images" / "uploads",
                    BASE_DIR / "gallus mama" / "public" / "images" / "uploads"
                ]:
                    upload_dir.mkdir(parents=True, exist_ok=True)
                    (upload_dir / filename).write_bytes(img_bytes)
                
                return self.send_json(200, {"success": True, "url": f"/images/uploads/{filename}", "filename": filename})
            except Exception as e:
                return self.send_json(500, {"error": f"Yükleme hatası: {str(e)}"})

        # Batch Save All (WordPress Live Edit Mode) POST
        if pathname == "/api/admin/save-all":
            try:
                local_db = {}
                if DB_PATH.exists():
                    local_db = json.loads(DB_PATH.read_text(encoding="utf-8"))
                
                site_info = body.get("siteInfo")
                if site_info and isinstance(site_info, dict):
                    if "siteInfo" not in local_db: local_db["siteInfo"] = {}
                    local_db["siteInfo"].update(site_info)
                    if db:
                        try:
                            db.collection("site_settings").document("main").set(local_db["siteInfo"], merge=True)
                        except Exception:
                            pass

                categories = body.get("categories")
                if categories and isinstance(categories, list):
                    local_db["categories"] = categories
                    global in_memory_categories
                    in_memory_categories = list(categories)

                brands = body.get("brands")
                if brands and isinstance(brands, list):
                    local_db["brands"] = brands
                
                products = body.get("products")
                if products and isinstance(products, list):
                    if body.get("replaceAllProducts") or len(products) > 5:
                        local_db["products"] = products
                        global in_memory_products
                        in_memory_products = list(products)
                    else:
                        existing_prods = local_db.get("products", [])
                        for up in products:
                            idx = next((i for i, ep in enumerate(existing_prods) if ep.get("id") == up.get("id")), -1)
                            if idx >= 0:
                                existing_prods[idx].update(up)
                            else:
                                existing_prods.append(up)
                        local_db["products"] = existing_prods
                        in_memory_products = list(existing_prods)
                
                # Write to both root and nested database.json
                for db_file in [
                    BASE_DIR / "data" / "database.json",
                    BASE_DIR / "gallus mama" / "data" / "database.json"
                ]:
                    db_file.parent.mkdir(parents=True, exist_ok=True)
                    db_file.write_text(json.dumps(local_db, ensure_ascii=False, indent=2), encoding="utf-8")
                
                # If Firestore is connected, sync metadata to public_products & product_web_meta
                if db and products and isinstance(products, list):
                    try:
                        batch = db.batch()
                        for p in products:
                            doc_id = p.get("doc_id") or p.get("id")
                            if doc_id:
                                pub_ref = db.collection("public_products").document(doc_id)
                                batch.set(pub_ref, {
                                    "id": doc_id,
                                    "name": p.get("name"),
                                    "price": float(p.get("price") or 0.0),
                                    "sale_price": float(p.get("price") or 0.0),
                                    "stock": float(p.get("stock") or 0.0),
                                    "stock_quantity": float(p.get("stock") or 0.0),
                                    "unit": p.get("unit", "adet"),
                                    "category": p.get("category", "diger"),
                                    "categoryName": p.get("categoryName", "Diğer"),
                                    "brand": p.get("brand", "Gallus Mama"),
                                    "packaging": p.get("packaging") or p.get("unit") or "Standart",
                                    "imageUrl": p.get("imageUrl", ""),
                                    "description": p.get("description", ""),
                                    "ingredients": p.get("ingredients", ""),
                                    "analysis": p.get("analysis", ""),
                                    "usage": p.get("usage", ""),
                                    "specs": p.get("specs", {}),
                                    "isPopular": bool(p.get("isPopular")),
                                    "isFeatured": bool(p.get("isFeatured")),
                                    "badge": p.get("badge", ""),
                                    "updatedAt": firestore.SERVER_TIMESTAMP
                                }, merge=True)
                                
                                meta_ref = db.collection("product_web_meta").document(doc_id)
                                batch.set(meta_ref, {
                                    "category": p.get("category", "diger"),
                                    "categoryName": p.get("categoryName", "Diğer"),
                                    "brand": p.get("brand", "Gallus Mama"),
                                    "packaging": p.get("packaging") or p.get("unit") or "Standart",
                                    "description": p.get("description", ""),
                                    "imageUrl": p.get("imageUrl", ""),
                                    "badge": p.get("badge", ""),
                                    "updatedAt": firestore.SERVER_TIMESTAMP
                                }, merge=True)
                        batch.commit()
                    except Exception as fs_err:
                        print(f"[WARN] Firestore sync warning: {fs_err}")
                
                return self.send_json(200, {
                    "success": True, 
                    "message": "Tüm site içerikleri ve ürünler kalıcı olarak kaydedildi! Sunucu yeniden başlasa bile korunur.",
                    "productCount": len(products) if products else len(local_db.get("products", []))
                })
            except Exception as e:
                return self.send_json(500, {"error": f"Kayıt hatası: {str(e)}"})

        return self.send_json(404, {"error": "Not Found"})

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        pathname = parsed.path
        content_len = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            body = json.loads(raw_body)
        except Exception:
            body = {}

        if pathname == "/api/members/profile":
            email = str(body.get("email") or "").strip().lower()
            if not email:
                return self.send_json(400, {"success": False, "error": "E-posta gerekli."})
            local_db = load_local_db()
            member = next((m for m in local_db.get("members", []) if str(m.get("email") or "").lower() == email), None)
            if not member:
                return self.send_json(404, {"success": False, "error": "Üye bulunamadı."})
            for k in ["fullname", "phone", "city", "district", "street", "address"]:
                if body.get(k) is not None:
                    member[k] = str(body.get(k)).strip()
            member["updatedAt"] = time.strftime("%Y-%m-%d %H:%M:%S")
            save_local_db(local_db)
            return self.send_json(200, {"success": True, "member": build_member_payload(local_db, member)})

        if pathname == "/api/info":
            local_db = load_local_db()
            if "siteInfo" not in local_db:
                local_db["siteInfo"] = {}
            local_db["siteInfo"].update(body)
            save_local_db(local_db)
            return self.send_json(200, {"success": True, "siteInfo": local_db["siteInfo"]})

        return self.send_json(404, {"error": "Not Found"})

def run_server():
    server_address = ("", PORT)
    httpd = ThreadingHTTPServer(server_address, GallusMamaHandler)
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
