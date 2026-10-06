// Icono de comida adivinado por el nombre, para los avatares de producto y
// receta cuando no hay foto. Es una pista visual, no una clasificación: si no
// encaja nada, cubiertos.
import type { IconName } from '$lib/icons';

const PRODUCT_RULES: [RegExp, IconName][] = [
	[/avena|cereal|arroz|pan|pasta/, 'grain'],
	[/pollo|pavo/, 'chicken'],
	[/leche|yogur|queso/, 'milk'],
	[/huevo/, 'egg'],
	[/manzana|plátano|fruta/, 'fruit'],
	[/jamón|ibérico|cerdo/, 'meat'],
	[/aceite|oliva/, 'oil'],
	[/cerveza/, 'beer'],
	[/barra|tierna/, 'bread'],
	[/kebab/, 'sandwich'],
	[/atún/, 'fish']
];

const RECIPE_RULES: [RegExp, IconName][] = [
	[/desayun|avena|porridge/, 'breakfast'],
	[/pollo|pechug/, 'chicken'],
	[/ensalada/, 'salad'],
	[/pasta|espagueti/, 'pot'],
	[/batido|smoothie|protein/, 'drink'],
	[/pescado|salmón|atún/, 'fish'],
	[/arroz|bowl/, 'grain'],
	[/tosta|pan/, 'sandwich']
];

function match(rules: [RegExp, IconName][], name: string): IconName {
	const n = name.toLowerCase();
	return rules.find(([re]) => re.test(n))?.[1] ?? 'meal';
}

export const productIcon = (name: string) => match(PRODUCT_RULES, name);
export const recipeIcon = (name: string) => match(RECIPE_RULES, name);
