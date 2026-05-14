type ToastType = 'error' | 'success' | 'info';

interface Toast {
	id: number;
	type: ToastType;
	message: string;
}

function createToastStore() {
	let toasts = $state<Toast[]>([]);
	let nextId = 0;

	function add(type: ToastType, message: string) {
		const id = nextId++;
		toasts = [...toasts, { id, type, message }];
		setTimeout(() => remove(id), 3500);
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
		remove,
	};
}

export const toast = createToastStore();
