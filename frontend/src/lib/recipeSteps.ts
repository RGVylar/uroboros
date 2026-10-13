// Ingredientes mencionados en los pasos de una receta: `@[Cebolla](179)` o,
// con cantidad propia para ese paso, `@[Aceite](197:15)` (gramos internos).
// El paso sigue siendo texto plano: sin migración ni cambios en la API, y si el
// ingrediente desaparece de la receta queda como texto normal.
import { fmtQty, type ProductUnit } from '$lib/drink';

type Ing = { product: { id: number; name: string; brand?: string | null; unit?: ProductUnit | null }; grams: number };

export type StepPart =
	| { kind: 'text'; text: string }
	| { kind: 'ing'; name: string; qty: string | null };

const TAG = /@\[([^\]]+)\]\((\d+)(?::(\d+(?:\.\d+)?))?\)/g;

export function mentionToken(name: string, productId: number, grams?: number | null): string {
	const clean = name.replace(/[[\]]/g, '');
	return grams ? `@[${clean}](${productId}:${grams})` : `@[${clean}](${productId})`;
}

/** Trocea un paso en texto y chips de ingrediente con su cantidad actual. */
export function stepParts(step: string, ingredients: Ing[]): StepPart[] {
	const parts: StepPart[] = [];
	let last = 0;
	for (const m of step.matchAll(TAG)) {
		if (m.index! > last) parts.push({ kind: 'text', text: step.slice(last, m.index) });
		const ing = ingredients.find((i) => i.product.id === Number(m[2]));
		if (ing) {
			const grams = m[3] ? Number(m[3]) : ing.grams;
			parts.push({ kind: 'ing', name: ing.product.name, qty: fmtQty(grams, ing.product) });
		} else {
			parts.push({ kind: 'text', text: m[1] });
		}
		last = m.index! + m[0].length;
	}
	if (last < step.length) parts.push({ kind: 'text', text: step.slice(last) });
	return parts;
}

/** El paso para compartir como texto: "la cebolla (150 g)". */
export function stepPlain(step: string, ingredients: Ing[]): string {
	return stepParts(step, ingredients)
		.map((p) => (p.kind === 'text' ? p.text : `${p.name.toLocaleLowerCase()} (${p.qty})`))
		.join('');
}

// En el editor no se ven las marcas: `@Cebolla` y, con cantidad propia,
// `@Aceite de oliva:10`. Al escribir se vuelven a convertir en marcas
// buscando el nombre más largo de los ingredientes de la receta tras la "@".

export function toDisplay(step: string): string {
	return step.replace(TAG, (_, name, _id, grams) => (grams ? `@${name}:${grams}` : `@${name}`));
}

export function fromDisplay(text: string, ingredients: Ing[]): string {
	const byLength = [...ingredients].sort((a, b) => b.product.name.length - a.product.name.length);
	let out = '';
	let i = 0;
	while (i < text.length) {
		const at = text.indexOf('@', i);
		if (at < 0) break;
		out += text.slice(i, at);
		const rest = text.slice(at + 1);
		const ing = byLength.find((x) => rest.toLocaleLowerCase().startsWith(x.product.name.toLocaleLowerCase()));
		if (!ing) {
			out += '@';
			i = at + 1;
			continue;
		}
		// Se guarda tal y como está escrito para que ida y vuelta dé el mismo
		// texto (si no, el textarea se reescribe y el cursor salta al final).
		let end = at + 1 + ing.product.name.length;
		const name = text.slice(at + 1, end);
		const qty = text.slice(end).match(/^:(\d+)/);
		if (qty) end += qty[0].length;
		out += mentionToken(name, ing.product.id, qty ? Number(qty[1]) : null);
		i = end;
	}
	return out + text.slice(i);
}

export function hasMentions(step: string): boolean {
	return /@\[[^\]]+\]\(\d+/.test(step);
}
