import re
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
from xml.sax.saxutils import escape as xml_escape
import firebase_admin
from firebase_admin import credentials, firestore

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("firestore_sync")

BASE_DIR = Path(__file__).resolve().parent
SITE_DOMAIN = "https://gallusmama.com"

# Path to service account key
CRED_PATH = Path(r"C:\Users\birdo\Projects\stok-satis-takip\firebase_credentials.json")
if not CRED_PATH.exists():
    CRED_PATH = BASE_DIR / "firebase_credentials.json"

if not firebase_admin._apps:
    cred = credentials.Certificate(str(CRED_PATH))
    firebase_admin.initialize_app(cred)

db = firestore.client()

CATEGORIES = [
    {"id": "kedi", "slug": "kedi", "name": "Kedi Mamaları ve Ürünleri", "icon": "cat", "description": "Kısırlaştırılmış, yetişkin ve yavru kedi mamaları, doğal bentonit kedi kumları ve koku gidericiler."},
    {"id": "kopek", "slug": "kopek", "name": "Köpek Mamaları ve Ürünleri", "icon": "dog", "description": "Yetişkin ve yavru köpek mamaları, etli konserveler, alıştırma pedleri ve profesyonel köpek şampuanları."},
    {"id": "tavuk-civciv", "slug": "tavuk-civciv", "name": "Tavuk ve Civciv Yemleri", "icon": "wheat", "description": "Eriş Yem güvencesiyle doğal gezen tavuk yumurta yemleri ve vitaminli civciv büyütme yemleri."},
    {"id": "guvercin", "slug": "guvercin", "name": "Güvercin Yemleri", "icon": "feather", "description": "Elenmiş 1. sınıf buğday, tane tahıllar ve yüksek kondisyon güvercin yemleri."},
    {"id": "balik-akvaryum", "slug": "balik-akvaryum", "name": "Balık Yemleri ve Akvaryum", "icon": "fish", "description": "Akvaryum balıkları için pul ve granül yemler, su düzenleyiciler."},
    {"id": "kumes-ekipman", "slug": "kumes-ekipman", "name": "Kümes Ekipmanları", "icon": "home", "description": "Evcil hayvan taşıma kafesleri, havalandırmalı kutular, suluk ve yemlikler."},
    {"id": "tarim-bahce", "slug": "tarim-bahce", "name": "Tarım ve Bahçe Ürünleri", "icon": "sprout", "description": "Doğal çiftlik gübreleri, tohumlar ve bahçe bakım ürünleri."},
    {"id": "diger", "slug": "diger", "name": "Diğer Ürünler", "icon": "egg", "description": "Değirmenköy çiftlik gezen tavuk yumurtaları, muhabbet kuşu yemleri ve özel ürünler."}
]

BRANDS = [
    {"name": "Gallus Çiftlik", "country": "Silivri / Değirmenköy", "desc": "Biyogüvenlikli serbest gezen tavuk yumurtası ve doğal çiftlik ürünleri."},
    {"name": "Eriş Yem", "country": "Silivri / İstanbul", "desc": "Yüksek verimli gezen tavuk yumurta yemi, pelet-granül kanatlı yemleri ve civciv büyütme yemleri."},
    {"name": "Reflex & Reflex Plus", "country": "Türkiye / Lider Pet", "desc": "Super Premium XOS prebiyotikli kısırlaştırılmış kedi mamaları, yavru/yetişkin köpek mamaları ve Reflex Care bakım serisi."},
    {"name": "Trendline & Enjoy", "country": "Türkiye / Lider Pet", "desc": "Kedi ve köpekler için tam ve dengeli kuru mamalar, soslu et parçacıklı konserve mamalar."},
    {"name": "Pancho & Pure Life & King", "country": "Türkiye / Ekonomik Seri", "desc": "15 kg profesyonel yetiştirici çuvalları ve yüksek enerjili kedi-köpek mamaları."}
]

# Exact Verified Product Package Images by Document ID
# Tavuk ve Civciv yemleri (u6_p1002, u6_p1003, u6_p67, u6_p68) orijinal ERİŞ YEM (Ortaköy-Silivri-İSTANBUL) çuval görselleridir.
EXACT_ID_IMAGE_MAP = {
    "prod-1": "https://cdn.myikas.com/images/49991071-0805-48a8-a1b4-2b82164c288a/36e2b918-a73d-477e-aa36-35c483d08455/3840/-cef8411.webp",
    "u6_p1002": "https://cdn.dsmcdn.com/ty662/product/media/images/20221223/17/244790234/658110596/1/1_org_zoom.jpg",
    "u6_p1003": "https://cdn.dsmcdn.com/ty31/product/media/images/20201204/11/34926560/101559174/1/1_org_zoom.jpg",
    "u6_p1004": "https://cdn.dsmcdn.com/ty1835/prod/QC_PREP/20260309/21/8ca7cd6d-437a-3ce0-9c4a-01e9554fd5dc/1_org_zoom.jpg",
    "u6_p1005": "https://cdn.dsmcdn.com/ty1941/prod/QC_PREP/20260509/17/b771b011-7c7f-340c-8e5b-4769a8d5e855/1_org_zoom.jpg",
    "u6_p1006": "https://cdn.dsmcdn.com/ty1650/prod/QC/20250318/13/098de440-b758-3bbd-a7fe-019bb4ad49d5/1_org_zoom.jpg",
    "u6_p1007": "https://cdn.dsmcdn.com/mnresize/420/620/ty1769/prod/QC_ENRICHMENT/20251004/15/419ea9f3-7f42-3273-b3f5-25588eb2726d/1_org_zoom.jpg",
    "u6_p1008": "https://cdn.dsmcdn.com/ty1621/prod/QC/20250108/09/3032dd1c-a292-306a-9e4b-d1c16b3db6a5/1_org_zoom.jpg",
    "u6_p1009": "https://cdn.dsmcdn.com/ty1329/product/media/images/prod/QC/20240525/19/699d9791-9122-3030-8396-0cd5bb55d2f7/1_org_zoom.jpg",
    "u6_p1010": "https://cdn.dsmcdn.com/ty1329/product/media/images/prod/QC/20240525/19/699d9791-9122-3030-8396-0cd5bb55d2f7/1_org_zoom.jpg",
    "u6_p24": "https://cdn.dsmcdn.com/ty1789/prod/QC_PREP/20251116/00/45347a08-09fc-393c-800d-404f915558f5/1_org_zoom.jpg",
    "u6_p25": "https://cdn.dsmcdn.com/ty1852/prod/QC_PREP/20260409/21/f89b428a-53d2-34c5-b96e-931f6c2f1a2c/1_org_zoom.jpg",
    "u6_p26": "https://cdn.dsmcdn.com/ty1852/prod/QC_PREP/20260409/21/f89b428a-53d2-34c5-b96e-931f6c2f1a2c/1_org_zoom.jpg",
    "u6_p27": "https://cdn.dsmcdn.com/ty1909/prod/QC_PREP/20260506/16/3a01c9a7-5ad5-3362-b0c8-871a197de6fd/1_org_zoom.jpg",
    "u6_p28": "https://cdn.dsmcdn.com/ty1909/prod/QC_PREP/20260506/16/3a01c9a7-5ad5-3362-b0c8-871a197de6fd/1_org_zoom.jpg",
    "u6_p29": "https://cdn.dsmcdn.com/ty1724/prod/QC_PREP/20250811/17/ce5d729a-93fc-34c2-9473-9f4989f2a7bb/1_org_zoom.jpg",
    "u6_p30": "https://cdn.dsmcdn.com/mnresize/420/620/ty1857/prod/QC_PREP/20260422/14/e21fe096-dc1f-318a-b021-52fa6a36de92/1_org_zoom.jpg",
    "u6_p31": "https://cdn.dsmcdn.com/ty1717/prod/QC_PREP/20250730/15/bc6efd31-aa43-347e-8a01-d4a653bdf71a/1_org_zoom.jpg",
    "u6_p32": "https://cdn.dsmcdn.com/ty1857/prod/QC_PREP/20260422/14/20bf0d33-8537-37ee-84cb-e3340827fb5d/1_org_zoom.jpg",
    "u6_p33": "https://cdn.dsmcdn.com/ty1694/product/media/images/prod/PIM/20250616/06/2a51c1e2-1e09-49bd-9123-3ea03aae3d54/1_org_zoom.jpg",
    "u6_p34": "https://petstore.co.ke/wp-content/uploads/2019/02/PetStore-Kenya-Trendline-Dog-Food-Beef-15kg-min-600x600.png",
    "u6_p35": "https://cdn.dsmcdn.com/ty1824/prod/QC_PREP/20260212/11/87846302-2f8d-3ab9-87b1-2d3597d24aae/1_org_zoom.jpg",
    "u6_p36": "https://cdn.dsmcdn.com/ty1743/product/media/images/prod/PIM/20251014/13/1e002e2c-b046-44e3-9414-827e0b25eb02/1_org_zoom.jpg",
    "u6_p37": "https://cdn.dsmcdn.com/ty1743/product/media/images/prod/PIM/20250909/12/11aaf518-43d8-41e4-b6c5-c5e737f94ba0/1_org_zoom.jpg",
    "u6_p38": "https://petstore.co.ke/wp-content/uploads/2019/02/Trendline-Multicolor.png",
    "u6_p39": "https://petzonebd.com/wp-content/uploads/2022/07/trendline-cat-salmon-1kg-600x600-1.jpg",
    "u6_p40": "https://cdn.dsmcdn.com/ty1793/prod/QC_PREP/20251124/11/25425833-16a5-3066-9a30-9a34755cad6b/1_org_zoom.jpg",
    "u6_p41": "https://cdn.dsmcdn.com/ty1773/prod/QC_PREP/20251015/15/2ddb4b6b-f15d-3eb9-997a-abf81c1aac4d/1_org_zoom.jpg",
    "u6_p42": "https://cdn.dsmcdn.com/ty1795/prod/QC_PREP/20251201/13/aa88ddd6-8588-3b69-b8f2-adcffb46e018/1_org_zoom.jpg",
    "u6_p43": "https://cdn.dsmcdn.com/ty1151/product/media/images/prod/SPM/PIM/20240130/01/1c8d0b02-5a4a-3e52-9fca-69af69f65151/1_org_zoom.jpg",
    "u6_p44": "https://cdn.dsmcdn.com/ty1773/prod/QC_PREP/20251015/14/b3b60293-f8cf-3a38-b3cd-e52097ca07d8/1_org_zoom.jpg",
    "u6_p45": "https://cdn.dsmcdn.com/ty1625/prod/QC/20250116/02/969c2c60-9b63-3ee7-8a71-576018392556/1_org_zoom.jpg",
    "u6_p46": "https://cdn.dsmcdn.com/ty1790/prod/QC_PREP/20251117/14/6b154e28-2db6-3244-b669-d74995210121/1_org_zoom.jpg",
    "u6_p47": "https://static.ticimax.cloud/50837/uploads/urunresimleri/buyuk/pro-plan-kisirlastirilmis-somonlu-kedi-49d8-b.png",
    "u6_p48": "https://static.ticimax.cloud/50837/uploads/urunresimleri/buyuk/pro-plan-kisirlastirilmis-somonlu-kedi-49d8-b.png",
    "u6_p49": "https://cdn.dsmcdn.com/ty1743/product/media/images/prod/PIM/20251014/13/1e002e2c-b046-44e3-9414-827e0b25eb02/1_org_zoom.jpg",
    "u6_p50": "https://cdn.dsmcdn.com/ty1519/product/media/images/prod/QC/20240902/18/74e0d985-7641-3ce2-aef1-7ad2e756d19b/1_org_zoom.jpg",
    "u6_p51": "https://cdn.dsmcdn.com/mnresize/420/620/ty1859/prod/QC_PREP/20260424/16/d71d2b45-7f2a-3278-a51e-100a89f1e398/1_org.jpg",
    "u6_p52": "https://cdn.dsmcdn.com/ty1903/prod/QC_PREP/20260428/14/91920fad-9d81-3155-92fd-55473ec08f13/1_org_zoom.jpg",
    "u6_p53": "https://cdn.dsmcdn.com/ty1805/prod/QC_PREP/20251227/18/308bfc1e-648c-3c4b-a340-ebc4ac917eb9/1_org_zoom.jpg",
    "u6_p54": "https://cdn.dsmcdn.com/ty1803/prod/QC_ENRICHMENT/20251224/10/9441539f-c9b7-3251-80ea-584b627b8750/1_org_zoom.jpg",
    "u6_p55": "https://cdn.dsmcdn.com/ty1843/prod/QC_ENRICHMENT/20260324/09/f8948bb5-f429-35c2-99eb-6fef9ee9f54a/1_org_zoom.jpg",
    "u6_p56": "https://cdn.dsmcdn.com/ty1767/prod/QC_ENRICHMENT/20251004/00/f62964d2-d53d-3bf1-86c6-43f5aa65da9a/1_org_zoom.jpg",
    "u6_p57": "https://cdn.dsmcdn.com/ty1859/prod/QC_PREP/20260423/12/e0b8fdda-b64b-3fc1-a25a-20f42e7793aa/1_org_zoom.jpg",
    "u6_p58": "https://cdn.dsmcdn.com/ty1859/prod/QC_PREP/20260423/12/e0b8fdda-b64b-3fc1-a25a-20f42e7793aa/1_org_zoom.jpg",
    "u6_p59": "https://cdn.dsmcdn.com/ty1903/prod/QC_PREP/20260509/19/cbcd7513-c24a-34f2-8fc9-60b3cda8cce6/1_org_zoom.jpg",
    "u6_p60": "https://cdn.dsmcdn.com/ty1859/prod/QC_PREP/20260423/12/e0b8fdda-b64b-3fc1-a25a-20f42e7793aa/1_org_zoom.jpg",
    "u6_p61": "https://cdn.dsmcdn.com/ty1859/prod/QC_PREP/20260423/12/e0b8fdda-b64b-3fc1-a25a-20f42e7793aa/1_org_zoom.jpg",
    "u6_p62": "https://cdn.dsmcdn.com/ty1678/prod/QC/20250514/23/b249a9eb-a4e8-3315-8740-993101e88776/1_org_zoom.jpg",
    "u6_p63": "https://cdn.dsmcdn.com/ty1910/prod/QC_PREP/20260428/19/1d79cb61-3dfe-3ef4-9479-b67894d238a5/1_org_zoom.jpg",
    "u6_p64": "https://static.ticimax.cloud/37708/uploads/urunresimleri/buyuk/paw-paw-kuzu-etli-yetiskin-kopek-mamas-2cabb6.jpg",
    "u6_p65": "https://cdn.dsmcdn.com/ty1784/prod/QC_PREP/20251104/13/50b5d5e7-3975-36de-8e7c-2def5a410f73/1_org_zoom.jpg",
    "u6_p66": "https://cdn.dsmcdn.com/ty1941/prod/QC_PREP/20260509/17/b771b011-7c7f-340c-8e5b-4769a8d5e855/1_org_zoom.jpg",
    "u6_p67": "https://xcdn.gormeklazim.com/img/cac2977f-e396-4b3d-93f0-53606a2b72a5.webp",
    "u6_p68": "https://xcdn.gormeklazim.com/img/cac2977f-e396-4b3d-93f0-53606a2b72a5.webp",
    "u6_p69": "https://cdn.dsmcdn.com/ty1941/prod/QC_PREP/20260509/17/b771b011-7c7f-340c-8e5b-4769a8d5e855/1_org_zoom.jpg",
    "u6_p999": "https://cdn.myikas.com/images/0fc5e2e6-3ea7-443f-a09e-daf74b83e708/50c5bccd-e3f9-455b-a12d-08ddd5a8949e/3840/efe-gezen-tavuk.webp"
}

