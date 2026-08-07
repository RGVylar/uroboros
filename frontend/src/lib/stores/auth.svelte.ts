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

		/** ¿Puede ver esta feature sin terminar? Solo decide qué se pinta; el
		 *  acceso lo corta el backend, que responde 404 si no toca. El layout
		 *  refresca el usuario desde /auth/me al entrar, así que activar un flag
		 *  en la BD se nota sin tener que cerrar sesión. */
		hasFlag(flag: string) { return user?.feature_flags?.includes(flag) ?? false; },

		login(t: string, u: User) {
			token = t;
			user = u;
			localStorage.setItem('token', t);
			localStorage.setItem('user', JSON.stringify(u));
		},

		updateUser(patch: Partial<User>) {
			if (!user) return;
			user = { ...user, ...patch };
			localStorage.setItem('user', JSON.stringify(user));
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
