import { Capacitor } from '@capacitor/core';
import { auth } from '$lib/stores/auth.svelte';

// In native app, API calls go to the remote server.
// In web, they go through Caddy's reverse proxy at /api.
const BASE = Capacitor.isNativePlatform()
	? (import.meta.env.VITE_API_URL || 'https://comida.mugrelore.com/api')
	: '/api';

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
	const headers: Record<string, string> = { 'Content-Type': 'application/json' };
	const token = auth.token;
	if (token) headers['Authorization'] = `Bearer ${token}`;

	const res = await fetch(`${BASE}${path}`, { ...opts, headers: { ...headers, ...opts.headers } });

	if (res.status === 401) {
		auth.logout();
		throw new Error('Unauthorized');
	}
	if (!res.ok) {
		const body = await res.json().catch(() => ({}));
		throw new Error(body.detail || res.statusText);
	}
	if (res.status === 204) return undefined as T;
	return res.json();
}

export const api = {
	get: <T>(path: string) => request<T>(path),
	post: <T>(path: string, body: unknown) => request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
	put: <T>(path: string, body: unknown) => request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
	patch: <T>(path: string, body: unknown) => request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
	del: <T>(path: string) => request<T>(path, { method: 'DELETE' })
};
