import { t } from '$lib/i18n/index.svelte';

// Heurística compartida para decidir si un producto se mide en ml (bebida) o g.
// Compara palabras completas: con includes(), "aguacate" contenía "agua" y los
// sólidos aparecían como "/100ml" en búsqueda, detalle y diario.

const DRINK_WORDS = new Set([
	'leche', 'zumo', 'jugo', 'agua', 'bebida', 'refresco', 'batido',
	'smoothie', 'néctar', 'nectar', 'cerveza', 'vino', 'caldo', 'té', 'te',
	'café', 'cafe', 'yogur', 'kéfir', 'kefir', 'infusión', 'infusion',
	'horchata', 'limonada', 'naranjada',
]);

export function isDrink(p: { name: string; brand?: string | null }): boolean {
	const words = `${p.name} ${p.brand ?? ''}`.toLowerCase().split(/[^\p{L}]+/u);
	return words.some(w => DRINK_WORDS.has(w));
}

/** Unidad de medida a mostrar para un producto. */
export function productUnit(p: { name: string; brand?: string | null }): 'ml' | 'g' {
	return isDrink(p) ? 'ml' : 'g';
}

// ── Unidad explícita del producto ────────────────────────────────────────────
// Desde 0054 el producto puede llevar `unit` ('g' | 'ml' | 'unit'); si es nulo
// se sigue adivinando por el nombre. Para 'unit' el backend guarda los macros
// "por unidad" y una unidad son 100 g internos (el factor por defecto de
// unit_conversions), así que aquí solo hay que convertir para enseñar.

export type ProductUnit = 'g' | 'ml' | 'unit';
export const GRAMS_PER_UNIT = 100;

type UnitSource = { name: string; brand?: string | null; unit?: ProductUnit | null };

/** Unidad real de un producto: la explícita si la tiene, si no la heurística. */
export function productUnitOf(p: UnitSource): ProductUnit {
	return p.unit ?? (isDrink(p) ? 'ml' : 'g');
}

/** Sufijo corto para pegar a una cantidad: 'g', 'ml' o 'ud'. */
export function unitSuffix(u: ProductUnit): string {
	return u === 'unit' ? ` ${t('unit.short')}` : u;
}

/** Gramos internos → cantidad que ve el usuario (unidades para 'unit'). */
export function gramsToQty(grams: number, u: ProductUnit): number {
	return u === 'unit' ? Math.round((grams / GRAMS_PER_UNIT) * 100) / 100 : grams;
}

/** Cantidad que ve el usuario → gramos internos. */
export function qtyToGrams(qty: number, u: ProductUnit): number {
	return u === 'unit' ? qty * GRAMS_PER_UNIT : qty;
}

/** "36g", "300ml" o "2 ud" a partir de los gramos internos de una entrada. */
export function fmtQty(grams: number, p: UnitSource | null | undefined): string {
	const u = p ? productUnitOf(p) : 'g';
	const q = gramsToQty(grams, u);
	return `${Number.isInteger(q) ? q : q.toFixed(1)}${unitSuffix(u)}`;
}

/** "/100g", "/100ml" o "/ud": a qué se refieren los macros del producto. */
export function perLabel(p: UnitSource): string {
	const u = productUnitOf(p);
	return u === 'unit' ? '/ud' : `/100${u}`;
}
