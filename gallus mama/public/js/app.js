/* ==========================================================================
   Gallus Mama & Yumurta - Main Application JavaScript
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initApp();
  bindCartEvents();
});

let allProducts = [];
let allCategories = [];
let activeCategoryId = 'all';
let cart = [];

// Turkey All 81 Cities & Complete Districts Mapping
const istanbulDistricts = [
  'Silivri (Değirmenköy / Gümüşyaka / Çantaköy)',
  'Adalar', 'Arnavutköy', 'Ataşehir', 'Avcılar', 'Bağcılar', 'Bahçelievler',
  'Bakırköy', 'Başakşehir', 'Bayrampaşa', 'Beşiktaş', 'Beykoz', 'Beylikdüzü',
  'Beyoğlu', 'Büyükçekmece', 'Çatalca', 'Çekmeköy', 'Esenler', 'Esenyurt',
  'Eyüpsultan', 'Fatih', 'Gaziosmanpaşa', 'Güngören', 'Kadıköy', 'Kağıthane',
  'Kartal', 'Küçükçekmece', 'Maltepe', 'Pendik', 'Sancaktepe', 'Sarıyer',
  'Sultanbeyli', 'Sultangazi', 'Şile', 'Şişli', 'Tuzla', 'Ümraniye', 'Üsküdar', 'Zeytinburnu'
];

const tekirdagDistricts = ['Çorlu', 'Çerkezköy', 'Kapaklı', 'Muratlı', 'Ergene', 'Marmaraereğlisi', 'Süleymanpaşa', 'Hayrabolu', 'Malkara', 'Şarköy', 'Saray'];
const edirneDistricts = ['Keşan', 'Uzunköprü', 'Havsa', 'Merkez', 'İpsala', 'Enez', 'Süloğlu', 'Lalapaşa', 'Meriç'];
const kirklareliDistricts = ['Lüleburgaz', 'Babaeski', 'Vize', 'Merkez', 'Pınarhisar', 'Demirköy', 'Kofçaz', 'Pehlivanköy'];
const kocaeliDistricts = ['Gebze', 'Darıca', 'İzmit', 'Çayırova', 'Dilovası', 'Körfez', 'Gölcük', 'Derince', 'Kartepe', 'Başiskele', 'Kandıra', 'Karamürsel'];
const ankaraDistricts = ['Çankaya', 'Keçiören', 'Yenimahalle', 'Mamık', 'Etimesgut', 'Sincan', 'Altındağ', 'Golbaşı', 'Merkez / Diğer'];
const izmirDistricts = ['Konak', 'Karşıyaka', 'Bornova', 'Buca', 'Çiğli', 'Gaziemir', 'Balçova', 'Urla', 'Çeşme', 'Merkez / Diğer'];
const bursaDistricts = ['Nilüfer', 'Osmangazi', 'Yıldırım', 'İnegöl', 'Gemlik', 'Mudanya', 'Merkez / Diğer'];

const turkeyCitiesList = [
  "İstanbul", "Tekirdağ", "Edirne", "Kırklareli", "Kocaeli",
  "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara", "Antalya", "Ardahan", "Artvin", "Aydın",
  "Balıkesir", "Bartın", "Batman", "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa",
  "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Elazığ", "Erzincan", "Erzurum", "Eskişehir",
  "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "İzmir", "Kahramanmaraş", "Karabük",
  "Karaman", "Kars", "Kastamonu", "Kayseri", "Kırıkkale", "Kırşehir", "Kilis", "Konya", "Kütahya", "Malatya",
  "Manisa", "Mardin", "Mersin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya",
  "Samsun", "Siirt", "Sinop", "Sivas", "Şanlıurfa", "Şırnak", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van", "Yalova", "Yozgat", "Zonguldak"
];

async function initApp() {
  loadCartFromStorage();
  populateCitiesDropdown();
  await loadSiteInfo();
  await loadCategories();
  await loadPopularProducts();
  await loadAllProducts();
}

function bindCartEvents() {
  document.querySelectorAll('.cart-toggle-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      openCartModal();
    });
  });
}

function populateCitiesDropdown() {
  const citySelect = document.getElementById('order-city');
  if (!citySelect) return;

  citySelect.innerHTML = turkeyCitiesList.map(c => `<option value="${c}">${c}</option>`).join('');
  updateDistrictsDropdown();
}

function scrollToSection(id) {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: 'smooth' });
}

function toggleMobileNav() {
  const overlay = document.getElementById('mobile-nav');
  if (overlay) overlay.classList.toggle('open');
}

// 1. Load Site Info
async function loadSiteInfo() {
  try {
    const res = await fetch('/api/info');
    if (!res.ok) return;
    const info = await res.json();

    if (info.slogan) {
      const sloganEl = document.getElementById('hero-slogan');
      if (sloganEl) sloganEl.textContent = info.slogan;
    }

    if (info.heroTitle) {
      const heroTitleEl = document.getElementById('hero-title-el');
      if (heroTitleEl) {
        heroTitleEl.innerHTML = `${escapeHtml(info.heroTitle)} <br><span class="text-gradient" id="hero-slogan">${escapeHtml(info.slogan || '')}</span>`;
      }
    }

    if (info.heroImage) {
      const heroImg = document.getElementById('hero-img');
      if (heroImg) heroImg.src = info.heroImage;
    }

    if (info.aboutTitle) {
      const aboutTitleEl = document.getElementById('about-title-el');
      if (aboutTitleEl) aboutTitleEl.textContent = info.aboutTitle;
    }

    if (info.aboutText) {
      const aboutShortEl = document.getElementById('hero-about-short');
      const aboutFullEl = document.getElementById('about-full-text');
      if (aboutShortEl) aboutShortEl.textContent = info.aboutText;
      if (aboutFullEl) aboutFullEl.textContent = info.aboutText;
    }

    if (info.aboutImage) {
      const aboutImg = document.getElementById('about-img');
      if (aboutImg) aboutImg.src = info.aboutImage;
    }

    if (info.address) {
      const el = document.getElementById('info-address');
      if (el) el.textContent = info.address;
    }
    if (info.phone) {
      const el = document.getElementById('info-phone');
      if (el) el.textContent = info.phone;
    }
    if (info.email) {
      const el = document.getElementById('info-email');
      if (el) el.textContent = info.email;
    }
    if (info.workingHours) {
      const el = document.getElementById('info-hours');
      if (el) el.textContent = info.workingHours;
    }

    if (info.googleMapsEmbedUrl) {
      const iframe = document.getElementById('google-maps-iframe');
      if (iframe) iframe.src = info.googleMapsEmbedUrl;
    }

    if (info.whatsappUrl) {
      const floatBtn = document.getElementById('whatsapp-float-btn');
      const heroWpBtn = document.getElementById('hero-whatsapp-btn');
      if (floatBtn) floatBtn.href = info.whatsappUrl;
      if (heroWpBtn) heroWpBtn.href = info.whatsappUrl;
    }

    if (info.instagramGallusMamaUrl) {
      const el = document.getElementById('link-ig-mama');
      if (el) el.href = info.instagramGallusMamaUrl;
    }

    if (info.instagramGallusYumurtaUrl) {
      const el = document.getElementById('link-ig-yumurta');
      if (el) el.href = info.instagramGallusYumurtaUrl;
    }

    if (info.googleMapsUrl) {
      const el = document.getElementById('link-google-maps');
      if (el) el.href = info.googleMapsUrl;
    }

  } catch (err) {
    console.error('Site info loading error:', err);
  }
}

// 2. Load Categories
async function loadCategories() {
  try {
    const res = await fetch('/api/categories');
    if (!res.ok) return;
    allCategories = await res.json();

    const tabsContainer = document.getElementById('category-tabs');
    if (!tabsContainer) return;

    tabsContainer.innerHTML = `
      <button class="category-tab ${activeCategoryId === 'all' ? 'active' : ''}" onclick="filterCategory('all')">🔥 Tüm Ürünler</button>
    `;

    allCategories.forEach(cat => {
      const btn = document.createElement('button');
      btn.className = `category-tab ${activeCategoryId === cat.id ? 'active' : ''}`;
      btn.onclick = () => filterCategory(cat.id);
      btn.innerHTML = `${cat.icon || '🏷️'} ${escapeHtml(cat.name)}`;
      tabsContainer.appendChild(btn);
    });
  } catch (err) {
    console.error('Categories loading error:', err);
  }
}

// 3. Load Popular Products
async function loadPopularProducts() {
  const container = document.getElementById('popular-products-grid');
  if (!container) return;

  try {
    const res = await fetch('/api/products?popular=true');
    if (!res.ok) return;
    const popularList = await res.json();

    if (popularList.length === 0) {
      container.innerHTML = `
        <div class="text-center" style="grid-column: 1/-1; padding: 40px; color: var(--color-text-muted);">
          Henüz öne çıkarılmış ürün bulunmuyor.
        </div>
      `;
      return;
    }

    container.innerHTML = popularList.map(p => renderProductCard(p)).join('');
  } catch (err) {
    console.error('Popular products loading error:', err);
  }
}

// 4. Load All Products
async function loadAllProducts() {
  const container = document.getElementById('all-products-grid');
  if (!container) return;

  try {
    const res = await fetch('/api/products');
    if (!res.ok) return;
    allProducts = await res.json();
    renderFilteredProducts();
  } catch (err) {
    console.error('All products loading error:', err);
  }
}

function filterCategory(categoryId) {
  activeCategoryId = categoryId;
  loadCategories();
  renderFilteredProducts();
}

function renderFilteredProducts() {
  const container = document.getElementById('all-products-grid');
  if (!container) return;

  let filtered = allProducts;
  if (activeCategoryId !== 'all') {
    filtered = allProducts.filter(p => p.categoryId === activeCategoryId);
  }

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="text-center" style="grid-column: 1/-1; padding: 50px; color: var(--color-text-muted); background: var(--color-bg-card); border-radius: var(--radius-md); border: 1px solid var(--color-border);">
        <div style="font-size: 3rem; margin-bottom: 10px;">🍽️</div>
        <h3>Bu kategoride henüz ürün bulunmuyor.</h3>
      </div>
    `;
    return;
  }

  container.innerHTML = filtered.map(p => renderProductCard(p)).join('');
}

function renderProductCard(product) {
  const category = allCategories.find(c => c.id === product.categoryId);
  const categoryName = category ? category.name : 'Gallus Özel';
  const defaultImg = 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80';
  const imgSrc = product.imageUrl || defaultImg;

  return `
    <article class="product-card">
      <div class="product-thumb">
        <img src="${imgSrc}" alt="${escapeHtml(product.name)}" onerror="this.src='${defaultImg}'">
        ${product.isPopular ? '<div class="popular-badge">⭐ POPÜLER</div>' : ''}
      </div>
      <div class="product-body">
        <div class="product-category">${escapeHtml(categoryName)}</div>
        <h3 class="product-title">${escapeHtml(product.name)}</h3>
        <p class="product-desc">${escapeHtml(product.description || 'Nefis lezzet ve özenle hazırlanan Gallus Mama tarifi.')}</p>
        <div class="product-footer">
          <div class="product-price">${Number(product.price).toLocaleString('tr-TR')} ₺</div>
          <button type="button" class="add-cart-btn" onclick="addToCart('${product.id}')">
            <span>🛒 Sepete Ekle</span>
          </button>
        </div>
      </div>
    </article>
  `;
}

/* ==========================================================================
   SHOPPING CART SYSTEM
   ========================================================================== */