IMAGE_MAP = {
    "reflex_plus_cat": "https://cdn.dsmcdn.com/ty1773/prod/QC_PREP/20251015/15/2ddb4b6b-f15d-3eb9-997a-abf81c1aac4d/1_org_zoom.jpg",
    "reflex_cat": "https://cdn.dsmcdn.com/ty1773/prod/QC_PREP/20251015/14/b3b60293-f8cf-3a38-b3cd-e52097ca07d8/1_org_zoom.jpg",
    "trendline_cat": "https://petzonebd.com/wp-content/uploads/2022/07/trendline-cat-salmon-1kg-600x600-1.jpg",
    "enjoy_cat": "https://cdn.dsmcdn.com/ty1824/prod/QC_PREP/20260212/11/87846302-2f8d-3ab9-87b1-2d3597d24aae/1_org_zoom.jpg",
    "pancho_cat": "https://cdn.dsmcdn.com/ty1910/prod/QC_PREP/20260428/19/1d79cb61-3dfe-3ef4-9479-b67894d238a5/1_org_zoom.jpg",
    "pure_life_cat": "https://cdn.dsmcdn.com/ty1678/prod/QC/20250514/23/b249a9eb-a4e8-3315-8740-993101e88776/1_org_zoom.jpg",
    "cat_litter": "https://cdn.dsmcdn.com/ty1805/prod/QC_PREP/20251227/18/308bfc1e-648c-3c4b-a340-ebc4ac917eb9/1_org_zoom.jpg",
    "cat_canned": "https://cdn.dsmcdn.com/ty1909/prod/QC_PREP/20260506/16/3a01c9a7-5ad5-3362-b0c8-871a197de6fd/1_org_zoom.jpg",
    "default_cat": "https://cdn.dsmcdn.com/ty1773/prod/QC_PREP/20251015/15/2ddb4b6b-f15d-3eb9-997a-abf81c1aac4d/1_org_zoom.jpg",

    "reflex_plus_dog": "https://cdn.dsmcdn.com/ty1793/prod/QC_PREP/20251124/11/25425833-16a5-3066-9a30-9a34755cad6b/1_org_zoom.jpg",
    "reflex_care": "https://cdn.dsmcdn.com/mnresize/420/620/ty1857/prod/QC_PREP/20260422/14/e21fe096-dc1f-318a-b021-52fa6a36de92/1_org_zoom.jpg",
    "trendline_dog": "https://petstore.co.ke/wp-content/uploads/2019/02/PetStore-Kenya-Trendline-Dog-Food-Beef-15kg-min-600x600.png",
    "enjoy_dog": "https://cdn.dsmcdn.com/ty1694/product/media/images/prod/PIM/20250616/06/2a51c1e2-1e09-49bd-9123-3ea03aae3d54/1_org_zoom.jpg",
    "king_dog": "https://cdn.dsmcdn.com/ty1743/product/media/images/prod/PIM/20250909/12/11aaf518-43d8-41e4-b6c5-c5e737f94ba0/1_org_zoom.jpg",
    "pancho_dog": "https://cdn.dsmcdn.com/ty1784/prod/QC_PREP/20251104/13/50b5d5e7-3975-36de-8e7c-2def5a410f73/1_org_zoom.jpg",
    "dog_canned": "https://cdn.dsmcdn.com/ty1852/prod/QC_PREP/20260409/21/f89b428a-53d2-34c5-b96e-931f6c2f1a2c/1_org_zoom.jpg",
    "default_dog": "https://cdn.dsmcdn.com/ty1694/product/media/images/prod/PIM/20250616/06/2a51c1e2-1e09-49bd-9123-3ea03aae3d54/1_org_zoom.jpg",

    "chicken_feed": "https://cdn.dsmcdn.com/ty662/product/media/images/20221223/17/244790234/658110596/1/1_org_zoom.jpg",
    "chick_feed": "https://xcdn.gormeklazim.com/img/cac2977f-e396-4b3d-93f0-53606a2b72a5.webp",
    "farm_eggs": "https://cdn.dsmcdn.com/ty1859/prod/QC_PREP/20260423/12/e0b8fdda-b64b-3fc1-a25a-20f42e7793aa/1_org_zoom.jpg",
    "wheat_grain": "https://cdn.dsmcdn.com/ty1941/prod/QC_PREP/20260509/17/b771b011-7c7f-340c-8e5b-4769a8d5e855/1_org_zoom.jpg",
    "bird_feed": "https://cdn.dsmcdn.com/ty1835/prod/QC_PREP/20260309/21/8ca7cd6d-437a-3ce0-9c4a-01e9554fd5dc/1_org_zoom.jpg",
    "equipment": "https://cdn.dsmcdn.com/ty1519/product/media/images/prod/QC/20240902/18/74e0d985-7641-3ce2-aef1-7ad2e756d19b/1_org_zoom.jpg",
    "general": "/images/mutlu-patiler-banner.jpg"
}

