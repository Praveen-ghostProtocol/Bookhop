{% load static %}// BookHop service worker — SYSTEM §4.27, ADR-001 §2.3.
//
// Served from / so its scope is the whole origin (web/views.py service_worker).
//
// It does three things and refuses to do a fourth:
//   1. precaches the shell: the stylesheet, the offline page, the manifest;
//   2. serves those from cache first, because they never change within a
//      version and a 3G round trip for a stylesheet is the student's money;
//   3. falls back to the offline page for a navigation that cannot be served.
//
// **NO OFFLINE WRITES, EVER.** ADR-001 §6 excludes them. There is no POST
// queue, no background sync, no retry-on-reconnect. A queued confirmation that
// the server never received would corrupt the one metric the pilot exists to
// measure (D-009), and a UI implying durability it does not have is a lie. So
// every non-GET request goes straight to the network and fails honestly.
//
// Cache-first is deliberately NOT applied to HTML pages other than /offline:
// SYSTEM §5.4 is explicit that the UI shows the last state the server
// confirmed. Serving a cached account or consent page would show a state that
// may have changed, with no as-of time, which is the stale-data defect
// students would not notice.

// THE CACHE NAME IS THE SHELL'S CONTENT, NOT A STRING SOMEBODY TYPED.
//
// This was `'bookhop-s1-1'`, and the comment two lines below claimed a stale
// asset could not outlive a deploy — which was true only while someone
// remembered to edit the constant. It failed the first time it was tested:
// an `app.css` change in S2 was invisible in the browser because this worker
// kept serving the precached copy, and a student with the PWA installed would
// have kept the old stylesheet indefinitely. CLAUDE.md rule 9: the claim and
// the check are one artefact, or they drift.
//
// `web/views.py shell_version()` hashes every file behind the list below, so
// changing any of them changes this name, `activate` deletes every other
// cache, and the new bytes are fetched. The list itself comes from the same
// place, so the precache set and the name it is stored under cannot disagree.
const VERSION = '{{ version }}';

const SHELL = [
{% for name in shell_static %}  '{% static name %}',
{% endfor %}{% for route in shell_routes %}  '{{ route }}'{% if not forloop.last %},{% endif %}
{% endfor %}];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(VERSION).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;

  // Anything that is not a plain GET is none of this worker's business.
  if (request.method !== 'GET') {
    return;
  }

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) {
    return;
  }

  // Shell assets: cache first. They are versioned by VERSION, so a stale one
  // cannot outlive a deploy.
  if (SHELL.indexOf(url.pathname) !== -1) {
    event.respondWith(
      caches.match(request).then((hit) => hit || fetch(request))
    );
    return;
  }

  // Navigations: network only, with the offline page as the fallback. No
  // cached HTML is ever served in its place.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match('/offline'))
    );
  }
});
