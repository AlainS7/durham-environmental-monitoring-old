// Hot Durham PWA Service Worker
// Provides offline functionality and caching for mobile dashboard

const CACHE_NAME = 'hot-durham-v1.0.0';
const STATIC_CACHE = 'hot-durham-static-v1';
const DATA_CACHE = 'hot-durham-data-v1';

// Assets to cache for offline use
const STATIC_ASSETS = [
  '/mobile',
  '/static/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
  'https://cdn.jsdelivr.net/npm/chart.js',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
];

// API endpoints to cache
const API_ENDPOINTS = [
  '/api/public/health-index',
  '/api/public/air-quality',
  '/api/public/weather',
  '/api/public/trends'
];

// Install Service Worker
self.addEventListener('install', (event) => {
  console.log('[SW] Installing Service Worker');
  
  event.waitUntil(
    Promise.all([
      // Cache static assets
      caches.open(STATIC_CACHE).then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      }),
      
      // Pre-cache API data
      caches.open(DATA_CACHE).then((cache) => {
        console.log('[SW] Pre-caching API data');
        return Promise.all(
          API_ENDPOINTS.map(url => {
            return fetch(url)
              .then(response => {
                if (response.status === 200) {
                  cache.put(url, response.clone());
                }
                return response;
              })
              .catch(err => {
                console.log(`[SW] Failed to pre-cache ${url}:`, err);
              });
          })
        );
      })
    ]).then(() => {
      console.log('[SW] Installation complete');
      return self.skipWaiting();
    })
  );
});

// Activate Service Worker
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating Service Worker');
  
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          // Delete old caches
          if (cacheName !== STATIC_CACHE && cacheName !== DATA_CACHE) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('[SW] Activation complete');
      return self.clients.claim();
    })
  );
});

// Fetch Event Handler
self.addEventListener('fetch', (event) => {
  const requestUrl = new URL(event.request.url);
  
  // Handle API requests with cache-first strategy for offline support
  if (requestUrl.pathname.startsWith('/api/public/')) {
    event.respondWith(handleApiRequest(event.request));
    return;
  }
  
  // Handle static assets with cache-first strategy
  if (STATIC_ASSETS.some(asset => event.request.url.includes(asset))) {
    event.respondWith(handleStaticRequest(event.request));
    return;
  }
  
  // Handle navigation requests
  if (event.request.mode === 'navigate') {
    event.respondWith(handleNavigationRequest(event.request));
    return;
  }
  
  // Default: network first, cache fallback
  event.respondWith(
    fetch(event.request).catch(() => {
      return caches.match(event.request);
    })
  );
});

// Handle API requests with intelligent caching
async function handleApiRequest(request) {
  const url = request.url;
  
  try {
    // Try network first
    const networkResponse = await fetch(request);
    
    if (networkResponse.status === 200) {
      // Update cache with fresh data
      const cache = await caches.open(DATA_CACHE);
      cache.put(url, networkResponse.clone());
      
      // Add timestamp to response headers
      const response = new Response(networkResponse.body, {
        status: networkResponse.status,
        statusText: networkResponse.statusText,
        headers: {
          ...networkResponse.headers,
          'sw-cache-timestamp': Date.now()
        }
      });
      
      return response;
    }
    
    // If network fails, try cache
    return getCachedResponse(url);
    
  } catch (error) {
    console.log(`[SW] Network failed for ${url}, using cache`);
    return getCachedResponse(url);
  }
}

// Handle static asset requests
async function handleStaticRequest(request) {
  const cachedResponse = await caches.match(request);
  
  if (cachedResponse) {
    return cachedResponse;
  }
  
  // If not in cache, try network and cache the result
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.status === 200) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.log('[SW] Failed to fetch static asset:', request.url);
    throw error;
  }
}

