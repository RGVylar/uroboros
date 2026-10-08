/// <reference types="@sveltejs/kit" />
/// <reference lib="webworker" />

import { build, files, version } from '$service-worker';

declare const self: ServiceWorkerGlobalScope;

// ── App shell offline ────────────────────────────────────────────────────────
// Durante los partidos de fútbol los operadores bloquean la IP de Cloudflare y
// no llega ni el HTML: sin esta caché la PWA ni siquiera abre. Guardamos el
// bundle de esta versión y el index.html (la SPA sirve el mismo para todo).
const CACHE = `uro-shell-${version}`;
const SHELL = '/';
const ASSETS = [...build, ...files, SHELL];
const ASSET_SET = new Set(ASSETS);
// Lo que tarda en rendirse la red antes de abrir la copia guardada: un
// bloqueo a veces no rechaza la conexión, la deja colgada.
const NAV_TIMEOUT_MS = 4000;

// ── Install / Activate ───────────────────────────────────────────────────────
self.addEventListener('install', (e) => {
	e.waitUntil(
		caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting())
	);
});
self.addEventListener('activate', (e) => {
	e.waitUntil(
		caches.keys()
			.then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
			.then(() => self.clients.claim())
	);
});

// ── Fetch ────────────────────────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
	const req = event.request;
	if (req.method !== 'GET') return;
	const url = new URL(req.url);
	// La API (y la landing que sirve el backend) van siempre a la red: su
	// modo sin conexión lo llevan api.ts y la cola.
	if (url.origin !== self.location.origin) return;
	if (url.pathname.startsWith('/api') || url.pathname.startsWith('/unete')) return;

	if (req.mode === 'navigate') {
		event.respondWith(navigate(req));
		return;
	}
	if (ASSET_SET.has(url.pathname)) {
		event.respondWith(caches.match(url.pathname).then((hit) => hit ?? fetch(req)));
	}
});

// Red primero (así cada despliegue se ve al momento); si no hay red o tarda
// demasiado, el index.html guardado.
async function navigate(req: Request): Promise<Response> {
	const cached = () => caches.match(SHELL).then((hit) => hit ?? Response.error());
	try {
		const res = await Promise.race([
			fetch(req),
			new Promise<never>((_, reject) => setTimeout(() => reject(new Error('timeout')), NAV_TIMEOUT_MS)),
		]);
		// Un 502 de Cloudflare con el servidor caído tampoco sirve para abrir la app.
		if (res.status >= 500) return cached();
		return res;
	} catch {
		return cached();
	}
}

// ── Push handler ─────────────────────────────────────────────────────────────
self.addEventListener('push', (event) => {
	let data: { title?: string; body?: string; url?: string; icon?: string } = {};
	try {
		data = event.data?.json() ?? {};
	} catch {
		data = { title: 'uroboros', body: event.data?.text() ?? '' };
	}

	const title = data.title ?? 'uroboros';
	const options: NotificationOptions = {
		body: data.body ?? '',
		icon: data.icon ?? '/icon-192.png',
		badge: '/icon-96.png',
		data: { url: data.url ?? '/' },
		// Vibrate: short double-tap
		vibrate: [100, 50, 100],
	};

	event.waitUntil(self.registration.showNotification(title, options));
});

// ── Notification click → open / focus the app ────────────────────────────────
self.addEventListener('notificationclick', (event) => {
	event.notification.close();
	const url = (event.notification.data?.url as string) ?? '/';

	event.waitUntil(
		self.clients
			.matchAll({ type: 'window', includeUncontrolled: true })
			.then((clients) => {
				// If the app is already open, focus it and navigate
				for (const client of clients) {
					if ('focus' in client) {
						client.focus();
						if ('navigate' in client) (client as WindowClient).navigate(url);
						return;
					}
				}
				// Otherwise open a new window
				return self.clients.openWindow(url);
			})
	);
});
