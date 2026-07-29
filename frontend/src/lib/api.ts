import { Capacitor } from '@capacitor/core';
import { auth } from '$lib/stores/auth.svelte';
import { connectivity } from '$lib/stores/connectivity.svelte';
import { t } from '$lib/i18n/index.svelte';

// In native app, API calls go to the remote server.
// In web, they go through Caddy's reverse proxy at /api.
const BASE = Capacitor.isNativePlatform()
	? (import.meta.env.VITE_API_URL || 'https://comida.mugrelore.com/api')
	: '/api';

// Las fotos de perfil las sirve el backend, no el bundle: en la app nativa hay
// que apuntar al servidor, no a la ruta local del APK.
export const MEDIA_BASE = `${BASE}/media`;

// AbortController timeout only on web — Capacitor's native fetch bridge on Android
// adds significant latency when a signal is passed, so we skip it on native.
const REQUEST_TIMEOUT_MS = 6000;
// Subir una foto por datos móviles no cabe en los 6s del resto de llamadas.
const UPLOAD_TIMEOUT_MS = 30000;
const isNative = Capacitor.isNativePlatform();

async function request<T>(path: string, opts: RequestInit = {}, timeoutMs = REQUEST_TIMEOUT_MS): Promise<T> {
	const headers: Record<string, string> = {};
	// Con FormData el Content-Type lo pone el navegador, que es el único que
	// sabe el boundary del multipart; ponerlo a mano rompe la petición.
	if (!(opts.body instanceof FormData)) headers['Content-Type'] = 'application/json';
	const token = auth.token;
	if (token) headers['Authorization'] = `Bearer ${token}`;

	const controller = isNative ? null : new AbortController();
	const timer = controller ? setTimeout(() => controller.abort(), timeoutMs) : null;

	let res: Response;
	try {
		res = await fetch(`${BASE}${path}`, {
			...opts,
			headers: { ...headers, ...opts.headers },
			...(controller ? { signal: controller.signal } : {}),
		});
	} catch {
		// Network-level failure (server unreachable, timeout, no internet, etc.)
		connectivity.recordFailure();
		throw new Error(t('net.offline'));
	} finally {
		if (timer) clearTimeout(timer);
	}

	// 502/503/504 = gateway errors (proxy up, backend down) → treat as offline
	if (res.status === 502 || res.status === 503 || res.status === 504) {
		connectivity.recordFailure();
		throw new Error(t('net.offline'));
	}

	// Got a meaningful response — server is reachable
	connectivity.recordSuccess();

	if (res.status === 401) {
		auth.logout();
		throw new Error('Unauthorized');
	}
	if (!res.ok) {
		const body = await res.json().catch(() => ({}));
		let message: string;
		if (res.status === 422 && typeof body.detail !== 'string') {
			// Los errores de validación de FastAPI traen una lista de campos que
			// no se le puede enseñar a nadie. Cuando el detail es un texto
			// nuestro ("no hemos podido leer esa imagen") sí se enseña.
			message = t('net.badFormat');
		} else if (typeof body.detail === 'string') {
			message = body.detail;
		} else {
			message = res.statusText || 'Error desconocido';
		}
		throw new Error(message);
	}
	if (res.status === 204) return undefined as T;
	return res.json();
}

export const api = {
	get: <T>(path: string) => request<T>(path),
	post: <T>(path: string, body: unknown) => request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
	put: <T>(path: string, body: unknown) => request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
	patch: <T>(path: string, body: unknown) => request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
	del: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
	upload: <T>(path: string, form: FormData) =>
		request<T>(path, { method: 'POST', body: form }, UPLOAD_TIMEOUT_MS)
};
