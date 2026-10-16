type ToastType = 'error' | 'success' | 'info';

interface ToastAction {
	label: string;
	run: () => void;
}

interface Toast {
	id: number;
	type: ToastType;
	message: string;
	action?: ToastAction;
}

function createToastStore() {
	let toasts = $state<Toast[]>([]);
	let nextId = 0;

	function add(type: ToastType, message: string, action?: ToastAction, ms = 3500) {
		const id = nextId++;
		toasts = [...toasts, { id, type, message, action }];
		setTimeout(() => remove(id), ms);
		return id;
	}

	function remove(id: number) {
		toasts = toasts.filter((t) => t.id !== id);
	}

	return {
		get toasts() {
			return toasts;
		},
		error: (msg: string) => add('error', msg),
		success: (msg: string) => add('success', msg),
		info: (msg: string) => add('info', msg),
		// Toast con un botón (p. ej. "Deshacer"); dura lo que diga quien lo pide.
		action: (msg: string, action: ToastAction, ms: number) => add('info', msg, action, ms),
		remove,
	};
}

export const toast = createToastStore();
