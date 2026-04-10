import type { User } from '$lib/types';

function createAuth() {
	let token = $state<string | null>(null);
	let user = $state<User | null>(null);

	if (typeof localStorage !== 'undefined') {
		token = localStorage.getItem('token');
		const saved = localStorage.getItem('user');
		if (saved) user = JSON.parse(saved);
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
