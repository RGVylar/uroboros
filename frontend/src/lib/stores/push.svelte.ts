/**
 * Push notification management — Web Push (browser) + FCM (native Android via Capacitor).
 *
 * Unified interface regardless of platform:
 *   pushStore.isSupported      → true if push is available on this platform
 *   pushStore.permission       → 'default' | 'granted' | 'denied'
 *   pushStore.isSubscribed     → active subscription registered with backend
 *   await pushStore.subscribe()    → request permission + subscribe
 *   await pushStore.unsubscribe()  → remove subscription
 */

import { api } from '$lib/api';
import { browser } from '$app/environment';

/** True when running inside a Capacitor native app (Android / iOS). */
export const isNativeApp: boolean =
	browser && typeof (window as unknown as { Capacitor?: { isNative?: boolean } }).Capacitor?.isNative === 'boolean'
		? ((window as unknown as { Capacitor: { isNative: boolean } }).Capacitor.isNative ?? false)
		: false;

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

		if (isNativeApp) {
			// Native Android — use Capacitor Push Notifications
			_isSupported = true;
			try {
				const { PushNotifications } = await import('@capacitor/push-notifications');
				const result = await PushNotifications.checkPermissions();
				_permission = result.receive === 'granted' ? 'granted'
					: result.receive === 'denied' ? 'denied'
					: 'default';
				_isSubscribed = _permission === 'granted';
			} catch {
				_isSupported = false;
			}
			return;
		}

		// Web Push
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
		if (!_isSupported) return false;

		if (isNativeApp) {
			try {
				const { PushNotifications } = await import('@capacitor/push-notifications');
				const result = await PushNotifications.requestPermissions();
				if (result.receive !== 'granted') {
					_permission = 'denied';
					return false;
				}
				_permission = 'granted';

				await PushNotifications.register();

				return new Promise((resolve) => {
					PushNotifications.addListener('registration', async (tokenData) => {
						try {
							await api.post('/push/fcm-subscribe', { token: tokenData.value });
							_isSubscribed = true;
							resolve(true);
						} catch {
							resolve(false);
						}
					});
					PushNotifications.addListener('registrationError', () => resolve(false));
					// Timeout fallback
					setTimeout(() => resolve(false), 10_000);
				});
			} catch (e) {
				console.error('[push] native subscribe failed', e);
				return false;
			}
		}

		// Web Push
		if (!_registration) return false;

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
		if (isNativeApp) {
			try {
				await api.del('/push/fcm-subscribe');
				_isSubscribed = false;
			} catch (e) {
				console.error('[push] native unsubscribe failed', e);
			}
			return;
		}

		// Web Push
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
