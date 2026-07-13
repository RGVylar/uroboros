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
