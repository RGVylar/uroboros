// Connectivity store — tracks whether the backend is reachable.
// Updated by api.ts on every request. The layout reads it to show a banner.

import { Capacitor } from '@capacitor/core';

const BASE = Capacitor.isNativePlatform()
	? (import.meta.env.VITE_API_URL || 'https://comida.mugrelore.com/api')
	: '/api';

let _offline = $state(false);
let _since: number | null = null;
let _pinging = false;
// Mientras no hay conexión, nada más pregunta al servidor (lo nuevo va a la
// cola), así que sin este sondeo la app no se enteraría de que el bloqueo
// terminó hasta la próxima pantalla que cargue datos.
const RETRY_MS = 15_000;
let _retry: ReturnType<typeof setInterval> | null = null;

function stopRetry() {
	if (_retry) clearInterval(_retry);
	_retry = null;
}

if (typeof document !== 'undefined') {
	// Al volver a la app (o recuperar red) se comprueba al momento.
	document.addEventListener('visibilitychange', () => {
		if (document.visibilityState === 'visible' && _offline) connectivity.ping();
	});
	window.addEventListener('online', () => { if (_offline) connectivity.ping(); });
}

export const connectivity = {
	get isOffline() { return _offline; },

	/** Call on every successful API response */
	recordSuccess() {
		if (_offline) {
			_offline = false;
			_since = null;
			stopRetry();
		}
	},

	/** Call on every network-level error (not 4xx/5xx — those are server responses) */
	recordFailure() {
		if (!_offline) {
			_offline = true;
			_since = Date.now();
			if (!_retry) _retry = setInterval(() => connectivity.ping(), RETRY_MS);
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
