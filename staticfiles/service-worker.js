const CACHE_NAME = 'schoolsaas-v6';
const urlsToCache = [
  '/',
  '/static/css/modern-dashboard.css',
  '/static/js/global-messages.js',
  '/static/js/pwa-install.js',
  '/static/manifest.json',
  '/static/images/icon-192x192.png',
  '/static/images/icon-512x512.png',
  '/offline/'
];

// Install event - cache all static assets
self.addEventListener('install', event => {
  console.log('Service Worker: Installing...');
  
  // Skip waiting to activate the new service worker immediately
  self.skipWaiting();
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        // Add each URL to cache one by one to prevent failing the entire cache if one fails
        const cachePromises = urlsToCache.map(url => {
          return cache.add(url).catch(error => {
            console.error(`Failed to cache ${url}:`, error);
          });
        });
        return Promise.all(cachePromises);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('Service Worker: Activating...');
  
  // Take control of all pages under this service worker's scope immediately
  event.waitUntil(clients.claim());
  
  // Remove old caches
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== CACHE_NAME) {
            console.log('Service Worker: Clearing Old Cache');
            return caches.delete(cache);
          }
        })
      );
    })
  );
  
  return self.clients.claim();
});

// Fetch event - serve from cache, falling back to network
self.addEventListener('fetch', event => {
  // Skip non-GET requests and cross-origin requests
  if (event.request.method !== 'GET' || !event.request.url.startsWith(self.location.origin)) {
    return;
  }
  
  // Handle navigation requests for SPA
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // If we got a valid response, cache and return it
          if (response && response.status === 200) {
            const responseToCache = response.clone();
            caches.open(CACHE_NAME)
              .then(cache => cache.put(event.request, responseToCache));
            return response;
          }
          // If not, try to serve from cache
          return caches.match('/offline/');
        })
        .catch(() => {
          // If both network and cache fail, show the offline page
          return caches.match('/offline/');
        })
    );
    return;
  }
  
  // For all other GET requests, try cache first, then network
  event.respondWith(
    caches.match(event.request)
      .then(cachedResponse => {
        // Return cached response if found
        if (cachedResponse) {
          return cachedResponse;
        }
        
        // Otherwise, fetch from network
        return fetch(event.request)
          .then(response => {
            // Check if we received a valid response
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }
            
            // Clone the response for caching
            const responseToCache = response.clone();
            
            // Cache the response
            caches.open(CACHE_NAME)
              .then(cache => cache.put(event.request, responseToCache));
            
            return response;
          });
      })
      .catch(error => {
        console.error('Fetch failed; returning offline page.', error);
        // For HTML requests, return the offline page
        if (event.request.headers.get('accept').includes('text/html')) {
          return caches.match('/offline/');
        }
      })
  );
});

// Listen for message event (can be used to update the service worker)
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
