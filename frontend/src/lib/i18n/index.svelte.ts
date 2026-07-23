import { es, type Dict } from './es';
import { en } from './en';
import { pt } from './pt';
import type { MealType } from '$lib/types';

export type Locale = 'es' | 'en' | 'pt';
export type TKey = keyof typeof es;

const dicts: Record<Locale, Dict> = { es, en, pt };
const LS_KEY = 'uro_lang';

export const LOCALE_NAMES: Record<Locale, string> = {
	es: 'Español',
	en: 'English',
	pt: 'Português',
};

export const i18n = $state({ locale: 'es' as Locale });

if (typeof localStorage !== 'undefined') {
	const stored = localStorage.getItem(LS_KEY);
	if (stored === 'es' || stored === 'en' || stored === 'pt') {
		i18n.locale = stored;
	} else {
		// Sin preferencia guardada: detectar por idioma del dispositivo. No se
		// persiste — solo una elección explícita en Ajustes escribe en localStorage,
		// así el que cambia el idioma del móvil ve la app seguirle.
		const nav = (navigator.language ?? 'es').slice(0, 2).toLowerCase();
		i18n.locale = nav === 'en' ? 'en' : nav === 'pt' ? 'pt' : 'es';
	}
	document.documentElement.lang = i18n.locale;
}

export function setLocale(l: Locale) {
	i18n.locale = l;
	try { localStorage.setItem(LS_KEY, l); } catch {}
	document.documentElement.lang = l;
}

export function t(key: TKey, params?: Record<string, string | number>): string {
	let s: string = dicts[i18n.locale][key] ?? es[key] ?? key;
	if (params) {
		for (const [k, v] of Object.entries(params)) s = s.replaceAll(`{${k}}`, String(v));
	}
	return s;
}

// Pluralización simple one/other — válida para es/en/pt.
export function tc(base: string, count: number, params?: Record<string, string | number>): string {
	return t(`${base}${count === 1 ? '_one' : '_other'}` as TKey, { count, ...params });
}

// pt es portugués europeo (pequeno-almoço, sumo, ementa). Un brasileño lo
// entiende sin problema; si algún día compensa un pt-BR propio, se parte el dict.
export function getLocaleTag(): string {
	return { es: 'es-ES', en: 'en-US', pt: 'pt-PT' }[i18n.locale];
}

export function fmtDate(d: Date, opts?: Intl.DateTimeFormatOptions): string {
	return d.toLocaleDateString(getLocaleTag(), opts);
}

export function fmtTime(d: Date, opts?: Intl.DateTimeFormatOptions): string {
	return d.toLocaleTimeString(getLocaleTag(), opts);
}

export function fmtNumber(n: number, opts?: Intl.NumberFormatOptions): string {
	return n.toLocaleString(getLocaleTag(), opts);
}

// Nombres de mes y día: los da Intl, que ya sabe hacerlo en los tres idiomas.
// Escribirlos a mano en el diccionario sería 19 claves más para nada.
export function monthNames(format: 'long' | 'short' = 'long'): string[] {
	const fmt = new Intl.DateTimeFormat(getLocaleTag(), { month: format });
	return Array.from({ length: 12 }, (_, m) =>
		fmt.format(new Date(2000, m, 1)).replace(/^\p{Ll}/u, (c) => c.toUpperCase()),
	);
}

/** Iniciales de los días, empezando en lunes (la semana europea). */
export function weekdayInitials(): string[] {
	const fmt = new Intl.DateTimeFormat(getLocaleTag(), { weekday: 'narrow' });
	// 2024-01-01 fue lunes.
	return Array.from({ length: 7 }, (_, i) => fmt.format(new Date(2024, 0, 1 + i)).toUpperCase());
}

/** Día de la semana abreviado de una fecha concreta. */
export function weekdayShort(d: Date): string {
	return new Intl.DateTimeFormat(getLocaleTag(), { weekday: 'short' }).format(d);
}

// Sustituye al antiguo MEAL_LABELS de types.ts, que era un objeto constante y
// por tanto no reaccionaba al cambio de idioma.
export function mealLabel(mt: MealType): string {
	return t(`meal.${mt}` as TKey);
}

/** Contorno corporal: la clave viaja a la API, la etiqueta solo se muestra. */
export function measureLabel(key: string): string {
	return t(`measure.${key}` as TKey);
}

/** Alérgeno de Open Food Facts. La clave viene de la API (p. ej. "sesame-seeds");
 *  si es una que no conocemos, se muestra tal cual en vez de romper. */
export function allergenLabel(key: string): string {
	const k = `allergen.${key}` as TKey;
	return k in es ? t(k) : key;
}

/** Avatar predefinido de lib/avatars.ts. */
export function avatarLabel(id: string): string {
	return t(`avatar.${id}` as TKey);
}

/** Ejercicio predefinido: la clave es su nombre en español, que es lo que
 *  guarda la BD como semilla y no cambia. Los creados por el usuario se
 *  devuelven tal cual, que para eso los escribió él. */
export function exerciseLabel(name: string): string {
	const key = `exercise.${name}` as TKey;
	return key in es ? t(key) : name;
}

/** Unidad de un ejercicio ('minutos' | 'repeticiones'), misma lógica. */
export function exerciseUnit(unit: string): string {
	const key = `exerciseUnit.${unit}` as TKey;
	return key in es ? t(key) : unit;
}
