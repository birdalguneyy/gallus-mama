import re
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
import firebase_admin
from firebase_admin import credentials, firestore

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("firestore_sync")

# Path to service account key
CRED_PATH = Path(r"C:\Users\birdo\Projects\stok-satis-takip\firebase_credentials.json")
if not CRED_PATH.exists():
    CRED_PATH = Path(__file__).resolve().parent / "firebase_credentials.json"

if not firebase_admin._apps:
    cred = credentials.Certificate(str(CRED_PATH))
    firebase_admin.initialize_app(cred)

db = firestore.client()

CATEGORIES = [
    {"id": "kedi", "name": "Kedi Mamaları ve Ürünleri", "icon": "🐱"},
    {"id": "kopek", "name": "Köpek Mamaları ve Ürünleri", "icon": "🐶"},
    {"id": "tavuk-civciv", "name": "Tavuk ve Civciv Yemleri", "icon": "🐓"},
    {"id": "guvercin", "name": "Güvercin Yemleri", "icon": "🕊️"},
    {"id": "balik-akvaryum", "name": "Balık Yemleri ve Akvaryum", "icon": "🐠"},
    {"id": "kumes-ekipman", "name": "Kümes Ekipmanları", "icon": "🏡"},
    {"id": "tarim-bahce", "name": "Tarım ve Bahçe Ürünleri", "icon": "🌱"},
    {"id": "diger", "name": "Diğer Ürünler", "icon": "✨"}
]

# Curated High-Quality Product Images
IMAGE_MAP = {
    # Cat products
    "reflex_plus_cat": "https://images.unsplash.com/photo-1548767797-d8c844163c4c?auto=format&fit=crop&w=600&q=80",
    "reflex_cat": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?auto=format&fit=crop&w=600&q=80",
    "trendline_cat": "https://images.unsplash.com/photo-1574158622682-e40e69881006?auto=format&fit=crop&w=600&q=80",
    "enjoy_cat": "https://images.unsplash.com/photo-1548767797-d8c844163c4c?auto=format&fit=crop&w=600&q=80",
    "pancho_cat": "https://images.unsplash.com/photo-1568640347023-a616a30bc3bd?auto=format&fit=crop&w=600&q=80",
    "pure_life_cat": "https://images.unsplash.com/photo-1573865526739-10659fec78a5?auto=format&fit=crop&w=600&q=80",
    "cat_litter": "https://images.unsplash.com/photo-1518791841217-8f162f1e1131?auto=format&fit=crop&w=600&q=80",
    "cat_canned": "https://images.unsplash.com/photo-1535930891776-0c2dfb7fda1a?auto=format&fit=crop&w=600&q=80",
    "default_cat": "https://images.unsplash.com/photo-1548767797-d8c844163c4c?auto=format&fit=crop&w=600&q=80",

    # Dog products
    "reflex_plus_dog": "https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?auto=format&fit=crop&w=600&q=80",
    "reflex_care": "https://images.unsplash.com/photo-1516734212186-a967f81ad0d7?auto=format&fit=crop&w=600&q=80",
    "trendline_dog": "https://images.unsplash.com/photo-1543466835-00a7907e9de1?auto=format&fit=crop&w=600&q=80",
    "enjoy_dog": "https://images.unsplash.com/photo-1587300003388-59208cc962cb?auto=format&fit=crop&w=600&q=80",
    "king_dog": "https://images.unsplash.com/photo-1537151625747-768eb6cf92b2?auto=format&fit=crop&w=600&q=80",
    "pancho_dog": "https://images.unsplash.com/photo-1568640347023-a616a30bc3bd?auto=format&fit=crop&w=600&q=80",
    "dog_canned": "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?auto=format&fit=crop&w=600&q=80",
    "default_dog": "https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?auto=format&fit=crop&w=600&q=80",

    # Poultry & Farm
    "chicken_feed": "/images/tavuklar.jpg",
    "farm_eggs": "/images/yumurta-koli-banner.jpg",

    # Pigeon / Grains
    "wheat_grain": "https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?auto=format&fit=crop&w=600&q=80",

    # Bird
    "bird_feed": "https://images.unsplash.com/photo-1552728089-57bdde30beb3?auto=format&fit=crop&w=600&q=80",

    # Equipment
    "equipment": "https://images.unsplash.com/photo-1541599540903-216a46ca1dc0?auto=format&fit=crop&w=600&q=80",
    "general": "/images/mutlu-patiler-banner.jpg"
}

