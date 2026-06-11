// Connectivity store — tracks whether the backend is reachable.
// Updated by api.ts on every request. The layout reads it to show a banner.

import { Capacitor } from '@capacitor/core';

const BASE = Capacitor.isNativePlatform()
	? (import.meta.env.VITE_API_URL || 'https://comida.mugrelore.com/api')
	: '/api';

let _offline = $state(false);
let _since: number | null = null;
let _pinging = false;

export const connectivity = {
	get isOffline() { return _offline; },

	/** Call on every successful API response */
	recordSuccess() {
		if (_offline) {
			_offline = false;
			_since = null;
		}
	},

	/** Call on every network-level error (not 4xx/5xx — those are server responses) */
	recordFailure() {
		if (!_offline) {
			_offline = true;
			_since = Date.now();
		}
	},

	/** Proactive check on app init — resolves quickly so the banner appears fast */
	async ping() {
		if (_pinging) return;
		_pinging = true;
		const controller = new AbortController();
		const timer = setTimeout(() => controller.abort(), 4000);
		try {
			const res = await fetch(`${BASE}/health`, { method: 'HEAD', signal: controller.signal });
			if (res.ok || res.status < 500) {
				connectivity.recordSuccess();
			} else {
				connectivity.recordFailure();
			}
		} catch {
			connectivity.recordFailure();
		} finally {
			clearTimeout(timer);
			_pinging = false;
		}
	},

	get offlineSince(): number | null { return _since; },
};