function loadCartFromStorage() {
  try {
    const saved = localStorage.getItem('gallus_cart');
    if (saved) {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed)) {
        cart = parsed.filter(item => item && item.id && item.price);
      } else {
        cart = [];
      }
    } else {
      cart = [];
    }
  } catch (e) {
    cart = [];
  }
  updateCartUI();
}

function saveCartToStorage() {
  try {
    localStorage.setItem('gallus_cart', JSON.stringify(cart));
  } catch (e) {
    console.error('Storage save error:', e);
  }
  updateCartUI();
}

function addToCart(productId) {
  let product = allProducts.find(p => p.id === productId);

  // Fallback for Organik Yumurta banner if allProducts is still loading
  if (!product && productId === 'prod-102') {
    product = {
      id: 'prod-102',
      name: "GALLUS Gezen Tavuk Taze Koli Yumurta (30'lu L Boy)",
      price: 150,
      imageUrl: "/images/yumurta-koli-banner.jpg"
    };
  }

  if (!product) return;

  const existingItem = cart.find(item => item.id === productId);
  if (existingItem) {
    existingItem.quantity = (Number(existingItem.quantity) || 1) + 1;
  } else {
    cart.push({
      id: product.id,
      name: product.name,
      price: Number(product.price) || 0,
      imageUrl: product.imageUrl || '',
      quantity: 1
    });
  }

  saveCartToStorage();
  showToast(`"${product.name}" sepete eklendi! 🛒`, 'success');
}