def detect_category(name: str, cat_name: str = "") -> Tuple[str, str]:
    text = (name + " " + cat_name).lower()

    # 1. Kümes & Pet Ekipmanları
    if any(k in text for k in ["taşıma kutusu", "tasima kutusu", "taşıma kafesi", "tasima kafesi", "suluk", "yemlik", "folluk", "tünek", "minder", "kafes"]):
        return "kumes-ekipman", "Kümes Ekipmanları"

    # 2. Balık & Akvaryum
    if any(k in text for k in ["balık", "balik", "akvaryum", "aquarium", "pul yem", "tetra"]):
        return "balik-akvaryum", "Balık Yemleri ve Akvaryum"

    # 3. Kedi Mamaları ve Ürünleri
    if any(k in text for k in ["kedi", "cat", "kitten", "kum", "litter", "marsilya", "lavanta kokulu", "aktif karbon", "koku giderici", "white fish", "multicolor cat"]):
        return "kedi", "Kedi Mamaları ve Ürünleri"

    # 4. Köpek Mamaları ve Ürünleri
    if any(k in text for k in ["köpek", "kopek", "dog", "puppy", "biftekli", "çoban", "kuzu etli yavru köpek", "alıştırma pedi", "şampuanı", "sampo", "tüy rengini", "haşere önleyici"]):
        return "kopek", "Köpek Mamaları ve Ürünleri"

    # 5. Tavuk ve Civciv Yemleri
    if any(k in text for k in ["tavuk yemi", "civciv", "yumurta yemi", "piliç", "kanatlı yemi"]):
        return "tavuk-civciv", "Tavuk ve Civciv Yemleri"

    # 6. Güvercin Yemleri
    if any(k in text for k in ["güvercin", "guvercin", "buğday", "bugday", "mısır", "darı", "fiğ", "aspir"]):
        return "guvercin", "Güvercin Yemleri"

    # 7. Tarım ve Bahçe Ürünleri
    if any(k in text for k in ["gübre", "gubre", "tohum", "bahçe", "bahce", "fide", "toprak", "torf"]):
        return "tarim-bahce", "Tarım ve Bahçe Ürünleri"

    # 8. Diğer Ürünler (Taze Yumurta, Kuş Yemi, vb.)
    return "diger", "Diğer Ürünler"

def detect_brand(name: str) -> str:
    upper_name = name.strip().upper()
    if "REFLEX PLUS" in upper_name:
        return "Reflex Plus"
    if "REFLEX CARE" in upper_name:
        return "Reflex Care"
    if "REFLEX" in upper_name:
        return "Reflex"
    if "TRENDLINE" in upper_name:
        return "Trendline"
    if "ENJOY" in upper_name:
        return "Enjoy"
    if "PANCHO" in upper_name:
        return "Pancho"
    if "KING" in upper_name:
        return "King"
    if "PURE LIFE" in upper_name:
        return "Pure Life"
    if "DREAMCAT" in upper_name:
        return "Dreamcat"
    if "SOPRESH" in upper_name:
        return "Sopresh"
    if any(k in upper_name for k in ["YUMURTA", "GEZEN TAVUK", "GALLUS", "CİVCİV"]):
        return "Gallus Çiftlik"
    return "Gallus Pet"

