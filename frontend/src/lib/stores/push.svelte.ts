/**
 * Push notification management — unified interface for browser (Web Push) and native app (local notifications).
 *
 *   pushStore.isSupported   → true if notifications available on this platform
 *   pushStore.permission    → 'default' | 'granted' | 'denied'
 *   pushStore.isSubscribed  → user has active notifications enabled
 *   await pushStore.subscribe()    → request permission + activate
 *   await pushStore.unsubscribe()  → disable notifications
 *   await pushStore.sendTest()     → fire a test notification
 *   await pushStore.reschedule()   → re-schedule local notifications after prefs change (native only)
 */

import { Capacitor } from '@capacitor/core';
import { api } from '$lib/api';
import { browser } from '$app/environment';
import {
	scheduleNativeNotifications,
	cancelNativeNotifications,
	testNativeNotification,
} from '$lib/services/nativeNotifications';

/**
 * True when running inside a Capacitor native app (Android / iOS).
 * Checks both the official API and the legacy window bridge as a fallback.
 */
export const isNativeApp: boolean = (() => {
	try {
		if (Capacitor.isNativePlatform()) return true;
	} catch { /* ignore */ }
	// Fallback: check the raw bridge object (works in older Capacitor versions)
	try {
		const cap = (typeof window !== 'undefined') && (window as unknown as Record<string, unknown>)['Capacitor'];
		if (cap && typeof (cap as Record<string, unknown>)['isNative'] === 'boolean') {
			return (cap as Record<string, unknown>)['isNative'] as boolean;
		}
		if (cap && typeof (cap as Record<string, unknown>)['isNativePlatform'] === 'function') {
			return ((cap as Record<string, unknown>)['isNativePlatform'] as () => boolean)();
		}
	} catch { /* ignore */ }
	return false;
})();

// ── State ─────────────────────────────────────────────────────────────────────

let _isSupported = $state(false);
let _permission = $state<NotificationPermission>('default');
let _isSubscribed = $state(false);
let _registration = $state<ServiceWorkerRegistration | null>(null);

// ── Helpers (web push only) ───────────────────────────────────────────────────

function urlBase64ToUint8Array(base64String: string): Uint8Array {
	const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
	const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
	const rawData = atob(base64);
	return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)));
}

async function getVapidKey(): Promise<string> {
	const { key } = await api.get<{ key: string }>('/push/vapid-public-key');
	return key;
}

// ── Store ─────────────────────────────────────────────────────────────────────

export const pushStore = {
	get isSupported() { return _isSupported; },
	get permission()  { return _permission;  },
	get isSubscribed() { return _isSubscribed; },

	/** Call once on app start after auth is confirmed. */
	async init() {
		if (!browser) return;

		if (isNativeApp) {
			_isSupported = true;
			try {
				const { LocalNotifications } = await import('@capacitor/local-notifications');
				const perm = await LocalNotifications.checkPermissions();
				_permission  = perm.display === 'granted' ? 'granted'
				             : perm.display === 'denied'  ? 'denied'
				             : 'default';
				_isSubscribed = _permission === 'granted';

				// Re-schedule on every app open (keeps recurring notifications alive)
				if (_isSubscribed) await scheduleNativeNotifications();
			} catch {
				_isSupported = false;
			}
			return;
		}

		// ── Web Push ──
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

	/** Request permission and activate push notifications. */
	async subscribe(): Promise<boolean> {
		if (!_isSupported) return false;

		if (isNativeApp) {
			const ok = await scheduleNativeNotifications();
			if (ok) {
				_permission   = 'granted';
				_isSubscribed = true;
			} else {
				_permission = 'denied';
			}
			return ok;
		}

		// ── Web Push ──
		if (!_registration) return false;
		const permission = await Notification.requestPermission();
		_permission = permission;
		if (permission !== 'granted') return false;

		try {
			const vapidKey = await getVapidKey();
			const sub = await _registration.pushManager.subscribe({
				userVisibleOnly: true,
				applicationServerKey: urlBase64ToUint8Array(vapidKey),
			});
			const json = sub.toJSON();
			await api.post('/push/subscribe', {
				endpoint: sub.endpoint,
				p256dh:   json.keys?.p256dh ?? '',
				auth:     json.keys?.auth   ?? '',
				user_agent: navigator.userAgent.slice(0, 255),
			});
			_isSubscribed = true;
			return true;
		} catch (e) {
			console.error('[push] web subscribe failed', e);
			return false;
		}
	},

	/** Disable and remove all push subscriptions. */
	async unsubscribe(): Promise<void> {
		if (isNativeApp) {
			await cancelNativeNotifications();
			_isSubscribed = false;
			return;
		}

		// ── Web Push ──
		if (!_registration) return;
		try {
			const sub = await _registration.pushManager.getSubscription();
			if (sub) {
				await api.del('/push/subscribe');
				await sub.unsubscribe();
			}
			_isSubscribed = false;
		} catch (e) {
			console.error('[push] web unsubscribe failed', e);
		}
	},

	/** Re-schedule local notifications after prefs change (native only, no-op on web). */
	async reschedule(): Promise<void> {
		if (isNativeApp && _isSubscribed) {
			await scheduleNativeNotifications();
		}
	},

	/** Send a test notification. */
	async sendTest(): Promise<void> {
		if (isNativeApp) {
			await testNativeNotification();
			return;
		}
		await api.post('/push/test', {});
	},
};
