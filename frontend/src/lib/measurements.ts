/** Keys must match backend `MEASUREMENT_KEYS` / `app.measurement_keys`. */
export const MEASUREMENT_FIELDS: { key: string; label: string }[] = [
	{ key: 'neck', label: 'Cuello' },
	{ key: 'chest', label: 'Pecho' },
	{ key: 'waist', label: 'Cintura' },
	{ key: 'hips', label: 'Cadera' },
	{ key: 'bicep_l', label: 'Brazo izq.' },
	{ key: 'bicep_r', label: 'Brazo dcha.' },
	{ key: 'thigh_l', label: 'Muslo izq.' },
	{ key: 'thigh_r', label: 'Muslo dcha.' },
	{ key: 'calf_l', label: 'Gemelo izq.' },
	{ key: 'calf_r', label: 'Gemelo dcha.' }
];

/** Distinct colors per series (works on dark UI). */
export const MEASUREMENT_COLORS: Record<string, string> = {
	neck: '#22c55e',
	chest: '#3b82f6',
	waist: '#a855f7',
	hips: '#f97316',
	bicep_l: '#ec4899',
	bicep_r: '#14b8a6',
	thigh_l: '#eab308',
	thigh_r: '#ef4444',
	calf_l: '#6366f1',
	calf_r: '#84cc16'
};