function updateCartQuantity(productId, delta) {
  const item = cart.find(i => i.id === productId);
  if (!item) return;

  item.quantity = (Number(item.quantity) || 1) + delta;
  if (item.quantity <= 0) {
    cart = cart.filter(i => i.id !== productId);
  }
  saveCartToStorage();
  renderCartModalItems();
}

function removeFromCart(productId) {
  cart = cart.filter(i => i.id !== productId);
  saveCartToStorage();
  renderCartModalItems();
}

function updateCartUI() {
  if (!Array.isArray(cart)) cart = [];
  const totalCount = cart.reduce((sum, i) => sum + (Number(i.quantity) || 0), 0);
  
  const badgeEl = document.getElementById('cart-count-badge');
  const mobileBadgeEl = document.querySelector('.cart-badge-count-mobile');
  
  if (badgeEl) badgeEl.textContent = totalCount;
  if (mobileBadgeEl) mobileBadgeEl.textContent = totalCount;
}

function openCartModal() {
  try {
    renderCartModalItems();
  } catch (err) {
    console.error('Error rendering cart modal items:', err);
  }
  const modal = document.getElementById('cart-modal');
  if (modal) {
    modal.classList.add('open');
    modal.style.display = 'flex';
  }
}

function closeCartModal() {
  const modal = document.getElementById('cart-modal');
  if (modal) {
    modal.classList.remove('open');
    modal.style.display = 'none';
  }
}