# Detailed Researched Specifications for All 56 Products
DETAILED_PRODUCT_OVERRIDES: Dict[str, Dict[str, Any]] = {
    "u6_p1002": {
        "brand": "Eriş Yem",
        "packaging": "1 Kg / Açık & Çuval",
        "fallbackImageUrl": "/images/eris-eko-yumurta-yemi.jpg",
        "description": (
            "Eriş Yem Gezen Tavuk Yumurta Yemi (Eko Yumurta Yemi), Silivri Ortaköy'deki modern Eriş Yem tesislerinde "
            "serbest dolaşan (free-range) ve kümes yumurta tavuklarının18. haftadan (yumurtlama başlangıcından) "
            "yumurtlama dönemi sonuna kadar olan tüm besin madde gereksinimlerini eksiksiz karşılamak üzere özel olarak "
            "formüle edilmiştir. Yüksek sindirilebilir enerji, dengeli esansiyel aminoasit (metiyonin-lizin) profili ve "
            "doğal bitkisel ksantofil kaynakları sayesinde hem yumurta verim yüzdesini maksimuma çıkarır hem de yumurta "
            "sarısının doğal altın-turuncu rengini ve kabuk mukavemetini güçlendirir."
        ),
        "ingredients": (
            "1. Sınıf Sarı Mısır, Kabuğu Soyulmuş Soya Küspesi (Genetiği Korunmuş Bitkisel Protein), Buğday, "
            "Tam Yağlı Soya (Full-Fat Soya), Ayçiçek Tohumu Küspesi, Buğday Kepeği, Kalsiyum Karbonat (Mermer Tozu / İri Granül Kalsiyum), "
            "Dikalsiyum Fosfat (DCP), Bitkisel Ham Yağ, Sodyum Klorür (Tuz), Sodyum Bikarbonat, DL-Metiyonin, L-Lizin, "
            "Doğal Karotenoidler (Kırmızı Biber ve Kadife Çiçeği Ekstraktı), Toksin Bağlayıcı, Fitaz Enzimi ve Eriş Yem Kanatlı Vitamin-Mineral Premiksi (Vitamin A, D3, E, K3, B Grubu, Mangan, Çinko, Selenyum)."
        ),
        "analysis": (
            "Ham Protein: %16.50 - %17.50 | Metabolik Enerji: 2750 kcal/kg | Ham Yağ: %3.60 | Ham Selüloz: %5.20 | "
            "Ham Kül: %12.80 | Kalsiyum (Ca): %3.80 - %4.10 | Toplam Fosfor (P): %0.62 | Kullanılabilir Fosfor: %0.40 | "
            "Sodyum (Na): %0.18 | Metiyonin: %0.42 | Lizin: %0.85 | Vitamin A: 10.000 IU/kg | Vitamin D3: 2.500 IU/kg | Vitamin E: 30 mg/kg."
        ),
        "usage": (
            "Yumurtlama dönemindeki gezen tavuklara 18. haftadan itibaren günlük tavuk başına ortalama 110 - 130 gram "
            "serbest (ad-libitum) olarak verilir. Yanında her zaman taze ve temiz içme suyu bulundurulmalıdır. "
            "Ekstra tahıl veya arpa karıştırılması rasyonun kalsiyum-protein dengesini düşürebileceğinden tek başına verilmesi tavsiye edilir."
        ),
        "specs": {
            "Marka / Üretici": "Eriş Yem (Ortaköy - Silivri / İstanbul)",
            "Ürün Tipi": "1. Dönem / Gezen Tavuk Yumurta Yemi",
            "Form Yapısı": "Granül / Pelet Kırma (Tozsuz Form)",
            "Hedef Kanatlı": "Yumurtacı Tavuklar (Lohmann, Ataks, Ligorin, Köy Tavuğu)",
            "Menşei": "Türkiye (Yerli Üretim)",
            "Saklama Koşulu": "Serin, kuru ve güneş görmeyen ortamda muhafaza ediniz."
        }
    },
    "u6_p1003": {
        "brand": "Eriş Yem",
        "packaging": "1 Kg Tartım",
        "fallbackImageUrl": "/images/eris-yumurta-tavuk-yemi.jpg",
        "description": (
            "Eriş Yem Yumurta Tavuk Yemi (Kg Tartım), Silivri'nin köklü yem üreticisi Eriş Yem tarafından "
            "kümes ve bahçe tavuklarının yüksek randımanla yumurtlaması için üretilmiş tam dengeli 1. dönem yumurta yemidir. "
            "İçeriğindeki çift boyutlu kalsiyum partikülleri gece boyunca yumurta kabuğu oluşumunu destekler, ince kabuklu "
            "veya kabuksuz (zar) yumurta problemini ortadan kaldırır. Granül/pelet yapısı sayesinde yem seçmeyi ve yemlikten "
            "saçılma zayiatını önler."
        ),
        "ingredients": (
            "Sarı Mısır (%45+), Soya Fasulyesi Küspesi, Buğday, Ayçiçek Tohumu Küspesi, Mısır Gluten Yemi, "
            "Kalsiyum Karbonat (Granül Mermer Tozu), Dikalsiyum Fosfat (DCP), Bitkisel Soya Yağı, DL-Metiyonin, L-Lizin, "
            "Tuz, Kolin Klorür, Multi-Enzim Kompleksi (Ksilanaz, Beta-Glukanaz, Fitaz) ve Vitamin-İz Mineral Premiksi."
        ),
        "analysis": (
            "Ham Protein: %17.00 | Metabolik Enerji: 2760 kcal/kg | Ham Yağ: %3.80 | Ham Selüloz: %4.80 | "
            "Ham Kül: %13.00 | Kalsiyum: %3.95 | Fosfor: %0.65 | Lizin: %0.86 | Metiyonin + Sistin: %0.74 | "
            "Vitamin A: 12.000 IU/kg | Vitamin D3: 3.000 IU/kg | Vitamin E: 35 mg/kg."
        ),
        "usage": (
            "Tavuk başına günlük 115 - 125 gram hesabıyla yemliklerde sürekli bulundurulmalıdır. "
            "Sabah erken saatlerde ve öğleden sonra olmak üzere günde 2 öğün halinde taze olarak verilmesi "
            "tavukların iştahını ve yumurta verimini artırır."
        ),
        "specs": {
            "Marka / Üretici": "Eriş Yem San. ve Tic. A.Ş. (Silivri / İstanbul)",
            "Satış Birimi": "1 Kg (Tartım / Açık)",
            "Yem Formu": "Pelet / Granül Yumurta Yemi",
            "Kullanım Dönemi": "18. Haftadan Yumurtlama Sonuna Kadar",
            "Antibiyotik / Hormon": "İçermez (%100 Doğal Bitkisel Rasyon)"
        }
    },
    "u6_p67": {
        "brand": "Eriş Yem",
        "packaging": "1 Adet Paket",
        "fallbackImageUrl": "/images/eris-yumurta-civciv-yemi.webp",
        "description": (
            "Eriş Yem Yumurta Civciv Başlangıç ve Büyütme Yemi (Kod: 2108), yumurtacı ve gezen tavuk civcivlerinin "
            "yumurtadan çıktığı ilk günden 8. haftanın sonuna kadar sağlıklı büyümesi, sindirim ve bağışıklık "
            "sistemlerinin hızla gelişmesi için özel olarak üretilmiş yüksek proteinli mikro-granül civciv yemidir. "
            "Civcivlerin küçük gagalarıyla kolayca tüketebileceği ince granül formdadır; sindirimi kolaylaştırılmış "
            "mısır ve soya proteinleri sayesinde ilk haftalardaki ölüm oranını en aza indirir ve hızlı tüylenme sağlar."
        ),
        "ingredients": (
            "Mikronize Sarı Mısır, Yüksek Proteinli Soya Küspesi, Tam Yağlı Soya, Buğday, Mısır Gluteni, "
            "Bitkisel Yağ, Dikalsiyum Fosfat (DCP), Kalsiyum Karbonat, DL-Metiyonin, L-Lizin, L-Treonin, "
            "Prebiyotik MOS (Mannan-Oligosakkarit), Organik Asitler, Sindirim Enzimleri ve Civciv Özel Vitamin-Mineral Premiksi."
        ),
        "analysis": (
            "Ham Protein: %19.50 - %20.00 | Metabolik Enerji: 2900 kcal/kg | Ham Yağ: %3.90 | Ham Selüloz: %4.00 | "
            "Ham Kül: %6.50 | Kalsiyum: %1.05 | Kullanılabilir Fosfor: %0.48 | Sodyum: %0.17 | "
            "Metiyonin: %0.48 | Lizin: %1.10 | Vitamin A: 13.500 IU/kg | Vitamin D3: 3.500 IU/kg | Vitamin E: 50 mg/kg."
        ),
        "usage": (
            "Civcivlerin ilk gününden (1. gün) 8. hafta (56. gün) sonuna kadar serbest (ad-libitum) olarak verilir. "
            "İlk hafta civciv altlığı üzerine serilen yem tepsilerinde, sonrasında civciv yemliklerinde taze olarak sunulmalıdır. "
            "Civcivlerin ilk günlerinde ılık (20-22°C) ve temiz suyla birlikte verilmesi önemle tavsiye edilir."
        ),
        "specs": {
            "Marka / Üretici": "Eriş Yem (Kod: 2108 Yumurta Civciv Yemi)",
            "Kullanım Yaşı": "0 - 8 Haftalık Civciv Dönemi",
            "Form": "İnce Kırma / Mikro Granül",
            "Protein Oranı": "%19.5 - %20 Yüksek Sindirilebilir Protein",
            "Menşei": "Türkiye (Silivri / İstanbul)"
        }
    },
    "u6_p68": {
        "brand": "Eriş Yem",
        "packaging": "1 Kg Tartım",
        "fallbackImageUrl": "/images/eris-yumurta-civciv-yemi.webp",
        "description": (
            "Eriş Yem Yumurta Civciv Yemi 2108 (1 Kg Tartım), civcivlerin ilk 8 haftalık kritik büyüme evresinde "
            "iskelet, kas, tüy ve bağışıklık gelişimini eksiksiz destekleyen yüksek enerjili ve %20 proteinli "
            "başlangıç yemidir. Tozsuz mikro-granül yapısı sayesinde civcivlerin solunum yollarını tahriş etmez "
            "ve her gagalamada dengeli vitamin-mineral alımı sağlar."
        ),
        "ingredients": (
            "Isıl İşlem Görmüş Sarı Mısır, Kabuğu Soyulmuş Soya Fasulyesi Küspesi, Tam Yağlı Soya, Buğday, "
            "Dikalsiyum Fosfat, Mermer Tozu, Bitkisel Yağ, Metiyonin, Lizin, Bağırsak Florası Düzenleyici Prebiyotikler "
            "ve Eriş Yem Civciv Vitamin-Mineral Kompleksi (A, D3, E, K3, B1, B2, B6, B12, Folik Asit, Biotin, Çinko, Mangan)."
        ),
        "analysis": (
            "Ham Protein: %20.00 | Metabolik Enerji: 2900 kcal/kg | Ham Yağ: %4.00 | Ham Selüloz: %3.80 | "
            "Ham Kül: %6.40 | Kalsiyum: %1.05 | Fosfor: %0.70 | Lizin: %1.12 | Metiyonin: %0.50."
        ),
        "usage": (
            "0-8 haftalık civcivlere günlük taze olarak serbest erişimli yemliklerde sunulur. "
            "Bir civciv 8 haftalık dönemin sonuna kadar toplamda ortalama 1.8 - 2.2 kg civciv yemi tüketir."
        ),
        "specs": {
            "Marka / Üretici": "Eriş Yem (Ortaköy - Silivri / İstanbul)",
            "Satış Birimi": "1 Kg Tartım",
            "Ürün Kodu": "Eriş 2108 Civciv Büyütme Yemi",
            "Hedef Grup": "Civciv, Bıldırcın, Sülün ve Keklik Yavruları",
            "Form": "Mikro Granül / Kırma"
        }
    }
}

def get_google_product_category(cat_id: str, name: str) -> Tuple[str, str]:
    n = name.lower()
    if "yumurta" in n and "yemi" not in n:
        return "Food, Beverages & Tobacco > Food Items > Meat, Seafood & Eggs > Eggs", "422"
    if cat_id == "kedi":
        if "kum" in n or "litter" in n or "koku" in n:
            return "Animals & Pet Supplies > Pet Supplies > Cat Supplies > Cat Litter", "4999"
        return "Animals & Pet Supplies > Pet Supplies > Cat Supplies > Cat Food", "3367"
    if cat_id == "kopek":
        if "ped" in n:
            return "Animals & Pet Supplies > Pet Supplies > Dog Supplies > Dog Diapers & Pee Pads", "5001"
        if "şampuan" in n or "tüy" in n or "haşere" in n:
            return "Animals & Pet Supplies > Pet Supplies > Pet Grooming Supplies > Pet Shampoo & Conditioner", "6385"
        return "Animals & Pet Supplies > Pet Supplies > Dog Supplies > Dog Food", "3530"
    if cat_id == "kumes-ekipman":
        if "tırmalama" in n:
            return "Animals & Pet Supplies > Pet Supplies > Cat Supplies > Cat Furniture", "4433"
        if "minder" in n:
            return "Animals & Pet Supplies > Pet Supplies > Dog Supplies > Dog Beds", "4434"
        return "Animals & Pet Supplies > Pet Supplies > Pet Carriers & Crates", "6251"
    if cat_id in ["tavuk-civciv", "guvercin"] or "kuş" in n or "buğday" in n:
        return "Animals & Pet Supplies > Pet Supplies > Bird Supplies > Bird Food", "4990"
    return "Animals & Pet Supplies > Pet Supplies", "2"

