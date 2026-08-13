// pwa.js — Register service worker + handle deep links
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').then((reg) => {
      console.log('[SW] Registered:', reg.scope);
    }).catch((err) => {
      console.log('[SW] Registration failed:', err);
    });
  });
}

// Handle URL deep links  e.g. ?page=lecture&id=5
window.addEventListener('load', () => {
  const params = new URLSearchParams(window.location.search);
  const page = params.get('page');
  const id = params.get('id');
  if (page && window.showPage) {
    setTimeout(() => {
      showPage(page);
      if (id && page === 'lecture') openLecture(parseInt(id));
    }, 3500);
  }
});

// Install prompt (Add to Home Screen)
let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  // Show install banner after 30 seconds
  setTimeout(() => {
    if (deferredPrompt) showInstallBanner();
  }, 30000);
});

function showInstallBanner() {
  const banner = document.createElement('div');
  banner.id = 'install-banner';
  banner.innerHTML = `
    <div style="
      position:fixed;bottom:80px;left:16px;right:16px;z-index:9998;
      background:linear-gradient(135deg,#0f3d22,#1a6832);
      border:1px solid rgba(201,162,39,0.3);border-radius:16px;
      padding:14px 16px;display:flex;align-items:center;gap:12px;
      box-shadow:0 8px 30px rgba(0,0,0,0.4);
    ">
      <div style="font-size:28px">☪️</div>
      <div style="flex:1">
        <div style="font-weight:700;color:#f0f7f2;font-size:0.9rem">Install Makari TV</div>
        <div style="color:rgba(240,247,242,0.7);font-size:0.8rem">Add to Home Screen for offline access</div>
      </div>
      <button onclick="installApp()" style="
        background:#c9a227;color:#000;border-radius:8px;padding:8px 14px;
        font-weight:700;font-size:13px;border:none;cursor:pointer
      ">Install</button>
      <button onclick="document.getElementById('install-banner').remove()" style="
        background:none;color:rgba(240,247,242,0.5);border:none;cursor:pointer;font-size:18px
      ">×</button>
    </div>
  `;
  document.body.appendChild(banner);
}

async function installApp() {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  const { outcome } = await deferredPrompt.userChoice;
  deferredPrompt = null;
  document.getElementById('install-banner')?.remove();
}

window.addEventListener('appinstalled', () => {
  console.log('[PWA] App installed successfully');
  if (window.showToast) showToast('App installed! 🎉', 'success');
});