function renderCartModalItems() {
  const container = document.getElementById('cart-items-container');
  const totalPriceEl = document.getElementById('cart-total-price');
  const checkoutBtn = document.getElementById('cart-checkout-btn');

  if (!container) return;
  if (!Array.isArray(cart)) cart = [];

  if (cart.length === 0) {
    container.innerHTML = `
      <div class="text-center" style="padding: 30px; color: var(--color-text-muted);">
        <div style="font-size: 2.5rem; margin-bottom: 8px;">🛒</div>
        <p>Sepetiniz şu anda boş.</p>
      </div>
    `;
    if (totalPriceEl) totalPriceEl.textContent = '0 ₺';
    if (checkoutBtn) checkoutBtn.disabled = true;
    return;
  }

  let total = 0;
  container.innerHTML = cart.map(item => {
    const price = Number(item.price) || 0;
    const quantity = Number(item.quantity) || 1;
    const itemTotal = price * quantity;
    total += itemTotal;
    return `
      <div class="cart-drawer-item">
        <div style="display: flex; align-items: center; gap: 12px;">
          <img src="${item.imageUrl || 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80'}" alt="${escapeHtml(item.name)}" style="width: 48px; height: 48px; border-radius: var(--radius-sm); object-fit: cover;">
          <div>
            <strong style="font-size: 0.95rem; color: var(--color-text-main); display: block;">${escapeHtml(item.name)}</strong>
            <span style="color: var(--color-accent); font-weight: 700; font-size: 0.9rem;">${price.toLocaleString('tr-TR')} ₺</span>
          </div>
        </div>

        <div style="display: flex; align-items: center; gap: 10px;">
          <button type="button" class="qty-btn" onclick="updateCartQuantity('${item.id}', -1)">-</button>
          <span style="font-weight: 800; min-width: 20px; text-align: center;">${quantity}</span>
          <button type="button" class="qty-btn" onclick="updateCartQuantity('${item.id}', 1)">+</button>
          <button type="button" onclick="removeFromCart('${item.id}')" style="color: var(--color-danger); font-size: 1.1rem; margin-left: 8px;">🗑️</button>
        </div>
      </div>
    `;
  }).join('');

  if (totalPriceEl) totalPriceEl.textContent = `${total.toLocaleString('tr-TR')} ₺`;
  if (checkoutBtn) checkoutBtn.disabled = false;
}