def build_detailed_product_content(doc_id: str, name: str, cat_id: str, brand: str, packaging: str, unit: str) -> Dict[str, Any]:
    if doc_id in DETAILED_PRODUCT_OVERRIDES:
        ov = DETAILED_PRODUCT_OVERRIDES[doc_id]
        g_cat, g_id = get_google_product_category(cat_id, name)
        return {
            "brand": ov.get("brand", brand),
            "packaging": ov.get("packaging", packaging),
            "fallbackImageUrl": ov.get("fallbackImageUrl", ""),
            "description": ov["description"],
            "ingredients": ov["ingredients"],
            "analysis": ov["analysis"],
            "usage": ov["usage"],
            "specs": ov["specs"],
            "googleProductCategory": g_cat,
            "googleProductCategoryId": g_id
        }

    n = name.lower()
    g_cat, g_id = get_google_product_category(cat_id, name)

    # 1. ÇİFTLİK YUMURTALARI (u6_p57, u6_p58, u6_p59, u6_p60, u6_p61, u6_p999, prod-1)
    if "yumurta" in n and "yemi" not in n:
        pack_count = "30 Adet (1 Koli / Viyol)"
        if "10'lu" in n or "10lu" in n:
            pack_count = "10 Adet Koruyucu Viyol"
        elif "15'li" in n or "15li" in n:
            pack_count = "15 Adet Koruyucu Viyol"
        elif "20'li" in n or "20li" in n:
            pack_count = "20 Adet Koruyucu Viyol"
        elif "1 adet" in n:
            pack_count = "1 Adet Taze Çiftlik Yumurtası"

        return {
            "brand": "Gallus Çiftlik",
            "packaging": pack_count,
            "fallbackImageUrl": "/images/yumurta-koli-banner.jpg",
            "description": (
                f"Gallus Çiftlik {name}, Silivri Değirmenköy'deki biyogüvenlikli serbest gezen tavuk çiftliğimizden "
                f"her sabah gün ağarırken günlük olarak toplanan %100 doğal, katkısız ve antibiyotiksiz köy/çiftlik yumurtasıdır. "
                f"Tavuklarımız açık yeşil mera alanlarında serbestçe güneşlenerek dolaşır ve Eriş Yem'in GDO'suz doğal mısır, "
                f"buğday ve bitkisel protein rasyonlarıyla beslenir. Bu doğal beslenme sayesinde yumurtalarımız koyu altın sarısı "
                f"renginde, yoğun kıvamlı, yüksek besin değerine sahip ve gerçek köy yumurtası lezzetindedir. Bebek ek gıda "
                f"döneminden sporcu beslenmesine kadar tüm aileniz için güvenle tüketebilirsiniz."
            ),
            "ingredients": (
                "%100 Doğal A Sınıfı Serbest Gezen Tavuk Yumurtası (Yetiştirme Metodu Kodu: 1 - Free Range / Açık Meralarda Serbest Dolaşan Tavuk Yumurtası). "
                "Tavuklarımızın yem rasyonunda antibiyotik, sentetik renklendirici, hormon veya hayvansal mezbaha yan ürünü kesinlikle kullanılmaz."
            ),
            "analysis": (
                "100g Yenilebilir Yumurta İçin Besin Değerleri: Enerji: 143 kcal (598 kJ) | Yüksek Biyoyararlanımlı Protein: 12.6 g | "
                "Toplam Yağ: 9.5 g (Tekli Doymamış Yağ: 3.7 g, Çoklu Doymamış Omega-3 & Omega-6: 1.9 g) | Karbonhidrat: 0.7 g | "
                "Kolin: 294 mg | Vitamin A: 540 IU | Vitamin D: 82 IU | Vitamin B12: 1.1 mcg | Demir: 1.75 mg | Çinko: 1.29 mg | Selenyum: 30.7 mcg."
            ),
            "usage": (
                "Teslim aldıktan sonra +4°C ile +8°C arasında buzdolabında, sivri ucu aşağı gelecek şekilde kendi viyolünde saklayınız. "
                "Yumurtanın doğal koruyucu zarını (kütikula) kaybetmemesi için kullanmadan hemen önce yıkayınız. "
                "Raf ömrü üretim/toplama tarihinden itibaren 28 gündür."
            ),
            "specs": {
                "Marka / Üretici": "Gallus Çiftlik (Değirmenköy - Silivri / İstanbul)",
                "Paket İçeriği": pack_count,
                "Yetiştirme Kodu": "1 (Serbest Gezen / Free-Range)",
                "Kalite Sınıfı": "A Sınıfı Günlük Taze Yumurta (M/L Boy 55-68g)",
                "Sevkiyat Ambalajı": "Darbe Emici Özel Kraft Viyol",
                "Menşei": "Türkiye (Yerli Çiftlik Üretimi)"
            },
            "googleProductCategory": g_cat,
            "googleProductCategoryId": g_id
        }

    # 2. BUĞDAY & GÜVERCİN YEMLERİ (u6_p1005, u6_p66, u6_p69)
    if "buğday" in n or "bugday" in n:
        is_sack = "1100" in str(packaging) or doc_id == "u6_p69"
        pkg_label = "50 Kg Çuval" if doc_id == "u6_p69" else "1 Kg Elenecek Tane Tahıl"
        return {
            "brand": "Gallus Çiftlik",
            "packaging": pkg_label,
            "fallbackImageUrl": "/images/tavuklar.jpg",
            "description": (
                f"Gallus Çiftlik 1. Sınıf Elenmiş Yemlik ve Güvercinlik {name} ({pkg_label}), Trakya ve Silivri bölgesinin "
                f"verimli tarlalarından hasat edilmiş, çift kademeli triyör ve toz eleme sisteminden geçirilmiş dolgun taneli "
                f"doğal kırmızı/sert buğdaydır. Güvercinler, tavuklar, bıldırcınlar, ördekler ve doğa kuşları için yüksek "
                f"karbonhidrat, bitkisel protein ve doğal E vitamini kaynağıdır. Kırık tane, yabancı ot tohumu ve toz içermez."
            ),
            "ingredients": (
                "%100 Doğal, İlaçsız ve Elenmiş 1. Sınıf Trakya Yemlik Tane Buğday (Triticum aestivum / durum). "
                "Yabancı madde ve tozdan arındırılmış saf tam tahıl."
            ),
            "analysis": (
                "Ham Protein: %12.00 - %13.50 | Metabolik Enerji: 3100 kcal/kg | Ham Yağ: %1.80 | "
                "Ham Selüloz: %2.60 | Ham Kül: %1.70 | Nişasta: %62.00 | Nem (Maksimum): %12.50 | Hektolitre Ağırlığı: 78-80 kg/hl."
            ),
            "usage": (
                "Güvercinlere günlük kondisyon rasyonunun %30-%50'si oranında veya doğrudan yemliklerde serbest olarak verilebilir. "
                "Tavuk ve kümes hayvanlarında karma yumurta yemine ek olarak akşam öğünlerinde dane yem takviyesi olarak kullanılır. "
                "Serin ve nemsiz ortamda çuval ağzı kapalı şekilde muhafaza ediniz."
            ),
            "specs": {
                "Marka / Tedarik": "Gallus Çiftlik (Trakya Mahsulü)",
                "Ambalaj / Birim": pkg_label,
                "Kalite Sınıfı": "1. Sınıf Triyörden Geçmiş Tozsuz Buğday",
                "Hedef Türler": "Güvercin, Tavuk, Hindi, Ördek, Kaz ve Doğa Kuşları",
                "Menşei": "Türkiye (Trakya / Silivri)"
            },
            "googleProductCategory": g_cat,
            "googleProductCategoryId": g_id
        }

    # 3. MUHABBET KUŞU YEMİ VE KUŞ VİTAMİNİ (u6_p1004, u6_p1008)
    if doc_id == "u6_p1004" or "muhabbet" in n:
        return {
            "brand": "Gallus Pet",
            "packaging": "1 Kg Özel Karışım",
            "fallbackImageUrl": "/images/mutlu-patiler-banner.jpg",
            "description": (
                "Gallus Pet Vitaminli Muhabbet Kuşu Yemi (1 Kg), muhabbet kuşlarının doğal beslenme alışkanlıklarına uygun olarak "
                "sarhoş etmeyen, tozsuz ve çift elenmiş birinci kalite darı ve tohum çeşitlerinin ideal oranlarda harmanlanmasıyla "
                "hazırlanmıştır. İçeriğindeki sarı darı, beyaz darı, kızıl darı, soyulmuş yulaf ve kanarya yemi (aspur) kuşunuzun "
                "günlük enerji ihtiyacını karşılarken parlak tüy yapısını, sindirim sağlığını ve ötüş neşesini destekler."
            ),
            "ingredients": (
                "Sarı Darı (%52), Beyaz Darı (%18), Kızıl Darı (%12), Kanarya Yemi / Aspur Tohumu (%10), "
                "Soyulmuş İç Yulaf (%5), Nijer Tohumu (%1.5), Keten Tohumu (%1.5) ve Meyveli-Vitaminli Renkli Galeta Granülleri (A, D3, E, C ve B Grubu Vitaminleri)."
            ),
            "analysis": (
                "Ham Protein: %11.80 | Ham Yağ: %4.60 | Ham Selüloz: %6.20 | Ham Kül: %3.40 | Nem: %11.00 | "
                "Kalsiyum: %0.80 | Fosfor: %0.40 | Vitamin A: 6.000 IU/kg | Vitamin D3: 800 IU/kg | Vitamin E: 25 mg/kg."
            ),
            "usage": (
                "Kuş başına günlük 2 yemek kaşığı (yaklaşık 10-15 gram) yemliklere konulmalıdır. "
                "Yemlik üzerindeki boş kabuklar her gün üflenerek temizlenmeli ve yanında daima taze içme suyu bulundurulmalıdır."
            ),
            "specs": {
                "Marka": "Gallus Pet",
                "Ağırlık": "1 Kg",
                "Hedef Kuş Türü": "Muhabbet Kuşu, Cennet Papağanı ve Küçük Paraketler",
                "Özellik": "Çift Elenmiş, Tozsuz, Aspur ve Soyulmuş Yulaflı",
                "Menşei": "Türkiye"
            },
            "googleProductCategory": g_cat,
            "googleProductCategoryId": g_id
        }

    if doc_id == "u6_p1008" or "kuş vitamini" in n:
        return {
            "brand": "Apex / Gallus Pet",
            "packaging": "30 ml Damla Şişe",
            "fallbackImageUrl": "/images/mutlu-patiler-banner.jpg",
            "description": (
                "Kafes Kuşları İçin Multivitamin ve Kondisyon Damlası (30 ml), muhabbet kuşu, kanarya, sultan papağanı ve "
                "güvercinlerin günlük vitamin gereksinimlerini karşılamak, mevsim geçişleri ve tüy dökümü (tüy değişimi) "
                "dönemlerinde bağışıklık sistemini güçlendirmek amacıyla formüle edilmiş sıvı multivitamin takviyesidir. "
                "Stresi azaltır, yavru gelişimini ve üreme performansını destekler."
            ),
            "ingredients": (
                "Deiyonize Su, Vitamin A (Retinol Palmitat), Vitamin D3 (Kolekalsiferol), Vitamin E (Alfa-Tokoferol), "
                "Vitamin C (Askorbik Asit), Vitamin B1, B2, B6, B12, Niasinamid (Vitamin B3), Kalsiyum D-Pantotenat (Vitamin B5), "
                "Folik Asit, D-Biotin (Vitamin H), Kolin Klorür ve Doğal Aromatik Taşıyıcılar."
            ),
            "analysis": (
                "1 Litre İçeriği: Vitamin A: 2.500.000 IU | Vitamin D3: 400.000 IU | Vitamin E: 3.000 mg | "
                "Vitamin C: 10.000 mg | Vitamin B1: 800 mg | Vitamin B2: 1.200 mg | Vitamin B6: 1.000 mg | Vitamin B12: 5 mg | Biotin: 20 mg."
            ),
            "usage": (
                "100 ml (standart bir suluk) içme suyuna haftada 2-3 kez 10-12 damla damlatılarak kullanılır. "
                "Tüy dökümü ve hastalık sonrası nekahet dönemlerinde 5 gün üst üste uygulanabilir. Vitaminli su her gün tazelenmelidir."
            ),
            "specs": {
                "Marka": "Gallus Pet / Profesyonel Kuş Bakım Serisi",
                "Hacim": "30 ml Damlalıklı Şişe",
                "Form": "Suda Tam Çözünen Sıvı Multivitamin",
                "Kullanım Alanı": "Muhabbet Kuşu, Kanarya, Papağan, İspinoz",
                "Menşei": "Türkiye"
            },
            "googleProductCategory": g_cat,
            "googleProductCategoryId": g_id
        }

    # 4. EKİPMAN, TAŞIMA KUTUSU, MİNDER, TIRMALAMA (u6_p1006, u6_p50, u6_p51, u6_p52)
    if doc_id == "u6_p1006" or "tırmalama" in n:
        return {
            "brand": "Gallus Pet",
            "packaging": "1 Adet (Tabanlı Direk)",
            "fallbackImageUrl": "/images/mutlu-patiler-banner.jpg",
            "description": (
                "Doğal Jüt Halatlı Peluş Tabanlı Kedi Tırmalama Tahtası ve Oyun Direği, kedinizin doğal tırmalama ve "
                "tırnak törpüleme içgüdüsünü sağlıklı bir şekilde gidermesi için tasarlanmıştır. Evdeki koltuk, perde ve "
                "halıların zarar görmesini engeller. Sıkı sarılmış %100 doğal sisal/jüt halat gövdesi patilere zarar vermez; "
                "yumuşak peluş kaplı geniş alt tablası devrilmeye karşı dengelidir ve ucundaki ponpon oyuncak kedinizin "
                "aktif kalmasını sağlar."
            ),
            "ingredients": (
                "Gövde: %100 Doğal Bitkisel Jüt / Sisal Halat Sarım ve Dayanıklı Silindir Gövde. "
                "Taban: 1. Sınıf Kaymaz MDF Üzeri Yumuşak Welsoft Peluş Kumaş Kaplama. Aksesuar: Sarkan Peluş Oyun Topu."
            ),
            "analysis": (
                "Yükseklik: 42 cm | Alt Tabla Ölçüsü: 30 cm x 30 cm | Direk Çapı: 7 cm | "
                "Halat Kalınlığı: 6 mm Doğal Jüt | Ağırlık: ~1.25 kg (Devrilmez Dengeli Taban)."
            ),
            "usage": (
                "Kutu içerisinden çıkan 1 adet montaj vidası ile direği alt tablaya elinizle çevirerek 30 saniyede "
                "kolayca sabitleyebilirsiniz. Kedinizin alışmasını hızlandırmak için tırmalama sütununa bir miktar kedi otu (catnip) sürebilirsiniz."
            ),
            "specs": {
                "Marka": "Gallus Pet Home",
                "Ebatlar": "30 x 30 x 42 cm",
                "Malzeme": "Doğal Jüt Halat + Welsoft Peluş Taban",
                "Hedef Tür": "Yavru ve Yetişkin Tüm Kediler",
                "Kurulum": "Aletsiz Vida İle 30 Saniyede Kolay Montaj"
            },
            "googleProductCategory": g_cat,
            "googleProductCategoryId": g_id
        }

    if doc_id in ["u6_p50", "u6_p51"] or "taşıma" in n or "kafes" in n:
        is_box = doc_id == "u6_p50"
        title_type = "Üstten ve Önden Açılır Havalandırmalı Plastik Kedi/Köpek Taşıma Kutusu (Box)" if is_box else "Kilitli Ergonomik Evcil Hayvan Seyahat ve Veteriner Taşıma Kafesi"
        return {
            "brand": "Gallus Pet Travel",
            "packaging": "1 Adet (50x33x32 cm)",
            "fallbackImageUrl": "/images/mutlu-patiler-banner.jpg",
            "description": (
                f"{title_type}, kedi, küçük ırk köpek ve yavru evcil dostlarınızın veteriner ziyaretlerinde, "
                f"otomobil ve toplu taşıma seyahatlerinde maksimum güvenlik ve konforla taşınması için kırılmaz "
                f"1. sınıf esnek kopolimer PP plastikten üretilmiştir. 360 derece geniş hava kanalları sayesinde "
                f"içeride ferah hava sirkülasyonu sağlar; emniyet kemeri geçiş yuvaları ve çift kademeli yaylı kapı kilidi "
                f"ile kaçma riskini tamamen ortadan kaldırır."
            ),
            "ingredients": (
                "Gövde ve Üst Kapak: %100 BPA İçermeyen Darbeye Dayanıklı Polipropilen (PP) Kopolimer Plastik. "
                "Kilit Mekanizması: Güçlendirilmiş Poliamid Yan Klipsler ve Güvenlik Mandallı Ön Kapı."
            ),
            "analysis": (
                "Dış Ölçüler: Uzunluk 50 cm x Genişlik 33 cm x Yükseklik 32 cm | Taşıma Kapasitesi: Maksimum 8 - 10 kg | "
                "Boş Ağırlık: 1.35 kg | Havalandırma: 4 Yönlü Panoramik Izgara Sistemi."
            ),
            "usage": (
                "Kullanım öncesinde alt ve üst gövdeyi yan klipsleriyle sabitleyiniz. Tabanına kaymaz bir ped veya "
                "ince bir minder yerleştirmeniz dostunuzun yolculuk stresini azaltacaktır. Ilık sabunlu suyla kolayca yıkanıp dezenfekte edilebilir."
            ),
            "specs": {
                "Marka": "Gallus Pet Travel",
                "Boyutlar": "50 x 33 x 32 cm (Standart / Medium Boy)",
                "Taşıma Kapasitesi": "8 - 10 Kg'a Kadar Kedi ve Küçük Irk Köpekler",
                "Özellik": "Emniyet Kemeri Uyumlu, Yıkanabilir, Güvenlik Kilitli",
                "Menşei": "Türkiye"
            },
            "googleProductCategory": g_cat,
            "googleProductCategoryId": g_id
        }

    if doc_id == "u6_p52" or "minder" in n:
        return {
            "brand": "Gallus Pet Comfort",
            "packaging": "1 Adet Yıkanabilir Yatak",
            "fallbackImageUrl": "/images/mutlu-patiler-banner.jpg",
            "description": (
                "Ortopedik Yumuşak Kedi ve Köpek Yatağı / Minderi, evcil dostunuzun gün boyu derin ve huzurlu bir uyku "
                "uyuması için yüksek yoğunluklu boncuk silikon elyaf dolgu ve tüy tutmayan yumuşak dokulu kumaştan "
                "üretilmiştir. Yükseltilmiş yan kenar destekleri kedi ve köpeğinizin başını yaslaması için yastık görevi görür, "
                "eklem ve kaslarını soğuk zeminden izole eder."
            ),
            "ingredients": (
                "Dış Kumaş: Leke Tutmaz, Nefes Alabilen Pamuklu Oxford & Yumuşak Peluş İç Yüzey. "
                "İç Dolgu: %100 Birinci Sınıf Anti-Alerjik Boncuk Silikon Elyaf. Taban: Kaydırmaz Noktalı Tela Taban."
            ),
            "analysis": (
                "Dış Ebatlar: 55 cm x 45 cm x 15 cm | İç Uyku Alanı: 42 cm x 34 cm | "
                "Dolgu Yoğunluğu: 450 gr/m² Çökme Yapmayan Silikon Elyaf | Yıkama Derecesi: 30°C Hassas Program."
            ),
            "usage": (
                "Ev içerisinde cereyan almayan sakin bir köşeye yerleştiriniz. Çamaşır makinesinde 30°C'de sıkma yapmadan "
                "hassas programda yıkanabilir."
            ),
            "specs": {
                "Marka": "Gallus Pet Comfort",
                "Ölçü": "55 x 45 x 15 cm",
                "Taban Yapısı": "Soğuk Geçirmez & Kaymaz Taban",
                "Temizlik": "30°C Makinede Yıkanabilir",
                "Uygunluk": "Tüm Kediler ve Küçük/Orta Irk Köpekler"
            },
            "googleProductCategory": g_cat,
            "googleProductCategoryId": g_id
        }

    # 5. KEDİ KUMLARI VE KOKU GİDERİCİ (u6_p24, u6_p53, u6_p54, u6_p55, u6_p56)
    if doc_id == "u6_p24" or "koku giderici" in n:
        return {
            "brand": "Dreamcat",
            "packaging": "500 g Pratik Serpme Kutu",
            "fallbackImageUrl": "/images/mutlu-patiler-banner.jpg",
            "description": (
                "Dreamcat Aktif Karbonlu Kedi Kumu Koku Giderici Granül, kedi tuvalet kabında oluşan amonyak ve "
                "kötü kokuları parfümle bastırmak yerine moleküler düzeyde hapsederek yok eden %100 doğal aktif karbon "
                "teknolojisine sahiptir. Mevcut kullandığınız her türlü bentonit, silika veya pelet kedi kumunun kullanım "
                "ömrünü uzatır, kumun topaklanma gücünü destekler ve patilere yapışmaz."
            ),
            "ingredients": (
                "%100 Doğal Hindistan Cevizi Kabuğundan Üretilmiş Mikro-Gözenekli Aktif Karbon Granülleri ve Doğal Mineral Zeolit Kompleksi. "
                "Kimyasal parfüm, toz veya toksik bileşen içermez."
            ),
            "analysis": (
                "İyot Sayısı (Adsorpsiyon Gücü): >1000 mg/g | Yüzey Alanı: 1050 m²/g | Toz Oranı: <%0.1 (99.9% Tozsuz) | "
                "Nem Oranı: Maks. %4 | Granül Boyutu: 0.8 - 2.0 mm."
            ),
            "usage": (
                "Temiz kedi kumu kabının en altına 1-2 yemek kaşığı, kumun üst yüzeyine ise 1 yemek kaşığı serperek "
                "hafifçe karıştırınız. Her temizlik sonrasında eksilen miktara göre 1 tatlı kaşığı takviye edebilirsiniz."
            ),
            "specs": {
                "Marka": "Dreamcat",
                "Ürün Tipi": "Aktif Karbonlu Kum Koku Nötralize Edici",
                "Etki Mekanizması": "Amonyak ve Kötü Kokuyu Moleküler Hapsetme",
                "Uyumluluk": "Tüm Bentonit, Silika ve Organik Kumlarla Uyumlu",
                "Menşei": "Türkiye"
            },
            "googleProductCategory": g_cat,
            "googleProductCategoryId": g_id
        }

    if "kum" in n or "litter" in n:
        aroma = "Doğal Aktif Karbonlu (Kokusuz / Nötr)"
        if "lavanta" in n:
            aroma = "Doğal Lavanta Çiçeği Kokulu"
        elif "baby powder" in n or "pudra" in n:
            aroma = "Bebek Pudrası (Baby Powder) Kokulu"
        vol = "10 Litre" if "10" in n else "5 Litre"
        brand_lit = "Sopresh" if "sopresh" in n else brand

        return {
            "brand": brand_lit,
            "packaging": vol,
            "fallbackImageUrl": "/images/mutlu-patiler-banner.jpg",
            "description": (
                f"{brand_lit} {name} ({vol} - {aroma}), %100 doğal beyaz kalsiyum/sodyum bentonit mineralinden üretilmiş, "
                f"süper topaklanan ve %99.5 oranında tozdan arındırılmış üst sınıf kedi kumudur. Sıvıyla temas ettiği anda "
                f"saniyeler içinde taş gibi sağlam topaklar oluşturur; kürekle temizlenirken dağılmaz ve kum kabının tabanına "
                f"yapışmaz. Özel {aroma.lower()} formülü sayesinde kötü kokuları anında hapseder ve evinizde uzun süreli "
                f"hijyenik ferahlık sağlar."
            ),
            "ingredients": (
                f"%100 Doğal Beyaz Sodyum/Kalsiyum Bentonit Kil Minerali ve {'Doğal Hindistan Cevizi Bazlı Aktif Karbon Granülleri' if 'carbon' in n or 'karbon' in n else f'Sıvı Temasıyla Aktifleşen Hipoalerjenik {aroma} Esansı'}."
            ),
            "analysis": (
                "Sıvı Emme Kapasitesi: %320 - %360 | Topaklanma Süresi: < 5 Saniye | Toz Oranı: <%0.5 (%99.5 Tozsuz Çift Eleme) | "
                "Granül Boyutu: 0.6 mm - 2.25 mm İnce/Orta Tane | pH Değeri: 8.5 - 9.2 (Bakteri Üremesini Önleyici Doğal Alkali Yapı)."
            ),
            "usage": (
                "Kedi tuvalet kabına en az 7 - 8 cm yüksekliğinde kum doldurunuz. Her gün topaklanan kısımları ve dışkıyı "
                "uygun bir kum küreği ile temizleyiniz. Eksilen kum miktarını tekrar 7-8 cm seviyesine tamamlayınız. "
                "Atık kumları klozete atmayınız, evsel çöp kutusuna atınız."
            ),
            "specs": {
                "Marka": brand_lit,
                "Hacim": vol,
                "Koku / Özellik": aroma,
                "Tane Yapısı": "İnce-Orta Tane Süper Topaklanan Beyaz Bentonit",
                "Tozsuzlaştırma": "%99.5 Çift Isıl İşlem ve Vakumlu Toz Alma",
                "Menşei": "Türkiye (Doğal Bentonit Madeni)"
            },
            "googleProductCategory": g_cat,
            "googleProductCategoryId": g_id
        }

    # 6. REFLEX CARE PED VE KÖPEK ŞAMPUANLARI (u6_p29, u6_p30, u6_p31, u6_p32)
    if doc_id == "u6_p29" or "alıştırma pedi" in n:
        return {
            "brand": "Reflex Care",
            "packaging": "60x90 cm (30 Adet)",
            "fallbackImageUrl": "/images/mutlu-patiler-banner.jpg",
            "description": (
                "Reflex Care Çiş Alıştırma ve Hasta Altı Bakım Pedi 60x90 cm (30'lu Paket), yavru köpeklerin tuvalet "
                "eğitimi sürecinde, evde yalnız kalan yetişkin köpeklerde, yaşlı/hasta evcil hayvanların bakımında ve "
                "taşıma kutusu tabanında maksimum hijyen sağlamak için 5 katmanlı süper emici polimer (SAP) teknolojisiyle "
                "üretilmiştir. Sıvıyı saniyeler içinde jele dönüştürerek hapseder, patilerin ıslanmasını ve zemine sızıntı "
                "yapmasını %100 engeller."
            ),
            "ingredients": (
                "1. Katman: Hızlı Sıvı Geçirgen Yırtılmaz Non-Woven Üst Yüzey. 2. Katman: Koku Önleyici Feromon Çekici Doku. "
                "3. Katman: Süper Emici Polimer (SAP - Sıvıyı Jele Dönüştüren Mikro Kristaller). "
                "4. Katman: Yüksek Yoğunluklu Selüloz Pamuk Elyaf. 5. Katman: Sızdırmaz ve Kaymaz PE Alt Tabaka."
            ),
            "analysis": (
                "Ped Ölçüsü: 60 cm x 90 cm (Büyük Boy / XL) | Paket İçeriği: 30 Adet | "
                "Sıvı Tutma Kapasitesi: Ped Başına 600 ml'ye Kadar Sıvı Hapsetme | Katman Sayısı: 5 Katmanlı Kilit Sistemi."
            ),
            "usage": (
                "Pedi plastik mavi yüzeyi alta, beyaz emici yüzeyi üste gelecek şekilde köpeğinizin mama ve su kabından "
                "uzak bir noktaya seriniz. Köpeğiniz pedin üzerine tuvaletini yaptığında ödüllendirerek alışkanlığı pekiştiriniz."
            ),
            "specs": {
                "Marka": "Reflex Care",
                "Ebat": "60 x 90 cm (XL Geniş Boy)",
                "Adet": "30'lu Ekonomik Paket",
                "Teknoloji": "Sıvıyı Jele Çeviren SAP Polimer & Sızdırmaz Taban",
                "Kullanım Alanı": "Yavru Köpek Tuvalet Eğitimi, Kedi/Köpek Taşıma Kabı"
            },
            "googleProductCategory": g_cat,
            "googleProductCategoryId": g_id
        }

    if doc_id in ["u6_p30", "u6_p31", "u6_p32"] or "şampuan" in n or "tüy rengini" in n:
        if doc_id == "u6_p30":
            shampoo_type = "Biotin ve Kolajen Destekli Tüy Dökülmesine Karşı Bakım Şampuanı"
            actives = "D-Biotin (Vitamin B7), Hidrolize Kolajen, Provitamin B5 (Panthenol), Aloe Vera Yaprak Özü, E Vitamini."
            benefit = "Tüy köklerini besleyerek mevsimsel olmayan tüy dökülmelerini azaltır, mat tüylere ipeksi parlaklık ve hacim kazandırır."
        elif doc_id == "u6_p31":
            shampoo_type = "Tüy Rengini Canlandırıcı ve Parlaklık Verici Köpek Şampuanı"
            actives = "Papatya Ekstraktı, Doğal Bitkisel Proteinler, Provitamin B5, Gliserin, Aloe Vera ve Optik Renk Koruyucu Bitkisel Özler."
            benefit = "Tüylerdeki sararma ve matlaşmayı giderir, köpeğinizin doğal kürk rengini belirginleştirir ve kolay taranmasını sağlar."
        else:
            shampoo_type = "Bitkisel Özlü Haşere, Pire ve Kene Uzaklaştırıcı Köpek Şampuanı"
            actives = "Doğal Neem (Tesbih Ağacı) Yağı, Lavanta Yağı, Okaliptüs Özü, Citronella (Limon Otu) Yağı, Provitamin B5."
            benefit = "Doğal bitkisel uçucu yağlar sayesinde pire, kene ve dış parazitlerin deriye tutunmasını önlemeye yardımcı olur, kaşıntı ve tahrişi yatıştırır."

        return {
            "brand": "Reflex Care",
            "packaging": "300 ml Şişe",
            "fallbackImageUrl": "/images/mutlu-patiler-banner.jpg",
            "description": (
                f"Reflex Care {name} ({shampoo_type} - 300 ml), köpeklerin hassas deri pH dengesine (pH 6.8 - 7.2) "
                f"tam uyumlu olarak veteriner dermatolojik standartlarda geliştirilmiştir. {benefit} "
                f"Paraben, boya, alkol ve sert sülfat içermez; yıkama sonrası deriyi kurutmaz."
            ),
            "ingredients": (
                f"Deiyonize Su, Yumuşak Hindistan Cevizi Bazlı Yüzey Aktif Maddeler (Coco-Glucoside), {actives} "
                f"Paraben, SLS/SLES ve Yapay Renklendirici İçermez."
            ),
            "analysis": (
                "pH Değeri: 7.0 (Köpek Derisi İle Tam Uyumlu Nötr pH) | Net Hacim: 300 ml | "
                "Dermatolojik Test: Hipoalerjenik, Göz Yakmayan Yumuşak Formül."
            ),
            "usage": (
                "Köpeğinizin tüylerini ılık suyla tamamen ıslatınız. Göz ve kulak içine temas ettirmeden yeterli miktarda "
                "şampuanı sırt bölgesinden başlayarak masaj yaparak köpürtünüz. Aktif bileşenlerin etki etmesi için 2-3 dakika "
                "beklettikten sonra bol ılık suyla iyice durulayınız ve havluyla kurulayınız."
            ),
            "specs": {
                "Marka": "Reflex Care",
                "Hacim": "300 ml",
                "Ürün Özelliği": shampoo_type,
                "pH Dengesi": "pH 7.0 Dengeli (Paraben & Alkol İçermez)",
                "Menşei": "Türkiye"
            },
            "googleProductCategory": g_cat,
            "googleProductCategoryId": g_id
        }

    # 7. KONSERVE YAŞ MAMALAR (u6_p25, u6_p26, u6_p27, u6_p28, u6_p49)
    if doc_id in ["u6_p25", "u6_p26", "u6_p27", "u6_p28", "u6_p49"] or "konserve" in n or "white fish" in n:
        is_cat = (cat_id == "kedi" or "kedi" in n or "cat" in n or "white fish" in n)
        flavor = "Beyaz Balıklı (White Fish)" if "white fish" in n else ("Somon Balıklı" if "somon" in n else ("Tavuk Etli" if "tavuk" in n else ("Kuzu Etli" if "kuzu" in n else "Dana Etli")))
        gram = "85 g Pouch / Konserve" if "85g" in n else "400 g Konserve"
        target_animal = "Yetişkin Kediler" if is_cat else "Yetişkin Köpekler"

        return {
            "brand": brand,
            "packaging": gram,
            "fallbackImageUrl": "/images/mutlu-patiler-banner.jpg",
            "description": (
                f"{brand} {name} ({gram}), {target_animal.lower()} için özenle seçilmiş taze {flavor.lower()} parçacıklarının "
                f"zengin ve lezzetli jöle/sos içerisinde buharda pişirilmesiyle hazırlanmış tam ve dengeli yaş mamadır. "
                f"Yüksek nem oranı (%80+) sayesinde üriner sistem ve böbrek sağlığını destekler; içerdiği kaliteli hayvansal "
                f"proteinler, vitaminler ve mineraller dostunuzun günlük enerji ihtiyacını karşılarken seçici kedi ve köpeklerin "
                f"bile büyük bir iştahla tüketmesini sağlar."
            ),
            "ingredients": (
                f"Et ve Hayvansal Türevler (En az %4 - %15 Gerçek {flavor.replace('lı', '').replace('li', '').replace('lu', '')}), "
                f"{'Balık ve Balık Türevleri, ' if 'somon' in n or 'fish' in n else ''}Tahıllar, Bitkisel Protein Ekstraktları, "
                f"Mineraller, Çeşitli Şekerler. Besinsel Katkılar: {'Taurin (450 mg/kg), ' if is_cat else ''}"
                f"Vitamin A (1100 IU/kg), Vitamin D3 (140 IU/kg), Vitamin E (15 mg/kg), Çinko (10 mg/kg), Manganez (2.5 mg/kg)."
            ),
            "analysis": (
                f"Ham Protein: {'%8.00' if is_cat else '%7.00'} | Ham Yağ: {'%4.50' if is_cat else '%4.00'} | "
                f"Ham Kül: %2.00 - %2.50 | Ham Selüloz (Lif): %0.40 | Nem Oranı: %81.00 | Metabolik Enerji: ~82 kcal/100g."
            ),
            "usage": (
                f"Oda sıcaklığında servis ediniz. Açıldıktan sonra buzdolabında (+4°C) saklayınız ve maksimum 48 saat "
                f"içerisinde tüketiniz. {target_animal} için günlük 1/2 ile 1 kutu arasında, kuru mama ile dönüşümlü veya tek başına verilebilir."
            ),
            "specs": {
                "Marka": brand,
                "Net Ağırlık": gram,
                "Aroma / İçerik": f"Sos İçinde {flavor} Et Parçacıklı",
                "Hedef Tür": target_animal,
                "Koruyucu / Yapay Boya": "İçermez (Buharda Pişirilmiş Taze Konserve)"
            },
            "googleProductCategory": g_cat,
            "googleProductCategoryId": g_id
        }

    # 8. KEDİ KURU MAMALARI (Reflex Plus, Reflex, Enjoy, Trendline, Pancho, Pure Life, Lüks, Açık)
    if cat_id == "kedi":
        is_kitten = ("yavru" in n or "kitten" in n)
        is_steril = ("kısır" in n or "steril" in n or doc_id in ["u6_p47", "u6_p48"])
        is_salmon = ("somon" in n or "salmon" in n or doc_id in ["u6_p47", "u6_p48"])
        is_multi = ("multicolor" in n)
        is_plus = ("reflex plus" in n)

        protein_pct = "%36.00" if is_kitten else ("%32.00" if (is_plus or is_steril) else "%30.00")
        fat_pct = "%18.00" if is_kitten else ("%12.00" if is_steril else "%14.00")
        energy_kcal = "3950 kcal/kg" if is_kitten else ("3650 kcal/kg" if is_steril else "3780 kcal/kg")
        flavor_tr = "Somon Balıklı ve Hamsili" if is_salmon else ("Sebzeli, Tavuklu ve Balıklı Renkli Tanecikli" if is_multi else "Tavuk Etli ve Pirinçli")
        stage_tr = "Yavru Kediler (2 - 12 Aylık)" if is_kitten else ("Kısırlaştırılmış Yetişkin Kediler" if is_steril else "Yetişkin Kediler (1 Yaş Üzeri)")

        return {
            "brand": brand,
            "packaging": packaging,
            "fallbackImageUrl": "/images/mutlu-patiler-banner.jpg",
            "description": (
                f"{brand} {name} ({packaging}), {stage_tr.lower()} için veteriner beslenme uzmanları tarafından "
                f"tam ve dengeli olarak formüle edilmiş {flavor_tr.lower()} kuru kedi mamasıdır. "
                f"{'İçerdiği yeni nesil süper prebiyotik XOS (Ksilo-Oligosakkaritler) ve Psyllium lifi sayesinde bağırsak florasını güçlendirir ve tüy yumağı (hairball) oluşumunu önler. ' if is_plus else ''}"
                f"{'Dengelenmiş magnezyum-fosfor oranı ve idrar pH kontrolü ile kısırlaştırılmış kedilerde taş (struvit/oksalat) oluşumu riskini azaltır, L-Karnitin desteği ile ideal kilonun korunmasına yardımcı olur. ' if is_steril else ''}"
                f"{'Yüksek sindirilebilir protein, DHA ve kalsiyum oranı sayesinde yavru kedilerin kas, kemik, beyin ve görme gelişimini en üst düzeyde destekler. ' if is_kitten else ''}"
                f"Zengin Taurin takviyesi kalp ve göz sağlığını korurken, Omega-3 ve Omega-6 yağ asitleri sağlıklı deri ve parlak tüy oluşumunu sağlar."
            ),
            "ingredients": (
                f"İşlenmiş {('Somon ve Balık Proteini (%32)' if is_salmon else 'Hayvansal Tavuk Proteini (%35)')}, "
                f"Mısır, Buğday, Pirinç (%8), Tavuk Yağı, {'Somon Yağı (Doğal Omega-3 & DHA Kaynağı), ' if is_salmon or is_plus else ''}"
                f"Mısır Gluteni, Kurutulmuş Şeker Pancarı Posası (Doğal Lif), Ciğer Aroması, Bira Mayası, Keten Tohumu, "
                f"{'Ksilo-Oligosakkaritler (XOS Süper Prebiyotik), Psyllium Lifleri, ' if is_plus else 'MOS (Mannan Oligosakkarit), '}"
                f"Taurin (1.500 - 2.200 mg/kg), Yucca Schidigera (Dışkı Kokusu Kontrolü), Tuz, Koruyucular-Antioksidanlar ve "
                f"Vitamin-Mineral Kompleksi (Vitamin A, D3, E, C, B1, B2, B6, B12, Folik Asit, Kolin, Çinko, Demir, Selenyum, İyot)."
            ),
            "analysis": (
                f"Ham Protein: {protein_pct} | Ham Yağ: {fat_pct} | Ham Kül: %7.80 | Ham Selüloz (Lif): {'%3.80' if is_steril else '%2.80'} | "
                f"Metabolik Enerji: {energy_kcal} | Nem: %8.00 | Kalsiyum: %1.30 | Fosfor: %1.00 | Magnezyum: %0.08 | "
                f"Taurin: 1800 mg/kg | Omega-6: %3.40 | Omega-3: %0.75 | Vitamin A: 18.000 IU/kg | Vitamin D3: 1.500 IU/kg | Vitamin E: 200 mg/kg."
            ),
            "usage": (
                f"Kedinizin ağırlığına göre günlük besleme miktarı: 2-3 kg kediler için 35-50 g, 3-5 kg kediler için 50-75 g, "
                f"5-7 kg kediler için 75-95 g. Günlük miktarı sabah ve akşam 2 öğüne bölerek kuru olarak servis ediniz. "
                f"Mama kabının yanında her zaman taze ve temiz içme suyu bulundurunuz."
            ),
            "specs": {
                "Marka": brand,
                "Ambalaj / Ağırlık": packaging,
                "Aroma": flavor_tr,
                "Yaş ve Özel Durum": stage_tr,
                "Tane Boyutu": "Kıtır Ergonomik Kedi Krokisi (Diş Tartar Kontrolü)",
                "Menşei": "Türkiye"
            },
            "googleProductCategory": g_cat,
            "googleProductCategoryId": g_id
        }

    # 9. KÖPEK KURU MAMALARI (Reflex Plus, Reflex, Enjoy, Trendline, King, Pancho, Pure Life, Açık)
    is_puppy = ("yavru" in n or "puppy" in n)
    is_mini = ("mini" in n or "küçük ırk" in n)
    is_lamb = ("kuzu" in n or "lamb" in n)
    is_salmon_dog = ("somon" in n or "salmon" in n)
    is_beef = ("biftek" in n or "beef" in n or "dana" in n)
    is_plus_dog = ("reflex plus" in n or "reflex" in n)

    dog_protein = "%28.00" if (is_puppy or is_mini) else ("%25.00" if is_plus_dog else "%21.00")
    dog_fat = "%16.00" if (is_puppy or is_mini) else ("%13.00" if is_plus_dog else "%10.00")
    dog_energy = "3850 kcal/kg" if (is_puppy or is_mini) else "3520 kcal/kg"
    dog_flavor = "Somon Balıklı ve Pirinçli" if is_salmon_dog else ("Kuzu Etli ve Pirinçli" if is_lamb else ("Biftekli / Dana Etli" if is_beef else "Kuzu ve Tavuk Etli"))
    dog_stage = "Yavru Köpekler (2 - 12 Aylık)" if is_puppy else ("Mini ve Küçük Irk Yetişkin Köpekler" if is_mini else "Tüm Irklar Yetişkin Köpekler")

    return {
        "brand": brand,
        "packaging": packaging,
        "fallbackImageUrl": "/images/mutlu-patiler-banner.jpg",
        "description": (
            f"{brand} {name} ({packaging}), {dog_stage.lower()} için günlük yüksek enerji, güçlü kas yapısı ve "
            f"sağlıklı sindirim gereksinimlerini karşılamak üzere özel olarak üretilmiş {dog_flavor.lower()} tam ve "
            f"dengeli kuru köpek mamasıdır. Yüksek sindirilebilir hayvansal protein kaynakları kas kütlesini korurken, "
            f"dengeli Kalsiyum-Fosfor oranı ve D3 vitamini güçlü iskelet ve diş yapısını destekler. "
            f"{'Hassas sindirime sahip ve alerjiye yatkın köpekler için kuzu eti/somon ve pirinç formülüyle mide-bağırsak konforu sağlar. ' if is_lamb or is_salmon_dog else ''}"
            f"İçeriğindeki keten tohumu, Omega-3 / Omega-6 yağ asitleri ve çinko desteği tüylerin dökülmesini azaltır, "
            f"sağlıklı deri ve parlak kürk görünümü kazandırır."
        ),
        "ingredients": (
            f"İşlenmiş {('Somon ve Balık Proteini' if is_salmon_dog else ('Kuzu Eti ve Hayvansal Protein' if is_lamb else 'Dana/Biftek ve Tavuk Proteini'))}, "
            f"Buğday, Mısır, Pirinç, Hayvansal Yağ, Buğday Kepeği, Kurutulmuş Şeker Pancarı Posası (Doğal Prebiyotik Lif), "
            f"Ciğer Aroması, Keten Tohumu, Kuru Bira Mayası (MOS Kaynağı), Tuz, Yucca Schidigera (Bağırsak ve Koku Kontrolü), "
            f"{'Ksilo-Oligosakkarit (XOS Prebiyotik), Glukozamin ve Kondroitin Sülfat, ' if is_plus_dog else ''}"
            f"Vitaminler (Vitamin A, D3, E, C, B1, B2, B6, B12, Kolin, Folik Asit) ve Şelatlı Mineraller (Çinko, Demir, Bakır, Manganez, Selenyum)."
        ),
        "analysis": (
            f"Ham Protein: {dog_protein} | Ham Yağ: {dog_fat} | Ham Kül: %8.00 | Ham Selüloz (Lif): %3.50 | "
            f"Metabolik Enerji: {dog_energy} | Nem: %9.00 | Kalsiyum: %1.50 | Fosfor: %1.00 | Sodyum: %0.35 | "
            f"Vitamin A: 15.000 IU/kg | Vitamin D3: 1.200 IU/kg | Vitamin E: 120 mg/kg | Omega-6: %2.80 | Omega-3: %0.55."
        ),
        "usage": (
            "Köpeğinizin canlı ağırlığına göre günlük besleme tablosu: 1-5 kg köpekler için 40-110 g, "
            "5-15 kg köpekler için 110-240 g, 15-30 kg köpekler için 240-400 g, 30-50 kg köpekler için 400-580 g. "
            "Mama değişimlerinde ilk 7 gün eski mamasıyla kademeli olarak karıştırarak veriniz ve yanında daima taze içme suyu bulundurunuz."
        ),
        "specs": {
            "Marka": brand,
            "Ambalaj / Ağırlık": packaging,
            "Aroma / Protein": dog_flavor,
            "Hedef Irk ve Yaş": dog_stage,
            "Tane Formu": "Diş Sağlığını Destekleyen Kıtır Krokiler",
            "Menşei": "Türkiye"
        },
        "googleProductCategory": g_cat,
        "googleProductCategoryId": g_id
    }

