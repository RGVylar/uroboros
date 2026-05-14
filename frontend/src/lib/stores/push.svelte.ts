/**
 * Web Push subscription management.
 *
 * Usage:
 *   pushStore.isSupported      → browser supports push
 *   pushStore.permission       → 'default' | 'granted' | 'denied'
 *   pushStore.isSubscribed     → active subscription registered with backend
 *   await pushStore.subscribe()    → request permission + subscribe
 *   await pushStore.unsubscribe()  → remove subscription
 */

import { api } from '$lib/api';
import { browser } from '$app/environment';

// ── State ─────────────────────────────────────────────────────────────────────

let _isSupported = $state(false);
let _permission = $state<NotificationPermission>('default');
let _isSubscribed = $state(false);
let _registration = $state<ServiceWorkerRegistration | null>(null);

// ── Helpers ───────────────────────────────────────────────────────────────────

function urlBase64ToUint8Array(base64String: string): Uint8Array {
	const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
	const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
	const rawData = atob(base64);
	return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)));
}

async function getVapidPublicKey(): Promise<string> {
	const { key } = await api.get<{ key: string }>('/push/vapid-public-key');
	return key;
}

// ── Store ─────────────────────────────────────────────────────────────────────

export const pushStore = {
	get isSupported() { return _isSupported; },
	get permission() { return _permission; },
	get isSubscribed() { return _isSubscribed; },

	/** Call once on app start (from +layout.svelte) after auth is confirmed. */
	async init() {
		if (!browser) return;
		_isSupported = 'serviceWorker' in navigator && 'PushManager' in window;
		if (!_isSupported) return;

		_permission = Notification.permission;

		try {
			const reg = await navigator.serviceWorker.ready;
			_registration = reg;
			const existing = await reg.pushManager.getSubscription();
			_isSubscribed = existing !== null;
		} catch {
			_isSubscribed = false;
		}
	},

	/** Request permission and register a push subscription with the backend. */
	async subscribe(): Promise<boolean> {
		if (!_isSupported || !_registration) return false;

		const permission = await Notification.requestPermission();
		_permission = permission;
		if (permission !== 'granted') return false;

		try {
			const vapidKey = await getVapidPublicKey();
			const sub = await _registration.pushManager.subscribe({
				userVisibleOnly: true,
				applicationServerKey: urlBase64ToUint8Array(vapidKey),
			});

			const json = sub.toJSON();
			await api.post('/push/subscribe', {
				endpoint: sub.endpoint,
				p256dh: json.keys?.p256dh ?? '',
				auth: json.keys?.auth ?? '',
				user_agent: navigator.userAgent.slice(0, 255),
			});

			_isSubscribed = true;
			return true;
		} catch (e) {
			console.error('[push] subscribe failed', e);
			return false;
		}
	},

	/** Remove the subscription from browser and backend. */
	async unsubscribe(): Promise<void> {
		if (!_registration) return;
		try {
			const sub = await _registration.pushManager.getSubscription();
			if (sub) {
				await api.del('/push/subscribe');
				await sub.unsubscribe();
			}
			_isSubscribed = false;
		} catch (e) {
			console.error('[push] unsubscribe failed', e);
		}
	},

	/** Send a test notification (requires existing subscription). */
	async sendTest(): Promise<void> {
		await api.post('/push/test', {});
	},
};
