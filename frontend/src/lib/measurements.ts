/**
 * Keys must match backend `MEASUREMENT_KEYS` / `app.measurement_keys`.
 * La etiqueta visible sale de measureLabel() del módulo i18n — aquí solo van
 * las claves, que son las que viajan a la API y no se traducen nunca.
 */
export const MEASUREMENT_FIELDS: { key: string }[] = [
	{ key: 'neck' },
	{ key: 'shoulders' },
	{ key: 'chest' },
	{ key: 'waist' },
	{ key: 'navel' },
	{ key: 'hips' },
	{ key: 'bicep_l' },
	{ key: 'bicep_r' },
	{ key: 'forearm_l' },
	{ key: 'forearm_r' },
	{ key: 'thigh_l' },
	{ key: 'thigh_r' },
	{ key: 'calf_l' },
	{ key: 'calf_r' }
];

/** Distinct colors per series (works on dark UI). */
export const MEASUREMENT_COLORS: Record<string, string> = {
	neck: '#22c55e',
	shoulders: '#f59e0b',
	chest: '#3b82f6',
	waist: '#a855f7',
	navel: '#f472b6',
	hips: '#f97316',
	bicep_l: '#ec4899',
	bicep_r: '#14b8a6',
	forearm_l: '#8b5cf6',
	forearm_r: '#06b6d4',
	thigh_l: '#eab308',
	thigh_r: '#ef4444',
	calf_l: '#6366f1',
	calf_r: '#84cc16'
};