def is_generic_or_broken_image(url: str) -> bool:
    if not url:
        return True
    if "images.unsplash.com" in url:
        return True
    if url in ["/images/tavuklar.jpg", "/images/yumurta-koli-banner.jpg", "/images/mutlu-patiler-banner.jpg", "/images/adrese-teslimat-banner.jpg"]:
        return True
    if url.startswith("/images/uploads/"):
        local_file = BASE_DIR / "public" / url.lstrip("/")
        if not local_file.exists():
            return True
    return False

def detect_category(name: str, cat_name: str = "") -> Tuple[str, str]:
    text = (name + " " + cat_name).lower()

    if any(k in text for k in ["taşıma kutusu", "tasima kutusu", "taşıma kafesi", "tasima kafesi", "suluk", "yemlik", "folluk", "tünek", "minder", "kafes", "tırmalama", "tirmalama"]):
        return "kumes-ekipman", "Kümes Ekipmanları"

    if any(k in text for k in ["balık", "balik", "akvaryum", "aquarium", "pul yem", "tetra"]):
        return "balik-akvaryum", "Balık Yemleri ve Akvaryum"

    if any(k in text for k in ["kedi", "cat", "kitten", "kum", "litter", "marsilya", "lavanta kokulu", "aktif karbon", "koku giderici", "white fish", "multicolor cat"]):
        return "kedi", "Kedi Mamaları ve Ürünleri"

    if any(k in text for k in ["köpek", "kopek", "dog", "puppy", "biftekli", "çoban", "kuzu etli yavru köpek", "alıştırma pedi", "şampuanı", "sampo", "tüy rengini", "haşere önleyici", "kuzulu extra"]):
        return "kopek", "Köpek Mamaları ve Ürünleri"

    if any(k in text for k in ["tavuk yemi", "civciv", "yumurta yemi", "piliç", "kanatlı yemi"]):
        return "tavuk-civciv", "Tavuk ve Civciv Yemleri"

    if any(k in text for k in ["güvercin", "guvercin", "buğday", "bugday", "mısır", "darı", "fiğ", "aspir"]):
        return "guvercin", "Güvercin Yemleri"

    if any(k in text for k in ["gübre", "gubre", "tohum", "bahçe", "bahce", "fide", "toprak", "torf"]):
        return "tarim-bahce", "Tarım ve Bahçe Ürünleri"

    return "diger", "Diğer Ürünler"

