/**
 * Preset profile avatars. Image files live in static/avatars/<id>.webp.
 * Keep this list in sync with backend/app/avatars.py.
 */
export interface AvatarOption {
	id: string;
	emoji: string;
}

// El id es lo que se guarda en la BD y nombra el fichero de imagen: no se
// traduce nunca. El nombre visible sale de avatarLabel() del módulo i18n.
export const AVATARS: AvatarOption[] = [
	{ id: 'aguacate', emoji: '🥑' },
	{ id: 'sushi', emoji: '🍣' },
	{ id: 'fresa', emoji: '🍓' },
	{ id: 'taco', emoji: '🌮' },
	{ id: 'brocoli', emoji: '🥦' },
	{ id: 'huevo', emoji: '🍳' },
	{ id: 'ramen', emoji: '🍜' },
	{ id: 'sandia', emoji: '🍉' },
	{ id: 'cafe', emoji: '☕' },
	{ id: 'pizza', emoji: '🍕' },
	{ id: 'pepinillo', emoji: '🥒' },
	{ id: 'donut', emoji: '🍩' },
	{ id: 'pulpo', emoji: '🐙' },
	{ id: 'tostada', emoji: '🍞' },
	{ id: 'lata', emoji: '🥫' },
	{ id: 'chile', emoji: '🌶️' },
	{ id: 'gelatina', emoji: '🧠' },
	{ id: 'queso', emoji: '🧀' },
];

const AVATAR_IDS = new Set(AVATARS.map((a) => a.id));

export function isAvatarId(id: string | null | undefined): id is string {
	return !!id && AVATAR_IDS.has(id);
}

export function avatarUrl(id: string | null | undefined): string | null {
	return isAvatarId(id) ? `/avatars/${id}.webp` : null;
}

/**
 * Curated identity-colour palette (OKLCH hues). Kept to the blue→violet→pink arc
 * on purpose: no green (clashes with --primary / goals), no amber (clashes with
 * --cal / kcal), no red (clashes with delete / fat). Keep in sync with the
 * backend palette in app/avatars.py (IDENTITY_HUES).
 */
export const IDENTITY_HUES: number[] = [320, 350, 290, 265, 235, 195];

/** Same name→hue derivation Avatar.svelte uses for the fallback initial disc. */
export function nameHue(name: string): number {
	let h = 0;
	for (const c of name || '?') h = (h * 31 + c.charCodeAt(0)) % 360;
	return h;
}

/** A user's identity hue: their chosen colour, or the name-derived fallback. */
export function identityHue(name: string, hue?: number | null): number {
	return hue ?? nameHue(name);
}

/** OKLCH identity colour string, optionally with alpha (for tints/borders). */
export function identityColor(name: string, hue?: number | null, alpha = 1): string {
	const h = identityHue(name, hue);
	return alpha < 1 ? `oklch(72% 0.15 ${h} / ${alpha})` : `oklch(72% 0.15 ${h})`;
}
