// La receta como imagen 4:5 (1080×1350): cabe entera en la miniatura del chat
// de WhatsApp (que recorta lo que pase de ~2:3; con 9:16 se perdían arriba y
// abajo), es la proporción de los posts de Instagram y en historias se ve con
// margen. Se pinta en un canvas en el propio móvil: no hace falta
// servidor y sale con las fuentes y colores de la app. Si la receta tiene
// enlace público, lleva un QR que abre la página /r/<código>.
import qrcode from 'qrcode-generator';

export type CardData = {
	name: string;
	meta: string; // "2 raciones · 35 min"
	kcal: number;
	p: number;
	c: number;
	f: number;
	macroNote: string; // "kcal / ración" o "kcal · receta entera"
	ingredients: { name: string; qty: string }[];
	moreLabel: (n: number) => string; // "+3 más"
	url: string | null;
	scanLabel: string; // "Escanéala para guardarla"
};

const W = 1080;
const H = 1350;
const PAD = 72;
const SERIF = "'Instrument Serif', Georgia, serif";
const SANS = "Geist, -apple-system, 'Segoe UI', Roboto, sans-serif";

function loadImage(src: string): Promise<HTMLImageElement | null> {
	return new Promise((resolve) => {
		const img = new Image();
		img.onload = () => resolve(img);
		img.onerror = () => resolve(null);
		img.src = src;
	});
}

// Parte el título en líneas que quepan; como mucho tres, con "…" si sobra.
function wrap(ctx: CanvasRenderingContext2D, text: string, max: number, lines = 3): string[] {
	const out: string[] = [];
	let line = '';
	for (const word of text.split(' ')) {
		const next = line ? `${line} ${word}` : word;
		if (ctx.measureText(next).width <= max || !line) line = next;
		else {
			out.push(line);
			line = word;
		}
	}
	if (line) out.push(line);
	if (out.length > lines) {
		out.length = lines;
		out[lines - 1] += '…';
	}
	return out;
}

function ellipsize(ctx: CanvasRenderingContext2D, text: string, max: number): string {
	if (ctx.measureText(text).width <= max) return text;
	let s = text;
	while (s.length > 1 && ctx.measureText(s + '…').width > max) s = s.slice(0, -1);
	return s + '…';
}

function drawQr(ctx: CanvasRenderingContext2D, value: string, x: number, y: number, size: number) {
	const q = qrcode(0, 'M');
	q.addData(value);
	q.make();
	const n = q.getModuleCount();
	const quiet = 3;
	const cell = size / (n + quiet * 2);
	ctx.fillStyle = '#ffffff';
	ctx.beginPath();
	ctx.roundRect(x, y, size, size, 24);
	ctx.fill();
	ctx.fillStyle = '#06100c';
	for (let r = 0; r < n; r++)
		for (let c = 0; c < n; c++)
			if (q.isDark(r, c)) ctx.fillRect(x + (c + quiet) * cell, y + (r + quiet) * cell, Math.ceil(cell), Math.ceil(cell));
}