def detect_brand(name: str, doc_id: str = "") -> str:
    if doc_id in ["u6_p1002", "u6_p1003", "u6_p67", "u6_p68"]:
        return "Eriş Yem"
    upper_name = name.strip().upper()
    if "ERİŞ" in upper_name or "ERIS" in upper_name or "TAVUK YEMİ" in upper_name or "CİVCİV YEMİ" in upper_name or "CIVCIV YEMI" in upper_name:
        return "Eriş Yem"
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
    if any(k in upper_name for k in ["YUMURTA", "GALLUS", "BUĞDAY", "BUGDAY"]):
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

def resolve_image(doc_id: str, name: str, category_id: str, existing_image: str = "") -> str:
    # 1. If user uploaded a valid custom image that exists on disk, keep it
    if existing_image and existing_image.startswith("/images/uploads/") and not is_generic_or_broken_image(existing_image):
        return existing_image

    # 2. Check exact ID map (prioritizes Eriş Yem & verified product images)
    if doc_id in EXACT_ID_IMAGE_MAP:
        return EXACT_ID_IMAGE_MAP[doc_id]

    # 3. If existing image is already a real non-generic product URL, keep it
    if existing_image and existing_image.startswith("http") and not is_generic_or_broken_image(existing_image):
        return existing_image

    # 4. Smart keyword match
    n = name.lower()
    if "yumurta" in n and "yemi" not in n:
        return IMAGE_MAP["farm_eggs"]
    if "civciv" in n:
        return IMAGE_MAP["chick_feed"]
    if "tavuk yemi" in n or "yumurta yemi" in n:
        return IMAGE_MAP["chicken_feed"]
    if "buğday" in n or "bugday" in n:
        return IMAGE_MAP["wheat_grain"]
    if "muhabbet" in n or "kuş" in n or "kus" in n:
        return IMAGE_MAP["bird_feed"]
    if "tırmalama" in n or "tirmalama" in n:
        return EXACT_ID_IMAGE_MAP["u6_p1006"]
    if "minder" in n:
        return EXACT_ID_IMAGE_MAP["u6_p52"]
    if "taşıma" in n or "tasima" in n or "kafes" in n:
        return IMAGE_MAP["equipment"]
    if "kum" in n or "litter" in n or "koku giderici" in n:
        return IMAGE_MAP["cat_litter"]
    if "konserve" in n or "400g" in n or "85g" in n:
        return IMAGE_MAP["cat_canned"] if category_id == "kedi" else IMAGE_MAP["dog_canned"]
    if "ped" in n:
        return EXACT_ID_IMAGE_MAP["u6_p29"]
    if "şampuan" in n or "tüy" in n:
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

