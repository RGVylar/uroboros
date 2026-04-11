/**
 * Reactive store for pending friend request count.
 * Polled every 60 seconds while the user is logged in.
 * The layout and settings page both read from this store.
 */
import { api } from '$lib/api';
import { auth } from './auth.svelte';

function createPendingFriendsStore() {
	let count = $state(0);
	let interval: ReturnType<typeof setInterval> | null = null;

	async function refresh() {
		if (!auth.isLoggedIn) return;
		try {
			const res = await api.get<{ count: number }>('/friends/pending/count');
			count = res.count;
		} catch {
			// ignore
		}
	}

	function start() {
		refresh();
		if (!interval) {
			interval = setInterval(refresh, 60_000);
		}
	}

	function stop() {
		if (interval) {
			clearInterval(interval);
			interval = null;
		}
		count = 0;
	}

	return {
		get count() { return count; },
		refresh,
		start,
		stop,
	};
}

export const pendingFriends = createPendingFriendsStore();
