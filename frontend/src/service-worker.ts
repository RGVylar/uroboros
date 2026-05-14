/// <reference types="@sveltejs/kit" />
/// <reference lib="webworker" />

declare const self: ServiceWorkerGlobalScope;

// ── Install / Activate ───────────────────────────────────────────────────────
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));

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
