// Service Worker — 缓存圣经经文数据（cuv.json）
// 更新 cuv.json 时将版本号改为 v2、v3… 即可清除旧缓存
var CACHE_NAME = 'mhenry-cuv-v1';
var CUV_PATH   = '/assets/cuv.json';

// 安装：预缓存 cuv.json（后台静默下载，不阻塞页面）
self.addEventListener('install', function(e) {
    e.waitUntil(
        caches.open(CACHE_NAME).then(function(cache) {
            return cache.add(CUV_PATH);
        })
    );
    self.skipWaiting();
});

// 激活：清理旧版本缓存
self.addEventListener('activate', function(e) {
    e.waitUntil(
        caches.keys().then(function(keys) {
            return Promise.all(
                keys.filter(function(k) { return k !== CACHE_NAME; })
                    .map(function(k) { return caches.delete(k); })
            );
        })
    );
    self.clients.claim();
});

// 拦截请求：只处理 cuv.json，其余请求正常走网络
self.addEventListener('fetch', function(e) {
    if (e.request.url.indexOf('/assets/cuv.json') === -1) return;

    e.respondWith(
        caches.match(e.request).then(function(cached) {
            if (cached) return cached;
            return fetch(e.request).then(function(response) {
                return caches.open(CACHE_NAME).then(function(cache) {
                    cache.put(e.request, response.clone());
                    return response;
                });
            });
        })
    );
});
