/**
 * Simple localStorage cache for API GET responses.
 * Keys are prefixed with "uro_cache_" to avoid collisions.
 * Data is considered stale after TTL_MS (default 24h).
 */

const PREFIX = 'uro_cache_';
const TTL_MS = 24 * 60 * 60 * 1000; // 24 hours

interface CacheEntry<T> {
	data: T;
	ts: number;
}

export function cacheSet<T>(key: string, data: T): void {
	try {
		localStorage.setItem(PREFIX + key, JSON.stringify({ data, ts: Date.now() } satisfies CacheEntry<T>));
	} catch {
		// Storage full or unavailable — silently ignore
	}
}

export function cacheGet<T>(key: string): { data: T; stale: boolean } | null {
	try {
		const raw = localStorage.getItem(PREFIX + key);
		if (!raw) return null;
		const entry: CacheEntry<T> = JSON.parse(raw);
		return { data: entry.data, stale: Date.now() - entry.ts > TTL_MS };
	} catch {
		return null;
	}
}

export function cacheClear(key: string): void {
	try {
		localStorage.removeItem(PREFIX + key);
	} catch { /* ignore */ }
}