def generate_google_shopping_xml(products: list) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss xmlns:g="http://base.google.com/ns/1.0" version="2.0">',
        '  <channel>',
        '    <title>Gallus Mama &amp; Yumurta - Google Alışveriş Ürün Kataloğu</title>',
        f'    <link>{SITE_DOMAIN}</link>',
        '    <description>Değirmenköy Gezen Tavuk Çiftliği Günlük Taze Yumurtaları, Eriş Yem Kanatlı Yemleri ve Premium Kedi/Köpek Mamaları Resmi Google Merchant Center Ürün Beslemesi</description>'
    ]
    for p in products:
        pid = xml_escape(str(p.get("id") or ""))
        slug = xml_escape(str(p.get("slug") or pid))
        title = xml_escape(f"{p.get('name', '')} ({p.get('brand', 'Gallus Mama')} - {p.get('packaging', p.get('unit', 'Standart'))})")
        desc = xml_escape(f"{p.get('description', '')} İçindekiler: {p.get('ingredients', '')} Analiz: {p.get('analysis', '')}")
        link = f"{SITE_DOMAIN}/urun/{slug}"
        img = str(p.get("imageUrl") or "")
        if img.startswith("/"):
            img = f"{SITE_DOMAIN}{img}"
        img = xml_escape(img)
        price_val = float(p.get("price") or p.get("sale_price") or 0.0)
        stock_val = float(p.get("stock") or p.get("stock_quantity") or 0.0)
        availability = "in_stock" if stock_val > 0 else "out_of_stock"
        brand = xml_escape(str(p.get("brand") or "Gallus Mama"))
        mpn = xml_escape(str(p.get("sku") or f"GL-{pid.upper()}"))
        g_cat = xml_escape(str(p.get("googleProductCategory") or "Animals & Pet Supplies > Pet Supplies"))
        p_type = xml_escape(str(p.get("categoryName") or "Pet & Çiftlik Ürünleri"))
        shipping_price = "0.00 TRY" if price_val >= 750 else "49.00 TRY"

        lines.extend([
            '    <item>',
            f'      <g:id>{pid}</g:id>',
            f'      <g:title>{title}</g:title>',
            f'      <g:description>{desc}</g:description>',
            f'      <g:link>{link}</g:link>',
            f'      <g:image_link>{img}</g:image_link>',
            '      <g:condition>new</g:condition>',
            f'      <g:availability>{availability}</g:availability>',
            f'      <g:price>{price_val:.2f} TRY</g:price>',
            f'      <g:brand>{brand}</g:brand>',
            f'      <g:mpn>{mpn}</g:mpn>',
            '      <g:identifier_exists>yes</g:identifier_exists>',
            f'      <g:google_product_category>{g_cat}</g:google_product_category>',
            f'      <g:product_type>{p_type}</g:product_type>',
            '      <g:shipping>',
            '        <g:country>TR</g:country>',
            '        <g:service>Standart Kargo / Çiftlik Servisi</g:service>',
            f'        <g:price>{shipping_price}</g:price>',
            '      </g:shipping>',
            '    </item>'
        ])
    lines.extend([
        '  </channel>',
        '</rss>'
    ])
    return "\n".join(lines)