/* ==========================================================================
   TRENDYOL STYLE ADDRESS & CREDIT CARD CHECKOUT
   ========================================================================== */

function openCheckoutModal() {
  closeCartModal();
  if (!Array.isArray(cart)) cart = [];
  const totalPrice = cart.reduce((sum, i) => sum + ((Number(i.price) || 0) * (Number(i.quantity) || 1)), 0);
  const checkoutTotalEl = document.getElementById('checkout-total-price');
  if (checkoutTotalEl) checkoutTotalEl.textContent = `${totalPrice.toLocaleString('tr-TR')} ₺`;
  populateCitiesDropdown();
  const modal = document.getElementById('checkout-modal');
  if (modal) {
    modal.classList.add('open');
    modal.style.display = 'flex';
  }
}

function closeCheckoutModal() {
  const modal = document.getElementById('checkout-modal');
  if (modal) {
    modal.classList.remove('open');
    modal.style.display = 'none';
  }
}

function updateDistrictsDropdown() {
  const citySelect = document.getElementById('order-city');
  const districtSelect = document.getElementById('order-district');
  if (!citySelect || !districtSelect) return;

  const selectedCity = citySelect.value;
  let districts = [];

  if (selectedCity === 'İstanbul') {
    districts = istanbulDistricts;
  } else if (selectedCity === 'Tekirdağ') {
    districts = tekirdagDistricts;
  } else if (selectedCity === 'Edirne') {
    districts = edirneDistricts;
  } else if (selectedCity === 'Kırklareli') {
    districts = kirklareliDistricts;
  } else if (selectedCity === 'Kocaeli') {
    districts = kocaeliDistricts;
  } else if (selectedCity === 'Ankara') {
    districts = ankaraDistricts;
  } else if (selectedCity === 'İzmir') {
    districts = izmirDistricts;
  } else if (selectedCity === 'Bursa') {
    districts = bursaDistricts;
  } else {
    districts = ['Merkez', 'Diğer İlçe / Semt'];
  }

  districtSelect.innerHTML = districts.map(d => `<option value="${d}">${d}</option>`).join('');
}

function selectPaymentMethod(method) {
  const cardOption = document.getElementById('pay-card');
  const cashOption = document.getElementById('pay-cash');
  const cardSection = document.getElementById('credit-card-details-section');
  const hiddenInput = document.getElementById('order-payment-method');

  if (method === 'card') {
    if (cardOption) cardOption.classList.add('selected');
    if (cashOption) cashOption.classList.remove('selected');
    if (cardSection) cardSection.style.display = 'block';
    if (hiddenInput) hiddenInput.value = 'Kredi / Banka Kartı (SSL İle Ödeme)';
  } else {
    if (cashOption) cashOption.classList.add('selected');
    if (cardOption) cardOption.classList.remove('selected');
    if (cardSection) cardSection.style.display = 'none';
    if (hiddenInput) hiddenInput.value = 'Kapıda Nakit Ödeme';
  }
}

// Format Credit Card Inputs & Visual Preview
function formatCardNumber(input) {
  let val = input.value.replace(/\D/g, '').substring(0, 16);
  let formatted = val.match(/.{1,4}/g)?.join(' ') || val;
  input.value = formatted;

  const preview = document.getElementById('card-num-preview');
  if (preview) {
    preview.textContent = formatted || '**** **** **** ****';
  }
}

function updateCardHolderPreview(input) {
  const preview = document.getElementById('card-holder-preview');
  if (preview) {
    preview.textContent = input.value.toUpperCase() || 'İSİM SOYİSİM';
  }
}

