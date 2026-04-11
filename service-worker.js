const CACHE_NAME = 'quant-radar-v2';
const STATIC_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './offline.html',
  './assets/pwa.png',
  './assets/ws.png',
  './assets/idx.png',
  './us_market/us_hub.html',
  './us_market/us_docs.html',
  './id_market/id_radar.html',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .catch((err) => {
        console.log('[SW] Cache addAll error:', err);
      })
  );
  self.skipWaiting();
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name !== CACHE_NAME)
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
  );
  self.clients.claim();
});

// Fetch event - cache-first strategy
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET' || !event.request.url.startsWith('http')) return;

  event.respondWith(
    // 1. COBA AMBIL DARI INTERNET DULU
    fetch(event.request)
      .then((networkResponse) => {
        // Kalau dapat data baru, simpan ke cache buat cadangan offline nanti
        if (networkResponse && networkResponse.status === 200) {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return networkResponse;
      })
      .catch(() => {
        // 2. KALAU INTERNET MATI (OFFLINE), BARU AMBIL DARI CACHE
        return caches.match(event.request).then((cachedResponse) => {
          if (cachedResponse) return cachedResponse;
          
          // 3. KALAU DI CACHE JUGA GA ADA, KASIH HALAMAN OFFLINE
          if (event.request.mode === 'navigate') {
            return caches.match('./offline.html');
          }
        });
      })
  );
});
