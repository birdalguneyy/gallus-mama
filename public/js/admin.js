/* ==========================================================================
   Gallus Mama - Admin Panel JavaScript
   ========================================================================== */

let adminToken = localStorage.getItem('gallus_admin_token') || '';
let categoriesList = [];
let productsList = [];
let activeAdminTab = 'products';

document.addEventListener('DOMContentLoaded', () => {
  checkAuth();
});

function getAuthHeaders() {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${adminToken}`
  };
}

async function checkAuth() {
  const loginOverlay = document.getElementById('login-overlay');
  const adminDashboard = document.getElementById('admin-dashboard');

  if (!adminToken) {
    loginOverlay.classList.add('open');
    adminDashboard.style.display = 'none';
    return;
  }

  try {
    const res = await fetch('/api/auth/check', {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    const data = await res.json();

    if (data.authenticated) {
      loginOverlay.classList.remove('open');
      adminDashboard.style.display = 'block';
      loadAdminDashboardData();
    } else {
      adminToken = '';
      localStorage.removeItem('gallus_admin_token');
      loginOverlay.classList.add('open');
      adminDashboard.style.display = 'none';
    }
  } catch (err) {
    console.error('Auth check error:', err);
    loginOverlay.classList.add('open');
    adminDashboard.style.display = 'none';
  }
}

async function handleLogin(event) {
  event.preventDefault();
  const passwordInput = document.getElementById('login-password');
  const password = passwordInput.value;

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password })
    });

    const data = await res.json();

    if (res.ok && data.token) {
      adminToken = data.token;
      localStorage.setItem('gallus_admin_token', adminToken);
      showToast('Giriş başarılı! Yönetim paneline aktarılıyorsunuz.', 'success');
      passwordInput.value = '';
      checkAuth();
    } else {
      showToast(data.error || 'Hatalı şifre! Tekrar deneyin.', 'error');
    }
  } catch (err) {
    showToast('Sunucu ile iletişim hatası.', 'error');
  }
}

function handleLogout() {
  fetch('/api/auth/logout', {
    method: 'POST',
    headers: getAuthHeaders()
  }).finally(() => {
    adminToken = '';
    localStorage.removeItem('gallus_admin_token');
    showToast('Başarıyla çıkış yapıldı.', 'success');
    checkAuth();
  });
}

async function loadAdminDashboardData() {
  await fetchCategories();
  await fetchProducts();
  await fetchSiteInfo();
  updateStats();
}

async function fetchCategories() {
  try {
    const res = await fetch('/api/categories');
    categoriesList = await res.json();
    renderCategoriesTable();
    populateCategoryDropdowns();
  } catch (err) {
    console.error('Error fetching categories:', err);
  }
}

async function fetchProducts() {
  try {
    const res = await fetch('/api/products');
    productsList = await res.json();
    renderProductsTable();
    updateStats();
  } catch (err) {
    console.error('Error fetching products:', err);
  }
}

async function fetchSiteInfo() {
  try {
    const res = await fetch('/api/info');
    const info = await res.json();
    if (info) {
      if (document.getElementById('info-form-hero-title')) document.getElementById('info-form-hero-title').value = info.heroTitle || '';
      if (document.getElementById('info-form-slogan')) document.getElementById('info-form-slogan').value = info.slogan || '';
      if (document.getElementById('info-form-hero-image')) document.getElementById('info-form-hero-image').value = info.heroImage || '';
      
      if (document.getElementById('info-form-delivery-regions')) document.getElementById('info-form-delivery-regions').value = info.deliveryRegions || '';

      if (document.getElementById('info-form-about-title')) document.getElementById('info-form-about-title').value = info.aboutTitle || '';
      if (document.getElementById('info-form-about')) document.getElementById('info-form-about').value = info.aboutText || '';
      if (document.getElementById('info-form-about-image')) document.getElementById('info-form-about-image').value = info.aboutImage || '';

      if (document.getElementById('info-form-whatsapp')) document.getElementById('info-form-whatsapp').value = info.whatsappUrl || '';
      if (document.getElementById('info-form-ig-mama')) document.getElementById('info-form-ig-mama').value = info.instagramGallusMamaUrl || '';
      if (document.getElementById('info-form-ig-yumurta')) document.getElementById('info-form-ig-yumurta').value = info.instagramGallusYumurtaUrl || '';
      if (document.getElementById('info-form-maps')) document.getElementById('info-form-maps').value = info.googleMapsUrl || '';
      if (document.getElementById('info-form-maps-embed')) document.getElementById('info-form-maps-embed').value = info.googleMapsEmbedUrl || '';

      if (document.getElementById('info-form-phone')) document.getElementById('info-form-phone').value = info.phone || '';
      if (document.getElementById('info-form-email')) document.getElementById('info-form-email').value = info.email || '';
      if (document.getElementById('info-form-address')) document.getElementById('info-form-address').value = info.address || '';
      if (document.getElementById('info-form-hours')) document.getElementById('info-form-hours').value = info.workingHours || '';
    }
  } catch (err) {
    console.error('Error fetching site info:', err);
  }
}

function updateStats() {
  document.getElementById('stat-products-count').textContent = productsList.length;
  document.getElementById('stat-categories-count').textContent = categoriesList.length;
  document.getElementById('stat-popular-count').textContent = productsList.filter(p => p.isPopular).length;
}

function switchAdminTab(tabName) {
  activeAdminTab = tabName;

  document.querySelectorAll('.category-tab').forEach(b => b.classList.remove('active'));
  document.getElementById(`tab-btn-${tabName}`).classList.add('active');

  document.getElementById('tab-section-products').style.display = tabName === 'products' ? 'block' : 'none';
  document.getElementById('tab-section-categories').style.display = tabName === 'categories' ? 'block' : 'none';
  document.getElementById('tab-section-info').style.display = tabName === 'info' ? 'block' : 'none';
}

/* Products Management */
function renderProductsTable() {
  const tbody = document.getElementById('admin-products-tbody');
  if (!tbody) return;

  if (productsList.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="text-center" style="padding: 30px; color: var(--color-text-muted);">
          Henüz ürün bulunmuyor. "Yeni Ürün Ekle" butonuna basarak ilk ürününüzü ekleyin.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = productsList.map(prod => {
    const category = categoriesList.find(c => c.id === prod.categoryId);
    const catName = category ? category.name : '—';
    const defaultImg = 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80';

    return `
      <tr>
        <td>
          <img src="${prod.imageUrl || defaultImg}" alt="${escapeHtml(prod.name)}" style="width: 50px; height: 50px; border-radius: var(--radius-sm); object-fit: cover;" onerror="this.src='${defaultImg}'">
        </td>
        <td>
          <strong style="color: var(--color-text-main); font-size: 1rem;">${escapeHtml(prod.name)}</strong>
          <div style="font-size: 0.8rem; color: var(--color-text-muted);">${escapeHtml(prod.description || '')}</div>
        </td>
        <td><span class="btn btn-secondary btn-sm" style="font-size: 0.75rem;">${escapeHtml(catName)}</span></td>
        <td><strong style="color: var(--color-accent); font-size: 1.1rem;">${Number(prod.price).toLocaleString('tr-TR')} ₺</strong></td>
        <td>
          <button class="btn btn-sm ${prod.isPopular ? 'btn-primary' : 'btn-secondary'}" onclick="toggleProductPopular('${prod.id}')">
            ${prod.isPopular ? '⭐ Evet' : '⚪ Hayır'}
          </button>
        </td>
        <td>
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-secondary btn-sm" onclick="editProduct('${prod.id}')">✏️ Düzenle</button>
            <button class="btn btn-danger btn-sm" onclick="deleteProduct('${prod.id}')">🗑️ Sil</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function openProductModal(editingProduct = null) {
  const modal = document.getElementById('product-modal');
  const title = document.getElementById('product-modal-title');
  const form = document.getElementById('product-form');

  populateCategoryDropdowns();

  if (editingProduct) {
    title.textContent = 'Ürün Düzenle';
    document.getElementById('product-edit-id').value = editingProduct.id;
    document.getElementById('product-form-name').value = editingProduct.name;
    document.getElementById('product-form-category').value = editingProduct.categoryId || '';
    document.getElementById('product-form-price').value = editingProduct.price;
    document.getElementById('product-form-image').value = editingProduct.imageUrl || '';
    document.getElementById('product-form-desc').value = editingProduct.description || '';
    document.getElementById('product-form-popular').checked = Boolean(editingProduct.isPopular);
  } else {
    title.textContent = 'Yeni Ürün Ekle';
    form.reset();
    document.getElementById('product-edit-id').value = '';
  }

  modal.classList.add('open');
}

function closeProductModal() {
  document.getElementById('product-modal').classList.remove('open');
}

function setPresetImg(url) {
  document.getElementById('product-form-image').value = url;
}

async function handleSaveProduct(event) {
  event.preventDefault();
  const id = document.getElementById('product-edit-id').value;
  const payload = {
    name: document.getElementById('product-form-name').value,
    categoryId: document.getElementById('product-form-category').value,
    price: document.getElementById('product-form-price').value,
    imageUrl: document.getElementById('product-form-image').value,
    description: document.getElementById('product-form-desc').value,
    isPopular: document.getElementById('product-form-popular').checked
  };

  const url = id ? `/api/products/${id}` : '/api/products';
  const method = id ? 'PUT' : 'POST';

  try {
    const res = await fetch(url, {
      method,
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      showToast(id ? 'Ürün güncellendi!' : 'Yeni ürün eklendi!', 'success');
      closeProductModal();
      fetchProducts();
    } else {
      const data = await res.json();
      showToast(data.error || 'İşlem başarısız.', 'error');
    }
  } catch (err) {
    showToast('Bağlantı hatası.', 'error');
  }
}

function editProduct(id) {
  const product = productsList.find(p => p.id === id);
  if (product) openProductModal(product);
}

async function deleteProduct(id) {
  if (!confirm('Bu ürünü silmek istediğinizden emin misiniz?')) return;

  try {
    const res = await fetch(`/api/products/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });

    if (res.ok) {
      showToast('Ürün silindi.', 'success');
      fetchProducts();
    } else {
      showToast('Ürün silinemedi.', 'error');
    }
  } catch (err) {
    showToast('Bağlantı hatası.', 'error');
  }
}

async function toggleProductPopular(id) {
  const product = productsList.find(p => p.id === id);
  if (!product) return;

  try {
    const res = await fetch(`/api/products/${id}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify({ isPopular: !product.isPopular })
    });

    if (res.ok) {
      showToast('Popülerlik durumu güncellendi.', 'success');
      fetchProducts();
    }
  } catch (err) {
    showToast('Güncelleme hatası.', 'error');
  }
}

/* Categories Management */
function populateCategoryDropdowns() {
  const select = document.getElementById('product-form-category');
  if (!select) return;

  select.innerHTML = '<option value="">-- Kategori Seçin --</option>' +
    categoriesList.map(c => `<option value="${c.id}">${c.icon || '🏷️'} ${escapeHtml(c.name)}</option>`).join('');
}

function renderCategoriesTable() {
  const tbody = document.getElementById('admin-categories-tbody');
  if (!tbody) return;

  if (categoriesList.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="4" class="text-center" style="padding: 30px; color: var(--color-text-muted);">
          Henüz kategori bulunmuyor.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = categoriesList.map(cat => `
    <tr>
      <td><span style="font-size: 1.6rem;">${cat.icon || '🏷️'}</span></td>
      <td><strong style="font-size: 1rem; color: var(--color-text-main);">${escapeHtml(cat.name)}</strong></td>
      <td><span style="color: var(--color-text-muted); font-size: 0.9rem;">${escapeHtml(cat.description || '—')}</span></td>
      <td>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-secondary btn-sm" onclick="editCategory('${cat.id}')">✏️ Düzenle</button>
          <button class="btn btn-danger btn-sm" onclick="deleteCategory('${cat.id}')">🗑️ Sil</button>
        </div>
      </td>
    </tr>
  `).join('');
}

function openCategoryModal(editingCategory = null) {
  const modal = document.getElementById('category-modal');
  const title = document.getElementById('category-modal-title');
  const form = document.getElementById('category-form');

  if (editingCategory) {
    title.textContent = 'Kategori Düzenle';
    document.getElementById('category-edit-id').value = editingCategory.id;
    document.getElementById('category-form-name').value = editingCategory.name;
    document.getElementById('category-form-icon').value = editingCategory.icon || '🏷️';
    document.getElementById('category-form-desc').value = editingCategory.description || '';
  } else {
    title.textContent = 'Yeni Kategori Ekle';
    form.reset();
    document.getElementById('category-edit-id').value = '';
    document.getElementById('category-form-icon').value = '🏷️';
  }

  modal.classList.add('open');
}

function closeCategoryModal() {
  document.getElementById('category-modal').classList.remove('open');
}

async function handleSaveCategory(event) {
  event.preventDefault();
  const id = document.getElementById('category-edit-id').value;
  const payload = {
    name: document.getElementById('category-form-name').value,
    icon: document.getElementById('category-form-icon').value,
    description: document.getElementById('category-form-desc').value
  };
  const url = id ? `/api/categories/${id}` : '/api/categories';
  const method = id ? 'PUT' : 'POST';

  try {
    const res = await fetch(url, {
      method,
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      showToast(id ? 'Kategori güncellendi!' : 'Yeni kategori eklendi!', 'success');
      closeCategoryModal();
      fetchCategories();
    } else {
      const data = await res.json();
      showToast(data.error || 'Hata oluştu.', 'error');
    }
  } catch (err) {
    showToast('Bağlantı hatası.', 'error');
  }
}

function editCategory(id) {
  const category = categoriesList.find(c => c.id === id);
  if (category) openCategoryModal(category);
}

async function deleteCategory(id) {
  if (!confirm('Bu kategoriyi silmek istediğinizden emin misiniz?')) return;

  try {
    const res = await fetch(`/api/categories/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });

    if (res.ok) {
      showToast('Kategori silindi.', 'success');
      fetchCategories();
      fetchProducts();
    } else {
      showToast('Kategori silinemedi.', 'error');
    }
  } catch (err) {
    showToast('Bağlantı hatası.', 'error');
  }
}

/* Site Content Management */
async function handleSaveInfo(event) {
  event.preventDefault();
  const payload = {
    heroTitle: document.getElementById('info-form-hero-title').value,
    slogan: document.getElementById('info-form-slogan').value,
    heroImage: document.getElementById('info-form-hero-image').value,
    deliveryRegions: document.getElementById('info-form-delivery-regions').value,
    aboutTitle: document.getElementById('info-form-about-title').value,
    aboutText: document.getElementById('info-form-about').value,
    aboutImage: document.getElementById('info-form-about-image').value,
    whatsappUrl: document.getElementById('info-form-whatsapp').value,
    instagramGallusMamaUrl: document.getElementById('info-form-ig-mama').value,
    instagramGallusYumurtaUrl: document.getElementById('info-form-ig-yumurta').value,
    googleMapsUrl: document.getElementById('info-form-maps').value,
    googleMapsEmbedUrl: document.getElementById('info-form-maps-embed').value,
    phone: document.getElementById('info-form-phone').value,
    email: document.getElementById('info-form-email').value,
    address: document.getElementById('info-form-address').value,
    workingHours: document.getElementById('info-form-hours').value
  };

  try {
    const res = await fetch('/api/info', {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      showToast('Tüm site içerikleri, teslimat bölgeleri ve bağlantıları başarıyla güncellendi!', 'success');
    } else {
      showToast('Güncelleme başarısız.', 'error');
    }
  } catch (err) {
    showToast('Bağlantı hatası.', 'error');
  }
}

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