function formatCardExpiry(input) {
  let val = input.value.replace(/\D/g, '').substring(0, 4);
  if (val.length >= 3) {
    val = val.substring(0, 2) + '/' + val.substring(2);
  }
  input.value = val;

  const preview = document.getElementById('card-exp-preview');
  if (preview) {
    preview.textContent = val || 'MM/YY';
  }
}

function handlePlaceOrder(event) {
  event.preventDefault();
  const name = document.getElementById('order-name').value;
  const phone = document.getElementById('order-phone').value;
  const city = document.getElementById('order-city').value;
  const district = document.getElementById('order-district').value;
  const neighborhood = document.getElementById('order-neighborhood').value;
  const address = document.getElementById('order-address').value;
  const paymentMethod = document.getElementById('order-payment-method').value;
  const note = document.getElementById('order-note').value;

  const isCard = document.getElementById('pay-card').classList.contains('selected');

  if (isCard) {
    const cardNum = document.getElementById('card-number').value.replace(/\s/g, '');
    const cardHolder = document.getElementById('card-holder').value;
    const cardExpiry = document.getElementById('card-expiry').value;
    const cardCvc = document.getElementById('card-cvc').value;

    if (cardNum.length < 16 || !cardHolder || cardExpiry.length < 5 || cardCvc.length < 3) {
      showToast('Lütfen kart bilgilerinizi eksiksiz doldurun!', 'error');
      return;
    }
  }

  const totalPrice = cart.reduce((sum, i) => sum + ((Number(i.price) || 0) * (Number(i.quantity) || 1)), 0);

  // Format WhatsApp Order Summary
  let orderSummary = `*🐓 GALLUS MAMA & YUMURTA - YENİ SİPARİŞ*\n\n`;
  orderSummary += `👤 *Müşteri:* ${name}\n`;
  orderSummary += `📞 *Telefon:* ${phone}\n`;
  orderSummary += `📍 *İl / İlçe:* ${city} / ${district}\n`;
  orderSummary += `🏙️ *Mahalle:* ${neighborhood}\n`;
  orderSummary += `🏠 *Açık Adres:* ${address}\n`;
  orderSummary += `💳 *Ödeme Yöntemi:* ${paymentMethod}\n`;
  if (isCard) {
    const cardNumRaw = document.getElementById('card-number').value;
    const last4 = cardNumRaw.slice(-4);
    orderSummary += `🔒 *Kart Sonu:* **** ${last4}\n`;
  }
  if (note) orderSummary += `📝 *Not:* ${note}\n`;

  orderSummary += `\n*🛒 SİPARİŞ İÇERİĞİ:*\n`;
  cart.forEach(item => {
    orderSummary += `• ${item.name} (${item.quantity} Adet) - ${item.price * item.quantity} ₺\n`;
  });

  orderSummary += `\n💰 *TOPLAM TUTAR:* ${totalPrice.toLocaleString('tr-TR')} ₺`;

  const encodedMsg = encodeURIComponent(orderSummary);
  const waUrl = `https://wa.me/905516553637?text=${encodedMsg}`;

  // Clear cart
  cart = [];
  saveCartToStorage();
  closeCheckoutModal();

  showToast('Siparişiniz alındı & ödeme doğrulandı! WhatsApp sistemine yönlendiriliyorsunuz...', 'success');

  // Open WhatsApp with complete formatted order summary
  setTimeout(() => {
    window.open(waUrl, '_blank');
  }, 1200);
}

/* Toast Helper */
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${type === 'success' ? '✅' : '⚠️'}</span>
    <span>${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

// Global scope export for inline onclick attributes
window.openCartModal = openCartModal;
window.closeCartModal = closeCartModal;
window.openCheckoutModal = openCheckoutModal;
window.closeCheckoutModal = closeCheckoutModal;
window.addToCart = addToCart;
window.updateCartQuantity = updateCartQuantity;
window.removeFromCart = removeFromCart;
window.filterCategory = filterCategory;
window.scrollToSection = scrollToSection;
window.toggleMobileNav = toggleMobileNav;
window.selectPaymentMethod = selectPaymentMethod;
window.updateDistrictsDropdown = updateDistrictsDropdown;
