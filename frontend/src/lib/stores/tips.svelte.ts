import { api } from '$lib/api';
import { auth } from '$lib/stores/auth.svelte';
import type { User } from '$lib/types';

/** Explicaciones cortas que salen la primera vez que hacen falta. Cada id
 *  tiene `tips.<id>.title` y `tips.<id>.body` en los diccionarios. */
export const TIP_IDS = [
	'duel',
	'circles',
	'recipe_sharing',
	'adherence',
	'consistency',
	'macro_adjust',
	'partner_day',
	'module.inventory',
	'module.cheat_days',
	'module.mood',
] as const;
export type TipId = (typeof TIP_IDS)[number];

function createTipsStore() {
	// Lo que hay en pantalla ahora mismo, y si es la primera vez (se marca como
	// vista al cerrar) o la ha pedido con el botón ⓘ (ya estaba vista).
	let current = $state<TipId | null>(null);
	let firstTime = $state(false);
	// Pedidas mientras había otra cosa encima: salen al cerrar.
	let queue: TipId[] = [];
	// El aviso de novedades manda: mientras no se sepa si hay, o esté abierto,
	// nada. Empieza bloqueado; lo libera el layout (ver +layout.svelte).
	let blocked = $state(true);
	// Una por sesión y tipo, aunque el POST de "vista" falle (sin conexión):
	// mejor no repetirla que machacar con ella en cada pantalla.
	const shownThisSession = new Set<TipId>();

	function seen(id: TipId): boolean {
		return auth.user?.seen_tips?.includes(id) ?? false;
	}

	function next() {
		if (current || blocked) return;
		const id = queue.shift();
		if (!id) return;
		current = id;
		firstTime = true;
	}

	return {
		get current() { return current; },
		get firstTime() { return firstTime; },

		/** La primera vez que hace falta: sale solo si nunca la ha cerrado. */
		request(id: TipId) {
			if (!auth.isLoggedIn || seen(id) || shownThisSession.has(id) || queue.includes(id)) return;
			shownThisSession.add(id);
			queue.push(id);
			next();
		},

		/** Botón ⓘ: siempre, aunque ya la haya visto. */
		open(id: TipId) {
			current = id;
			firstTime = false;
		},

		close() {
			const id = current;
			const markSeen = firstTime;
			current = null;
			firstTime = false;
			if (id && markSeen && !seen(id)) {
				auth.updateUser({ seen_tips: [...(auth.user?.seen_tips ?? []), id] });
				api.post<User>(`/users/me/tips/${encodeURIComponent(id)}/seen`, {})
					.then((u) => auth.updateUser({ seen_tips: u.seen_tips }))
					.catch(() => {});
			}
			// Un respiro antes de la siguiente, para que no parezca la misma.
			setTimeout(next, 400);
		},

		setBlocked(value: boolean) {
			blocked = value;
			if (!value) setTimeout(next, 400);
		},
	};
}

export const tips = createTipsStore();
