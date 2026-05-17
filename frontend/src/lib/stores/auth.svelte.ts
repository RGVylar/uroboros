import type { User } from '$lib/types';

function createAuth() {
	let token = $state<string | null>(null);
	let user = $state<User | null>(null);

	if (typeof localStorage !== 'undefined') {
		try {
			const t = localStorage.getItem('token');
			if (t && t !== 'undefined') token = t;
			const saved = localStorage.getItem('user');
			if (saved && saved !== 'undefined') user = JSON.parse(saved);
		} catch {
			localStorage.removeItem('token');
			localStorage.removeItem('user');
		}
	}

	return {
		get token() { return token; },
		get user() { return user; },
		get isLoggedIn() { return !!token; },

		login(t: string, u: User) {
			token = t;
			user = u;
			localStorage.setItem('token', t);
			localStorage.setItem('user', JSON.stringify(u));
		},

		logout() {
			token = null;
			user = null;
			localStorage.removeItem('token');
			localStorage.removeItem('user');
		}
	};
}

export const auth = createAuth();
