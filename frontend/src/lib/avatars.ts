/**
 * Preset profile avatars. Image files live in static/avatars/<id>.webp.
 * Keep this list in sync with backend/app/avatars.py.
 */
export interface AvatarOption {
	id: string;
	label: string;
	emoji: string;
}

export const AVATARS: AvatarOption[] = [
	{ id: 'aguacate', label: 'Aguacate', emoji: '🥑' },
	{ id: 'sushi', label: 'Sushi', emoji: '🍣' },
	{ id: 'fresa', label: 'Fresa', emoji: '🍓' },
	{ id: 'taco', label: 'Taco', emoji: '🌮' },
	{ id: 'brocoli', label: 'Brócoli', emoji: '🥦' },
	{ id: 'huevo', label: 'Huevo', emoji: '🍳' },
	{ id: 'ramen', label: 'Ramen', emoji: '🍜' },
	{ id: 'sandia', label: 'Sandía', emoji: '🍉' },
	{ id: 'cafe', label: 'Café', emoji: '☕' },
];

const AVATAR_IDS = new Set(AVATARS.map((a) => a.id));

export function isAvatarId(id: string | null | undefined): id is string {
	return !!id && AVATAR_IDS.has(id);
}

export function avatarUrl(id: string | null | undefined): string | null {
	return isAvatarId(id) ? `/avatars/${id}.webp` : null;
}
