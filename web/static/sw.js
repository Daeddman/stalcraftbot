const CACHE_NAME='ph-v3';
const STATIC_ASSETS=[
  '/static/css/style.css',
  '/static/js/api.js',
  '/static/js/app.js',
];

self.addEventListener('install',e=>{
  e.waitUntil(
    caches.open(CACHE_NAME).then(c=>c.addAll(STATIC_ASSETS)).then(()=>self.skipWaiting())
  );
});

self.addEventListener('activate',e=>{
  e.waitUntil(
    caches.keys().then(keys=>Promise.all(
      keys.filter(k=>k!==CACHE_NAME).map(k=>caches.delete(k))
    )).then(()=>self.clients.claim())
  );
});

self.addEventListener('fetch',e=>{
  const url=new URL(e.request.url);
  // API — network only
  if(url.pathname.startsWith('/api/')||url.pathname.startsWith('/ws/'))return;
  // Icons — cache first, long TTL
  if(url.pathname.startsWith('/icons/')||url.pathname.startsWith('/icon-thumbs/')||url.pathname.startsWith('/custom-icons/')){
    e.respondWith(caches.open(CACHE_NAME).then(c=>c.match(e.request).then(r=>{
      if(r)return r;
      return fetch(e.request).then(resp=>{
        if(resp.ok)c.put(e.request,resp.clone());
        return resp;
      }).catch(()=>new Response('',{status:404}));
    })));
    return;
  }
  // Static assets — stale-while-revalidate
  if(url.pathname.startsWith('/static/')){
    e.respondWith(caches.open(CACHE_NAME).then(c=>c.match(e.request).then(cached=>{
      const fetched=fetch(e.request).then(resp=>{
        if(resp.ok)c.put(e.request,resp.clone());
        return resp;
      }).catch(()=>cached);
      return cached||fetched;
    })));
    return;
  }
  // Google Fonts — cache first
  if(url.hostname==='fonts.googleapis.com'||url.hostname==='fonts.gstatic.com'){
    e.respondWith(caches.open(CACHE_NAME).then(c=>c.match(e.request).then(r=>{
      if(r)return r;
      return fetch(e.request).then(resp=>{
        if(resp.ok)c.put(e.request,resp.clone());
        return resp;
      });
    })));
    return;
  }
});