// Handle navigation requests (SPA routing)
async function handleNavigationRequest(request) {
  try {
    // Try network first
    const networkResponse = await fetch(request);
    return networkResponse;
  } catch (error) {
    // If offline, serve cached mobile dashboard
    const cachedResponse = await caches.match('/mobile');
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Fallback offline page
    return new Response(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>Hot Durham - Offline</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
          body { 
            font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
            text-align: center; 
            padding: 2rem; 
            background: #f8f9fa; 
          }
          .offline-content { 
            max-width: 400px; 
            margin: 0 auto; 
            background: white; 
            padding: 2rem; 
            border-radius: 12px; 
            box-shadow: 0 2px 12px rgba(0,0,0,0.1);
          }
          .icon { 
            font-size: 3rem; 
            color: #FF5722; 
            margin-bottom: 1rem; 
          }
          .title { 
            font-size: 1.5rem; 
            font-weight: 700; 
            color: #2E7D32; 
            margin-bottom: 1rem; 
          }
          .message { 
            color: #666; 
            line-height: 1.5; 
            margin-bottom: 1.5rem; 
          }
          .retry-btn { 
            background: #2E7D32; 
            color: white; 
            border: none; 
            padding: 0.75rem 1.5rem; 
            border-radius: 8px; 
            cursor: pointer; 
            font-weight: 600; 
          }
        </style>
      </head>
      <body>
        <div class="offline-content">
          <div class="icon">📡</div>
          <div class="title">You're Offline</div>
          <div class="message">
            Hot Durham requires an internet connection to fetch current air quality data. 
            Please check your connection and try again.
          </div>
          <button class="retry-btn" onclick="window.location.reload()">
            Try Again
          </button>
        </div>
      </body>
      </html>
    `, {
      headers: { 'Content-Type': 'text/html' }
    });
  }
}

// Get cached response with fallback
async function getCachedResponse(url) {
  const cache = await caches.open(DATA_CACHE);
  const cachedResponse = await cache.match(url);
  
  if (cachedResponse) {
    // Add cache indicator to response
    const data = await cachedResponse.json();
    data._cached = true;
    data._cacheTime = cachedResponse.headers.get('sw-cache-timestamp');
    
    return new Response(JSON.stringify(data), {
      status: 200,
      statusText: 'OK (Cached)',
      headers: {
        'Content-Type': 'application/json',
        'sw-cache-status': 'hit'
      }
    });
  }
  
  // Return offline data structure if no cache available
  return new Response(JSON.stringify({
    error: 'Offline - No cached data available',
    offline: true,
    message: 'Please connect to the internet to get current data'
  }), {
    status: 503,
    statusText: 'Service Unavailable',
    headers: { 'Content-Type': 'application/json' }
  });
}

// Background sync for data updates
self.addEventListener('sync', (event) => {
  if (event.tag === 'background-sync-data') {
    console.log('[SW] Background sync triggered');
    event.waitUntil(updateDataCache());
  }
});

// Update data cache in background
async function updateDataCache() {
  const cache = await caches.open(DATA_CACHE);
  
  const updatePromises = API_ENDPOINTS.map(async (url) => {
    try {
      const response = await fetch(url);
      if (response.status === 200) {
        await cache.put(url, response.clone());
        console.log(`[SW] Updated cache for ${url}`);
      }
    } catch (error) {
      console.log(`[SW] Failed to update cache for ${url}:`, error);
    }
  });
  
  await Promise.all(updatePromises);
  console.log('[SW] Background data sync complete');
}

// Push notification handler
self.addEventListener('push', (event) => {
  if (!event.data) return;
  
  const data = event.data.json();
  
  const options = {
    body: data.body || 'Air quality alert for your area',
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/badge-96x96.png',
    vibrate: [200, 100, 200],
    data: {
      url: data.url || '/mobile',
      timestamp: Date.now()
    },
    actions: [
      {
        action: 'view',
        title: 'View Details',
        icon: '/static/icons/action-view.png'
      },
      {
        action: 'dismiss',
        title: 'Dismiss',
        icon: '/static/icons/action-dismiss.png'
      }
    ],
    requireInteraction: data.important || false,
    silent: data.silent || false
  };
  
  event.waitUntil(
    self.registration.showNotification(data.title || 'Hot Durham Alert', options)
  );
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  
  const action = event.action;
  const data = event.notification.data;
  
  if (action === 'view' || !action) {
    // Open or focus the app
    event.waitUntil(
      clients.matchAll({ type: 'window' }).then((clientList) => {
        // If app is already open, focus it
        for (const client of clientList) {
          if (client.url.includes('/mobile') && 'focus' in client) {
            return client.focus();
          }
        }
        
        // Otherwise open new window
        if (clients.openWindow) {
          return clients.openWindow(data.url || '/mobile');
        }
      })
    );
  }
  
  // Action: dismiss - do nothing (notification already closed)
});

// Message handler for app-to-SW communication
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'GET_CACHE_STATUS') {
    event.ports[0].postMessage({
      type: 'CACHE_STATUS',
      caches: {
        static: STATIC_CACHE,
        data: DATA_CACHE
      }
    });
  }
  
  if (event.data && event.data.type === 'FORCE_UPDATE') {
    event.waitUntil(updateDataCache());
  }
});

console.log('[SW] Service Worker loaded successfully');