def detect_packaging(name: str, unit: str = "adet") -> str:
    text = name.strip()
    match = re.search(r"(\d+(\.\d+)?\s*(kg|g|l|ml|'lu|li|'li|koli|adet))", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match_dim = re.search(r"(\d+x\d+)", text, re.IGNORECASE)
    if match_dim:
        return match_dim.group(1).strip()
    if unit and unit != "adet":
        return f"1 {unit}"
    return "Standart Ambalaj"

def resolve_image(name: str, category_id: str, existing_image: str = "") -> str:
    # If existing image is a valid remote URL or local absolute path, keep it
    if existing_image and (existing_image.startswith("http") or existing_image.startswith("/images/")):
        return existing_image
    
    n = name.lower()
    if "yumurta" in n:
        return IMAGE_MAP["farm_eggs"]
    if "tavuk yemi" in n or "civciv" in n:
        return IMAGE_MAP["chicken_feed"]
    if "buğday" in n or "bugday" in n:
        return IMAGE_MAP["wheat_grain"]
    if "muhabbet" in n or "kuş" in n or "kus" in n:
        return IMAGE_MAP["bird_feed"]
    if "kum" in n or "litter" in n or "koku giderici" in n:
        return IMAGE_MAP["cat_litter"]
    if "konserve" in n or "400g" in n or "85g" in n:
        return IMAGE_MAP["cat_canned"] if category_id == "kedi" else IMAGE_MAP["dog_canned"]
    if "taşıma" in n or "tasima" in n or "kafes" in n or "minder" in n:
        return IMAGE_MAP["equipment"]
    if "şampuan" in n or "ped" in n or "tüy" in n:
        return IMAGE_MAP["reflex_care"]

    if category_id == "kedi":
        if "reflex plus" in n:
            return IMAGE_MAP["reflex_plus_cat"]
        if "reflex" in n:
            return IMAGE_MAP["reflex_cat"]
        if "trendline" in n:
            return IMAGE_MAP["trendline_cat"]
        if "enjoy" in n:
            return IMAGE_MAP["enjoy_cat"]
        if "pancho" in n:
            return IMAGE_MAP["pancho_cat"]
        if "pure life" in n:
            return IMAGE_MAP["pure_life_cat"]
        return IMAGE_MAP["default_cat"]

    if category_id == "kopek":
        if "reflex plus" in n:
            return IMAGE_MAP["reflex_plus_dog"]
        if "trendline" in n:
            return IMAGE_MAP["trendline_dog"]
        if "enjoy" in n:
            return IMAGE_MAP["enjoy_dog"]
        if "king" in n:
            return IMAGE_MAP["king_dog"]
        if "pancho" in n:
            return IMAGE_MAP["pancho_dog"]
        return IMAGE_MAP["default_dog"]

    return IMAGE_MAP["general"]

def generate_seo_description(name: str, category_id: str, brand: str, packaging: str) -> str:
    n = name.lower()
    if "yumurta" in n:
        return (
            f"Silivri Değirmenköy'deki biyogüvenlikli gezen tavuk çiftliğimizden her sabah günlük toplanan "
            f"katkısız ve taze {name}. Doğal beslenen tavuklarımızdan sofranıza yüksek proteinli, altın sarısı lezzet."
        )
    if "kum" in n or "litter" in n or "koku giderici" in n:
        return (
            f"{brand} kalitesiyle sunulan {name}. Üstün sıvı hapsetme, güçlü topaklanma ve koku nötralize "
            f"edici formülüyle kediniz için maksimum hijyen, eviniz için kalıcı ferahlık sağlar."
        )
    if "konserve" in n or "400g" in n or "85g" in n:
        if category_id == "kedi":
            return (
                f"{brand} taze ve lezzetli {name}. Kedinizin damak zevkine uygun zengin protein ve vitamin dengesiyle "
                f"günlük sıvı ve enerji ihtiyacını destekleyen tam ve dengeli ıslak mama."
            )
        else:
            return (
                f"{brand} taze et içerikli {name}. Köpeğinizin iştahla tüketeceği, kas yapısını ve sindirim sistemini "
                f"destekleyen besleyici konserve ıslak mama."
            )
    if category_id == "kedi":
        if "kısır" in n or "steril" in n:
            return (
                f"{brand} kısırlaştırılmış yetişkin kediler için özel formüle edilmiş {name} ({packaging}). "
                f"Düşük yağ oranıyla kilo kontrolünü destekler, dengeli mineral içeriğiyle idrar yolu sağlığını korur."
            )
        elif "yavru" in n or "kitten" in n:
            return (
                f"{brand} yavru kedilerin büyüme dönemine özel üretilmiş {name} ({packaging}). "
                f"Gelişmiş DHA, kalsiyum ve yüksek sindirilebilir protein içeriğiyle güçlü bağışıklık ve kemik gelişimi sağlar."
            )
        else:
            return (
                f"{brand} yetişkin kediler için tam ve dengeli beslenme sunan {name} ({packaging}). "
                f"Kaliteli protein kaynakları, omega yağ asitleri ve vitamin desteğiyle parlak tüy ve canlılık sağlar."
            )
    if category_id == "kopek":
        if "yavru" in n or "puppy" in n:
            return (
                f"{brand} yavru köpeklerin sağlıklı büyüme evresini destekleyen {name} ({packaging}). "
                f"Yüksek enerji, kalsiyum ve dengeli protein içeriğiyle sağlıklı iskelet ve kas yapısı kazandırır."
            )
        elif "şampuan" in n or "ped" in n or "bakım" in n or "tüy" in n:
            return (
                f"{brand} evcil hayvan bakım serisinden {name}. "
                f"Dostunuzun günlük temizlik, hijyen ve deri sağlığı gereksinimlerini güvenle karşılayan profesyonel bakım ürünü."
            )
        else:
            return (
                f"{brand} yetişkin köpeklerin günlük enerji ve kondisyon ihtiyacını karşılayan {name} ({packaging}). "
                f"Yüksek sindirilebilir et proteini ve vitamin takviyesiyle güçlü bağışıklık ve enerjik yaşam sunar."
            )
    if category_id == "tavuk-civciv":
        if "civciv" in n:
            return (
                f"Civcivlerin ilk haftalarından itibaren sağlıklı büyümesini ve bağışıklık kazanmasını sağlayan "
                f"özel formüle edilmiş {name}. Doğal vitamin ve mineral destekli taze yem."
            )
        else:
            return (
                f"Gezen tavuk ve yumurta tavukları için dengeli rasyonla hazırlanmış yüksek verimli {name}. "
                f"Doğal yumurtlama performansı ve kemik sağlığı için optimum kalsiyum ve protein içerir."
            )
    if category_id == "guvercin":
        return (
            f"Güvercinlerin ve kanatlıların sağlıklı beslenmesi için elenmiş, tozsuz ve birinci kalite {name}. "
            f"Kuşlarınızın tüy yapısını, kas gücünü ve uçuş kondisyonunu destekleyen doğal tahıl."
        )
    if category_id == "kumes-ekipman":
        return (
            f"Evcil ve çiftlik hayvanlarınız için ergonomik, dayanıklı ve uzun ömürlü {name}. "
            f"Güvenli taşıma, konforlu barınma ve pratik kullanım sunan kaliteli ekipman."
        )
    return (
        f"Gallus Mama güvencesiyle sunulan {name}. "
        f"Doğal içerikli, kaliteli ve güvenli üretim standartlarına sahip orijinal ürün."
    )

def slugify(text: str) -> str:
    text = text.lower().strip()
    replacements = {
        'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c',
        'I': 'i', 'Ğ': 'g', 'Ü': 'u', 'Ş': 's', 'Ö': 'o', 'Ç': 'c'
    }
    for tr, en in replacements.items():
        text = text.replace(tr, en)
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def sync_all_products(user_id: int = 6):
    """Firestore 'products' koleksiyonundan tüm ürünleri okur,
    'product_web_meta' ve 'public_products' koleksiyonlarını günceller."""
    logger.info("Firestore ürünleri senkronize ediliyor...")
    
    products_stream = db.collection("products").stream()
    synced_count = 0

    batch = db.batch()
    batch_ops = 0

    for doc in products_stream:
        d = doc.to_dict()
        doc_uid = d.get("user_id")

        # GALLUS2 (User 6) or active Gallus products
        if doc_uid != user_id and not doc.id.startswith(f"u{user_id}_"):
            continue

        doc_id = doc.id
        pid = d.get("id") or doc_id
        name = str(d.get("name") or "").strip()
        if not name:
            continue

        sale_price = float(d.get("sale_price") or 0.0)
        stock_quantity = float(d.get("stock_quantity") or 0.0)
        unit = str(d.get("unit") or "adet").strip()
        is_active = int(d.get("is_active", 1))

        # Check existing metadata if any
        meta_ref = db.collection("product_web_meta").document(doc_id)
        meta_doc = meta_ref.get()
        meta_data = meta_doc.to_dict() if meta_doc.exists else {}

        # Classify product
        cat_id, cat_name = detect_category(name, d.get("category_name", ""))
        brand = meta_data.get("brand") or detect_brand(name)
        packaging = meta_data.get("packaging") or detect_packaging(name, unit)
        description = meta_data.get("description") or generate_seo_description(name, cat_id, brand, packaging)
        image_url = meta_data.get("imageUrl") or resolve_image(name, cat_id, d.get("image_path", ""))
        slug = meta_data.get("slug") or f"{slugify(name)}-{str(pid)}"

        is_popular = meta_data.get("isPopular", stock_quantity > 10 and sale_price > 50)
        badge = meta_data.get("badge", "Çok Satan" if is_popular else "")

        # 1. Update product_web_meta
        new_meta = {
            "id": pid,
            "productId": doc_id,
            "category": cat_id,
            "categoryName": cat_name,
            "brand": brand,
            "packaging": packaging,
            "description": description,
            "imageUrl": image_url,
            "slug": slug,
            "isPopular": bool(is_popular),
            "badge": badge,
            "updatedAt": firestore.SERVER_TIMESTAMP
        }
        batch.set(meta_ref, new_meta, merge=True)
        batch_ops += 1

        # 2. Update public_products (Sanitized, NO purchase_price!)
        public_ref = db.collection("public_products").document(doc_id)
        public_doc = {
            "id": doc_id,
            "productId": pid,
            "name": name,
            "sale_price": sale_price,
            "price": sale_price,
            "stock_quantity": stock_quantity,
            "stock": stock_quantity,
            "unit": unit,
            "is_active": is_active,
            "category": cat_id,
            "categoryId": cat_id,
            "categoryName": cat_name,
            "brand": brand,
            "packaging": packaging,
            "description": description,
            "imageUrl": image_url,
            "slug": slug,
            "isPopular": bool(is_popular),
            "badge": badge,
            "inStock": stock_quantity > 0,
            "updatedAt": firestore.SERVER_TIMESTAMP
        }
        batch.set(public_ref, public_doc, merge=True)
        batch_ops += 1
        synced_count += 1

        if batch_ops >= 400:
            batch.commit()
            batch = db.batch()
            batch_ops = 0

    if batch_ops > 0:
        batch.commit()

    logger.info(f"Başarıyla {synced_count} ürün 'public_products' ve 'product_web_meta' ile eşitlendi.")
    return synced_count

def start_realtime_listener(user_id: int = 6):
    """Firestore 'products' koleksiyonunu canlı dinler ve
    Stok Satış Takip'te yapılan her değişikliği anında 'public_products'a aktarır."""
    logger.info("Canlı Firestore 'products' listener başlatılıyor...")

    def on_snapshot(col_snapshot, changes, read_time):
        for change in changes:
            doc = change.document
            d = doc.to_dict()
            doc_id = doc.id

            if d.get("user_id") != user_id and not doc_id.startswith(f"u{user_id}_"):
                continue

            if change.type.name == "REMOVED":
                logger.info(f"Ürün silindi: {doc_id}")
                db.collection("public_products").document(doc_id).delete()
            else:
                # ADDED or MODIFIED
                name = str(d.get("name") or "").strip()
                if not name:
                    continue
                sale_price = float(d.get("sale_price") or 0.0)
                stock_quantity = float(d.get("stock_quantity") or 0.0)
                unit = str(d.get("unit") or "adet").strip()
                is_active = int(d.get("is_active", 1))

                # Fetch meta
                meta_doc = db.collection("product_web_meta").document(doc_id).get()
                meta = meta_doc.to_dict() if meta_doc.exists else {}

                cat_id, cat_name = detect_category(name, d.get("category_name", ""))
                brand = meta.get("brand") or detect_brand(name)
                packaging = meta.get("packaging") or detect_packaging(name, unit)
                description = meta.get("description") or generate_seo_description(name, cat_id, brand, packaging)
                image_url = meta.get("imageUrl") or resolve_image(name, cat_id, d.get("image_path", ""))
                slug = meta.get("slug") or f"{slugify(name)}-{str(d.get('id') or doc_id)}"

                public_doc = {
                    "id": doc_id,
                    "productId": d.get("id") or doc_id,
                    "name": name,
                    "sale_price": sale_price,
                    "price": sale_price,
                    "stock_quantity": stock_quantity,
                    "stock": stock_quantity,
                    "unit": unit,
                    "is_active": is_active,
                    "category": cat_id,
                    "categoryId": cat_id,
                    "categoryName": cat_name,
                    "brand": brand,
                    "packaging": packaging,
                    "description": description,
                    "imageUrl": image_url,
                    "slug": slug,
                    "isPopular": meta.get("isPopular", stock_quantity > 10 and sale_price > 50),
                    "badge": meta.get("badge", ""),
                    "inStock": stock_quantity > 0,
                    "updatedAt": firestore.SERVER_TIMESTAMP
                }
                db.collection("public_products").document(doc_id).set(public_doc, merge=True)
                logger.info(f"Canlı Güncelleme -> {doc_id}: {name} (Fiyat: {sale_price} ₺, Stok: {stock_quantity})")

    # Attach listener
    query = db.collection("products")
    col_watch = query.on_snapshot(on_snapshot)
    logger.info("Canlı dinleyici aktif! Firestore güncellemeleri anlık izleniyor.")
    return col_watch

if __name__ == "__main__":
    count = sync_all_products(user_id=6)
    print(f"\n[OK] Toplam {count} ürün Firestore public kataloğuna senkronize edildi.")
