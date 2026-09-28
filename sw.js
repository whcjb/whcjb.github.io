// Service Worker —— 已停用（kill switch）
//
// 原先这个 SW 预缓存 /assets/cuv.json（3.3MB）。但 _includes/head.html 从
// 2026-05-08 起在每次页面加载时注销所有 SW 并清空 caches，而站点又在 footer
// 与 mhenry 的三个 layout 里重新注册，形成「清空 → 重装 → 重下 3.3MB」的循环，
// iOS Safari 因此反复弹出「增加储存空间大小？」。
//
// 注册端已全部关闭（_config.yml 的 service-worker: false）。这个文件保留为
// 自注销版本：设备上仍装着旧 SW 的，在它下次拉取 /sw.js 更新时自行清缓存并注销。
// cuv.json 改走普通 HTTP 缓存（GitHub Pages 带 ETag，命中即 304）。

self.addEventListener('install', function() {
    self.skipWaiting();
});

self.addEventListener('activate', function(e) {
    e.waitUntil(
        caches.keys()
            .then(function(keys) {
                return Promise.all(keys.map(function(k) { return caches.delete(k); }));
            })
            .then(function() { return self.registration.unregister(); })
            .then(function() { return self.clients.matchAll(); })
            .then(function(clients) {
                clients.forEach(function(c) { c.navigate(c.url); });
            })
    );
});
