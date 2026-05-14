/**
 * Offline write queue — persists pending API writes to localStorage.
 * Drained automatically when connectivity is restored (from +layout.svelte).
 */

import { api } from '$lib/api';

const STORAGE_KEY = 'uro_sync_queue';

export interface PendingWrite {
	id: string;
	method: 'POST' | 'DELETE' | 'PATCH' | 'PUT';
	path: string;
	body?: unknown;
	createdAt: number;
	/** Human-readable label shown in the UI */
	label?: string;
}

function load(): PendingWrite[] {
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		return raw ? JSON.parse(raw) : [];
	} catch {
		return [];
	}
}

function persist(queue: PendingWrite[]) {
	try {
		localStorage.setItem(STORAGE_KEY, JSON.stringify(queue));
	} catch { /* storage full */ }
}

let _queue = $state<PendingWrite[]>(load());
let _syncing = $state(false);

export const syncQueue = {
	get items(): PendingWrite[] { return _queue; },
	get count(): number { return _queue.length; },
	get isSyncing(): boolean { return _syncing; },

	enqueue(write: Omit<PendingWrite, 'id' | 'createdAt'>) {
		const entry: PendingWrite = {
			...write,
			id: crypto.randomUUID(),
			createdAt: Date.now(),
		};
		_queue = [..._queue, entry];
		persist(_queue);
		return entry.id;
	},

	remove(id: string) {
		_queue = _queue.filter(w => w.id !== id);
		persist(_queue);
	},

	/** Drain the queue — call when connectivity is restored. */
	async drain(): Promise<{ succeeded: number; failed: number }> {
		if (_syncing || _queue.length === 0) return { succeeded: 0, failed: 0 };
		_syncing = true;
		let succeeded = 0;
		let failed = 0;

		// Work on a snapshot so we don't mutate while iterating
		const snapshot = [..._queue];
		for (const write of snapshot) {
			try {
				if (write.method === 'POST') {
					await api.post(write.path, write.body ?? {});
				} else if (write.method === 'DELETE') {
					await api.del(write.path);
				} else if (write.method === 'PATCH') {
					await api.patch(write.path, write.body ?? {});
				} else if (write.method === 'PUT') {
					await api.put(write.path, write.body ?? {});
				}
				// Success — remove from queue
				_queue = _queue.filter(w => w.id !== write.id);
				persist(_queue);
				succeeded++;
			} catch {
				// Leave in queue — will retry next reconnect
				failed++;
			}
		}

		_syncing = false;
		return { succeeded, failed };
	},
};
