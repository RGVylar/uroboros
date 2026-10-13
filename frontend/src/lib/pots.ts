import { nameHue } from '$lib/avatars';
import { i18n, t } from '$lib/i18n/index.svelte';
import type { Pot, User } from '$lib/types';

/** Quién es quién en una olla y con qué color se pinta (el de identidad). */
export interface PotPeople {
	meId: number;
	meColor: string;
	partnerId: number | null;
	partnerName: string | null;
	partnerColor: string;
}

const hueColor = (hue: number) => `oklch(78% 0.15 ${hue})`;

export function potPeople(me: User | null, partner: User | null): PotPeople {
	return {
		meId: me?.id ?? 0,
		meColor: hueColor(me?.identity_hue ?? nameHue(me?.name ?? '')),
		partnerId: partner?.id ?? null,
		partnerName: partner?.name ?? null,
		partnerColor: hueColor(partner?.identity_hue ?? nameHue(partner?.name ?? '')),
	};
}

export function potEatenBy(pot: Pot, userId: number): number {
	return pot.eaten.find((e) => e.user_id === userId)?.servings ?? 0;
}

/** "1,5" o "1.5" según el idioma; sin decimales sobrantes. */
export function fmtServings(n: number): string {
	return (Math.round(n * 10) / 10).toLocaleString(i18n.locale, { maximumFractionDigits: 1 });
}

/** "1 ración", "2,5 raciones". */
export function servingsLabel(n: number): string {
	const r = Math.round(n * 10) / 10;
	return t(r === 1 ? 'pot.serving_one' : 'pot.serving_other', { n: fmtServings(r) });
}
