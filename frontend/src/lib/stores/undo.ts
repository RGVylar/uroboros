import { toast } from './toast.svelte';
import { t } from '$lib/i18n/index.svelte';

// Borrado diferido con "Deshacer": la UI quita el elemento al momento, pero la
// petición al servidor no sale hasta que pasa el plazo. Deshacer solo tiene que
// devolverlo a la vista, porque en el servidor sigue existiendo.
// Solo hay uno pendiente a la vez: uno nuevo confirma el anterior.

const UNDO_MS = 5000;

interface Pending {
	timer: ReturnType<typeof setTimeout>;
	toastId: number;
	commit: () => unknown;
}

let pending: Pending | null = null;

export function undoable(message: string, commit: () => unknown, revert: () => void) {
	flushUndo();
	const timer = setTimeout(() => {
		pending = null;
		commit();
	}, UNDO_MS);
	const toastId = toast.action(message, {
		label: t('common.undo'),
		run: () => {
			if (pending?.timer !== timer) return;
			clearTimeout(timer);
			toast.remove(toastId);
			pending = null;
			revert();
		},
	}, UNDO_MS);
	pending = { timer, toastId, commit };
}

// Confirma ya lo pendiente (al cerrar o mandar la app a segundo plano).
export function flushUndo() {
	if (!pending) return;
	const p = pending;
	pending = null;
	clearTimeout(p.timer);
	toast.remove(p.toastId);
	p.commit();
}

if (typeof document !== 'undefined') {
	document.addEventListener('visibilitychange', () => {
		if (document.visibilityState === 'hidden') flushUndo();
	});
}