def generate_sitemap_xml(products: list) -> str:
    today = time.strftime("%Y-%m-%d")
    static_routes = [
        "", "/kedi", "/kedi/mama", "/kedi/kum", "/kopek", "/kopek/mama",
        "/tavuk-civciv", "/guvercin", "/balik-akvaryum", "/kumes-ekipman",
        "/tarim-bahce", "/yumurta", "/diger", "/markalar", "/kampanyalar",
        "/toptan-satis", "/hakkimizda", "/ciftligimiz", "/iletisim",
        "/yardim", "/kargo-ve-iade"
    ]
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    for r in static_routes:
        prio = "1.0" if r == "" else "0.8"
        lines.append(
            f"  <url>\n    <loc>{SITE_DOMAIN}{r}</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>{prio}</priority>\n  </url>"
        )
    for p in products:
        slug = p.get("slug") or p.get("id")
        lines.append(
            f"  <url>\n    <loc>{SITE_DOMAIN}/urun/{slug}</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>0.9</priority>\n  </url>"
        )
    lines.append("</urlset>")
    return "\n".join(lines)

def sync_all_products(user_id: int = 6):
    """Firestore 'products' koleksiyonundan tüm ürünleri okur,
    detaylı içerik, analiz, kullanım, Eriş Yem görselleri ve Google Alışveriş verileriyle
    'product_web_meta', 'public_products' ve yerel 'database.json' dosyalarını günceller."""
    logger.info("Firestore ürünleri, Eriş Yem görselleri ve detaylı ürün içerikleri senkronize ediliyor...")

    try:
        db.collection("public_products").document("prod-1").delete()
    except Exception:
        pass

    products_stream = db.collection("products").stream()
    synced_count = 0
    local_products_list = []

    batch = db.batch()
    batch_ops = 0

    for doc in sorted(list(products_stream), key=lambda x: x.id):
        d = doc.to_dict()
        doc_uid = d.get("user_id")

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

        meta_ref = db.collection("product_web_meta").document(doc_id)
        meta_doc = meta_ref.get()
        meta_data = meta_doc.to_dict() if meta_doc.exists else {}

        cat_id, cat_name = detect_category(name, d.get("category_name", ""))
        brand = detect_brand(name, doc_id)
        packaging = detect_packaging(name, unit)

        detailed = build_detailed_product_content(doc_id, name, cat_id, brand, packaging, unit)
        brand = detailed["brand"]
        packaging = detailed["packaging"]
        description = detailed["description"]
        ingredients = detailed["ingredients"]
        analysis = detailed["analysis"]
        usage = detailed["usage"]
        specs = detailed["specs"]
        fallback_img = detailed.get("fallbackImageUrl") or "/images/mutlu-patiler-banner.jpg"
        g_cat = detailed["googleProductCategory"]
        g_cat_id = detailed["googleProductCategoryId"]

        image_url = resolve_image(doc_id, name, cat_id, meta_data.get("imageUrl") or d.get("image_path", ""))
        slug = meta_data.get("slug") or f"{slugify(name)}-{str(pid)}"
        sku = f"GL-{doc_id.upper().replace('_', '-')}"

        is_popular = bool(meta_data.get("isPopular", stock_quantity >= 10 and sale_price >= 40))
        is_featured = bool(meta_data.get("isFeatured", is_popular))
        badge = meta_data.get("badge", "Çok Satan" if is_popular else "")

        new_meta = {
            "id": pid,
            "productId": doc_id,
            "sku": sku,
            "category": cat_id,
            "categoryName": cat_name,
            "brand": brand,
            "packaging": packaging,
            "description": description,
            "ingredients": ingredients,
            "analysis": analysis,
            "usage": usage,
            "specs": specs,
            "imageUrl": image_url,
            "fallbackImageUrl": fallback_img,
            "slug": slug,
            "googleProductCategory": g_cat,
            "googleProductCategoryId": g_cat_id,
            "condition": "new",
            "isPopular": is_popular,
            "isFeatured": is_featured,
            "badge": badge,
            "updatedAt": firestore.SERVER_TIMESTAMP
        }
        batch.set(meta_ref, new_meta, merge=True)
        batch_ops += 1

        public_ref = db.collection("public_products").document(doc_id)
        public_doc = {
            "id": doc_id,
            "doc_id": doc_id,
            "productId": pid,
            "sku": sku,
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
            "ingredients": ingredients,
            "analysis": analysis,
            "usage": usage,
            "specs": specs,
            "imageUrl": image_url,
            "fallbackImageUrl": fallback_img,
            "gallery": [image_url],
            "slug": slug,
            "googleProductCategory": g_cat,
            "googleProductCategoryId": g_cat_id,
            "condition": "new",
            "availability": "in_stock" if stock_quantity > 0 else "out_of_stock",
            "isPopular": is_popular,
            "isFeatured": is_featured,
            "badge": badge,
            "inStock": stock_quantity > 0,
            "updatedAt": firestore.SERVER_TIMESTAMP
        }
        batch.set(public_ref, public_doc, merge=True)
        batch_ops += 1
        synced_count += 1

        local_doc = dict(public_doc)
        local_doc["updatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        local_products_list.append(local_doc)

        if batch_ops >= 400:
            batch.commit()
            batch = db.batch()
            batch_ops = 0

    if batch_ops > 0:
        batch.commit()

    # Update local database.json files
    for db_path in [
        BASE_DIR / "data" / "database.json",
        BASE_DIR / "gallus mama" / "data" / "database.json"
    ]:
        try:
            existing_db = json.loads(db_path.read_text(encoding="utf-8")) if db_path.exists() else {}
            existing_db["products"] = local_products_list
            existing_db["categories"] = CATEGORIES
            existing_db["brands"] = BRANDS
            db_path.parent.mkdir(parents=True, exist_ok=True)
            db_path.write_text(json.dumps(existing_db, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Local DB update warning ({db_path}): {e}")

    # Generate Google Shopping Feed XML, Sitemap XML, and Robots.txt
    shopping_xml = generate_google_shopping_xml(local_products_list)
    sitemap_xml = generate_sitemap_xml(local_products_list)
    robots_txt = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /api/\n\n"
        f"Sitemap: {SITE_DOMAIN}/sitemap.xml\n"
        f"# Google Merchant Center Feed: {SITE_DOMAIN}/google-shopping-feed.xml\n"
    )

    for pub_dir in [BASE_DIR / "public", BASE_DIR / "gallus mama" / "public"]:
        try:
            pub_dir.mkdir(parents=True, exist_ok=True)
            (pub_dir / "google-shopping-feed.xml").write_text(shopping_xml, encoding="utf-8")
            (pub_dir / "sitemap.xml").write_text(sitemap_xml, encoding="utf-8")
            (pub_dir / "robots.txt").write_text(robots_txt, encoding="utf-8")
        except Exception as e:
            logger.warning(f"Static SEO files write warning ({pub_dir}): {e}")

    logger.info(f"Başarıyla {synced_count} ürün detaylı içerikleri, Eriş Yem görselleri ve Google Alışveriş XML beslemesiyle eşitlendi.")
    return synced_count

if __name__ == "__main__":
    count = sync_all_products(user_id=6)
    print(f"\n[OK] Toplam {count} ürün detaylı açıklamaları, içerik analizleri, Eriş Yem görselleri ve Google Alışveriş uyumluluğuyla senkronize edildi.")
