// The only JavaScript BookHop ships.
//
// It registers the service worker and does nothing else. No framework, no
// htmx, no polyfill, no analytics. Every route in slice S1 works with
// JavaScript disabled, so if this file never loads the product is unchanged
// except that the offline page is not cached.
//
// External rather than inline because backend's CSP is
// `script-src 'self' 'nonce-...'` with no 'unsafe-inline'
// (apps/core/middleware.py). A same-origin file satisfies 'self' and needs no
// nonce, which keeps the templates free of a server-injected attribute.
//
// Failure is silent on purpose: a student on a browser without service workers,
// or in a private window where registration throws, loses offline caching and
// nothing else. Logging a console error for a capability we treat as optional
// would be noise.
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function () {
    navigator.serviceWorker.register('/sw.js').catch(function () {});
  });
}