export async function recipeCardBlob(d: CardData): Promise<Blob> {
	// Que la serif del título esté cargada antes de pintar (si no, sale Georgia).
	await document.fonts?.load(`96px ${SERIF}`).catch(() => {});
	const logo = await loadImage('/logo.png');

	const canvas = document.createElement('canvas');
	canvas.width = W;
	canvas.height = H;
	const ctx = canvas.getContext('2d')!;

	// Fondo: el mismo negro verdoso con halos de color que la app.
	ctx.fillStyle = '#06070a';
	ctx.fillRect(0, 0, W, H);
	for (const [x, y, r, color] of [
		[150, 120, 900, 'rgba(40, 150, 120, 0.30)'],
		[1000, 380, 800, 'rgba(120, 70, 190, 0.20)'],
		[540, 1500, 900, 'rgba(30, 110, 150, 0.22)'],
	] as const) {
		const g = ctx.createRadialGradient(x, y, 0, x, y, r);
		g.addColorStop(0, color);
		g.addColorStop(1, 'rgba(0,0,0,0)');
		ctx.fillStyle = g;
		ctx.fillRect(0, 0, W, H);
	}

	// Cabecera: logo y marca
	if (logo) ctx.drawImage(logo, PAD, 52, 68, 68);
	ctx.font = `48px ${SERIF}`;
	ctx.fillStyle = 'rgba(238,241,245,0.85)';
	ctx.fillText('Uroboros', PAD + (logo ? 88 : 0), 102);

	// Con muchos ingredientes la cabecera se compacta para dejarles sitio.
	const compact = d.ingredients.length > 6;

	// Título (dos líneas, o una si va compacta) y raciones/tiempo
	let y = 120;
	ctx.fillStyle = '#eef1f5';
	ctx.font = `${compact ? 80 : 92}px ${SERIF}`;
	ctx.textBaseline = 'alphabetic';
	for (const line of wrap(ctx, d.name, W - PAD * 2, compact ? 1 : 2)) {
		y += compact ? 86 : 96;
		ctx.fillText(line, PAD, y);
	}
	if (d.meta) {
		y += 54;
		ctx.font = `500 34px ${SANS}`;
		ctx.fillStyle = 'rgba(255,255,255,0.55)';
		ctx.fillText(d.meta, PAD, y);
	}

	// Calorías en grande y macros en sus colores
	y += compact ? 128 : 150;
	ctx.font = `800 ${compact ? 116 : 140}px ${SANS}`;
	ctx.fillStyle = '#ffb36b';
	ctx.fillText(String(d.kcal), PAD, y);
	const kw = ctx.measureText(String(d.kcal)).width;
	ctx.font = `500 38px ${SANS}`;
	ctx.fillStyle = 'rgba(255,255,255,0.55)';
	ctx.fillText(d.macroNote, PAD + kw + 22, y);

	y += compact ? 64 : 74;
	let x = PAD;
	ctx.font = `700 46px ${SANS}`;
	for (const [label, value, color] of [
		['P', d.p, '#6fb8ff'],
		['C', d.c, '#b4a0ff'],
		['G', d.f, '#ff8a8a'],
	] as const) {
		ctx.fillStyle = color;
		const text = `${label} ${value}g`;
		ctx.fillText(text, x, y);
		x += ctx.measureText(text).width + 48;
	}

	y += 46;
	ctx.strokeStyle = 'rgba(255,255,255,0.12)';
	ctx.lineWidth = 2;
	ctx.beginPath();
	ctx.moveTo(PAD, y);
	ctx.lineTo(W - PAD, y);
	ctx.stroke();

	// Ingredientes: se encogen para que quepan todos; si aun así no, pasan a
	// dos columnas, y solo con muchísimos se corta con "+N más".
	const qrSize = d.url ? 190 : 0;
	const bottom = H - PAD - (d.url ? qrSize + 28 : 0);
	const area = bottom - y - 10;
	const MIN_ROW = 41;
	const MAX_ROW = 78;
	const n = d.ingredients.length;
	const rowsFit = Math.max(1, Math.floor(area / MIN_ROW));
	const cols = n > rowsFit ? 2 : 1;
	const capacity = rowsFit * cols;
	const shown = n > capacity ? d.ingredients.slice(0, capacity - 1) : d.ingredients;
	const items = shown.length < n ? [...shown, { name: d.moreLabel(n - shown.length), qty: '' }] : shown;
	const rows = Math.ceil(items.length / cols);
	const rowH = Math.min(MAX_ROW, Math.max(MIN_ROW, area / Math.max(rows, 1)));
	const gap = 48;
	const colW = (W - PAD * 2 - gap * (cols - 1)) / cols;
	ctx.font = `500 ${Math.round(Math.min(rowH * 0.62, cols === 2 ? 28 : 46))}px ${SANS}`;
	items.forEach((ing, i) => {
		const col = Math.floor(i / rows);
		const left = PAD + col * (colW + gap);
		const base = y + (i % rows + 1) * rowH - rowH * 0.22;
		if (!ing.qty) {
			ctx.fillStyle = 'rgba(255,255,255,0.45)';
			ctx.fillText(ing.name, left, base);
			return;
		}
		ctx.fillStyle = '#8ff0c4';
		ctx.textAlign = 'right';
		ctx.fillText(ing.qty, left + colW, base);
		const qw = ctx.measureText(ing.qty).width;
		ctx.textAlign = 'left';
		ctx.fillStyle = '#d6dedb';
		ctx.fillText(ellipsize(ctx, ing.name, colW - qw - 24), left, base);
	});

	// Pie: si hay enlace, el QR y para qué sirve
	if (d.url) {
		const qy = H - PAD - qrSize;
		ctx.font = `500 32px ${SANS}`;
		ctx.fillStyle = 'rgba(255,255,255,0.55)';
		const lines = wrap(ctx, d.scanLabel, W - PAD * 2 - qrSize - 48, 2);
		lines.forEach((line, i) => ctx.fillText(line, PAD, qy + qrSize - 14 - (lines.length - 1 - i) * 42));
		drawQr(ctx, d.url, W - PAD - qrSize, qy, qrSize);
	}

	return new Promise((resolve, reject) =>
		canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('canvas'))), 'image/png')
	);
}
