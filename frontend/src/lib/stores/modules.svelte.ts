import { api } from '$lib/api';

/** Partes de la app que cada usuario puede encender o apagar. El backend
 *  (GET/PATCH /users/me/modules) mezcla las de solo interfaz con las tres que
 *  viven en user_goals; aquí son todas iguales. */
export type ModuleKey =
	| 'water'
	| 'weight'
	| 'exercise'
	| 'measurements'
	| 'supplements'
	| 'mood'
	| 'cheat_days'
	| 'inventory';

export type Modules = Record<ModuleKey, boolean>;

// Los mismos que services/modules.py: se usan hasta que responde el servidor.
const DEFAULTS: Modules = {
	water: true,
	weight: true,
	exercise: true,
	measurements: true,
	supplements: true,
	mood: false,
	cheat_days: false,
	inventory: false,
};

const CACHE_KEY = 'uro_modules';
// Antes de existir el endpoint, ánimo y suplementos vivían solo en este
// dispositivo. Se suben una vez y se borran.
const LEGACY_KEYS: Partial<Record<ModuleKey, string>> = {
	mood: 'mood_enabled',
	supplements: 'supplements_enabled',
};

function readCache(): Modules {
	try {
		const raw = localStorage.getItem(CACHE_KEY);
		if (raw) return { ...DEFAULTS, ...JSON.parse(raw) };
	} catch {
		// sin caché o ilegible: valores por defecto
	}
	return { ...DEFAULTS };
}

function writeCache(m: Modules) {
	try {
		localStorage.setItem(CACHE_KEY, JSON.stringify(m));
	} catch {
		// almacenamiento lleno o bloqueado: la próxima carga vuelve a pedirlo
	}
}

function legacyChanges(server: Modules): Partial<Modules> {
	const changes: Partial<Modules> = {};
	try {
		for (const [key, lsKey] of Object.entries(LEGACY_KEYS) as [ModuleKey, string][]) {
			const raw = localStorage.getItem(lsKey);
			if (raw === null) continue;
			const value = raw === 'true';
			if (value !== server[key]) changes[key] = value;
		}
	} catch {
		// sin acceso a localStorage: nada que migrar
	}
	return changes;
}

function clearLegacy() {
	try {
		for (const lsKey of Object.values(LEGACY_KEYS)) localStorage.removeItem(lsKey);
	} catch {
		// ídem
	}
}

function createModulesStore() {
	let state = $state<Modules>(typeof localStorage !== 'undefined' ? readCache() : { ...DEFAULTS });
	let loaded = $state(false);

	function apply(m: Modules) {
		state = m;
		writeCache(m);
	}

	async function load() {
		try {
			let m = await api.get<Modules>('/users/me/modules');
			const changes = legacyChanges(m);
			if (Object.keys(changes).length > 0) m = await api.patch<Modules>('/users/me/modules', changes);
			clearLegacy();
			apply(m);
		} catch {
			// offline: se queda con la caché
		} finally {
			loaded = true;
		}
	}

	/** Cambia un módulo. Optimista: si el servidor lo rechaza, vuelve atrás y
	 *  relanza el error (p.ej. 402 al encender cheat days sin Premium). */
	async function set(key: ModuleKey, value: boolean) {
		const prev = state;
		state = { ...state, [key]: value };
		try {
			apply(await api.patch<Modules>('/users/me/modules', { [key]: value }));
		} catch (e) {
			state = prev;
			throw e;
		}
	}

	return {
		get all() { return state; },
		get loaded() { return loaded; },
		on(key: ModuleKey) { return state[key]; },
		load,
		set,
	};
}

export const modules = createModulesStore();
