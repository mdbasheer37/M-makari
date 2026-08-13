// Makari Islamic TV — Service Worker
// CACHE_NAME is versioned so a new deploy can invalidate old cached assets —
// bump this string whenever frontend assets change (or wire it up to a
// build-time hash if you add a build step).
const CACHE_VERSION = 'v2';
const CACHE_NAME = `makari-tv-${CACHE_VERSION}`;
const OFFLINE_URL = '/index.html';

const STATIC_ASSETS = [
  '/manifest.json',
  'https://fonts.googleapis.com/css2?family=Amiri:ital,wght@0,400;0,700;1,400&family=Outfit:wght@300;400;500;600;700;800&display=swap',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css',
];

// Install
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate — drop every cache that isn't the current version (including
// the app-download cache from a previous major version, but NOT the
// user's offline lecture downloads, which live in a separate 'makari-
// downloads-*' cache and must survive app updates).
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== CACHE_NAME && !k.startsWith('makari-downloads'))
          .map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// Fetch
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // API requests — always network, never cached, so content is always fresh.
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request).catch(() =>
        new Response(JSON.stringify({ error: 'Offline', message: 'No internet connection' }), {
          headers: { 'Content-Type': 'application/json' },
          status: 503,
        })
      )
    );
    return;
  }

  // HTML navigations (the app shell) — network-first so a new deploy is
  // picked up immediately; only fall back to the cached shell when
  // genuinely offline. This is what actually fixes "stale app after
  // deploy" — cache-first here would keep serving yesterday's index.html
  // forever.
  if (request.mode === 'navigate' || (request.method === 'GET' && request.headers.get('accept')?.includes('text/html'))) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          return response;
        })
        .catch(() => caches.match(request).then((cached) => cached || caches.match(OFFLINE_URL)))
    );
    return;
  }

  // Media files — cache first (large, unlikely to change after upload)
  if (url.pathname.startsWith('/media/')) {
    event.respondWith(
      caches.match(request).then((cached) => cached || fetch(request).then((response) => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        return response;
      }))
    );
    return;
  }

  // Other static assets (CSS/JS/fonts/icons) — cache first, network fallback,
  // with the cache refreshed in the background so updates still arrive.
  event.respondWith(
    caches.match(request).then((cached) => {
      const networkFetch = fetch(request).then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      }).catch(() => cached);
      return cached || networkFetch;
    })
  );
});

// Push Notifications
// NOTE: this handler will only ever fire if the browser has an active
// Push subscription, which requires a VAPID key pair and a backend
// endpoint to store subscriptions (e.g. POST /api/notifications/subscribe)
// plus a server-side push sender (e.g. via the `pywebpush` library or
// Firebase Cloud Messaging). Neither exists in this codebase yet — see
// README.md. Until that's added, all in-app notifications (bell icon,
// /api/notifications) work as normal; this is only for OS-level push
// notifications when the app is closed.
self.addEventListener('push', (event) => {
  const data = event.data?.json() || {};
  const options = {
    body: data.body || 'New content available on Makari Islamic TV',
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-72.png',
    vibrate: [200, 100, 200],
    data: { url: data.url || '/' },
    actions: [
      { action: 'open', title: 'Open', icon: '/icons/icon-72.png' },
      { action: 'dismiss', title: 'Dismiss' },
    ],
  };
  event.waitUntil(
    self.registration.showNotification(data.title || 'Makari Islamic TV', options)
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  if (event.action === 'open' || !event.action) {
    event.waitUntil(
      clients.openWindow(event.notification.data?.url || '/')
    );
  }
});
