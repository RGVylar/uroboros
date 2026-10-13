// La receta como imagen vertical (1080×1920) para historias de Instagram y
// estados de WhatsApp. Se pinta en un canvas en el propio móvil: no hace falta
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
const H = 1920;
const PAD = 96;
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
		[540, 2050, 1100, 'rgba(30, 110, 150, 0.22)'],
	] as const) {
		const g = ctx.createRadialGradient(x, y, 0, x, y, r);
		g.addColorStop(0, color);
		g.addColorStop(1, 'rgba(0,0,0,0)');
		ctx.fillStyle = g;
		ctx.fillRect(0, 0, W, H);
	}

	let y = 170;
	if (logo) ctx.drawImage(logo, PAD, y - 70, 110, 110);
	y += 130;

	// Título
	ctx.fillStyle = '#eef1f5';
	ctx.font = `112px ${SERIF}`;
	ctx.textBaseline = 'alphabetic';
	for (const line of wrap(ctx, d.name, W - PAD * 2)) {
		y += 110;
		ctx.fillText(line, PAD, y);
	}
	y += 64;
	ctx.font = `500 40px ${SANS}`;
	ctx.fillStyle = 'rgba(255,255,255,0.55)';
	ctx.fillText(d.meta, PAD, y);

	// Calorías en grande y macros en sus colores
	y += 230;
	ctx.font = `800 190px ${SANS}`;
	ctx.fillStyle = '#ffb36b';
	ctx.fillText(String(d.kcal), PAD, y);
	const kw = ctx.measureText(String(d.kcal)).width;
	ctx.font = `500 44px ${SANS}`;
	ctx.fillStyle = 'rgba(255,255,255,0.55)';
	ctx.fillText(d.macroNote, PAD + kw + 24, y);

	y += 100;
	let x = PAD;
	ctx.font = `700 54px ${SANS}`;
	for (const [label, value, color] of [
		['P', d.p, '#6fb8ff'],
		['C', d.c, '#b4a0ff'],
		['G', d.f, '#ff8a8a'],
	] as const) {
		ctx.fillStyle = color;
		const text = `${label} ${value}g`;
		ctx.fillText(text, x, y);
		x += ctx.measureText(text).width + 56;
	}

	// Ingredientes: los que quepan antes del pie
	y += 90;
	ctx.strokeStyle = 'rgba(255,255,255,0.12)';
	ctx.lineWidth = 2;
	ctx.beginPath();
	ctx.moveTo(PAD, y);
	ctx.lineTo(W - PAD, y);
	ctx.stroke();

	const footerTop = H - 380;
	const rowH = 76;
	const fit = Math.max(1, Math.floor((footerTop - y - 40) / rowH));
	const shown = d.ingredients.length > fit ? d.ingredients.slice(0, fit - 1) : d.ingredients;
	ctx.font = `500 44px ${SANS}`;
	for (const ing of shown) {
		y += rowH;
		ctx.fillStyle = '#8ff0c4';
		ctx.textAlign = 'right';
		ctx.fillText(ing.qty, W - PAD, y);
		const qw = ctx.measureText(ing.qty).width;
		ctx.textAlign = 'left';
		ctx.fillStyle = '#d6dedb';
		ctx.fillText(ellipsize(ctx, ing.name, W - PAD * 2 - qw - 40), PAD, y);
	}
	if (shown.length < d.ingredients.length) {
		y += rowH;
		ctx.fillStyle = 'rgba(255,255,255,0.45)';
		ctx.fillText(d.moreLabel(d.ingredients.length - shown.length), PAD, y);
	}

	// Pie: marca y, si hay enlace, el QR
	const qrSize = 250;
	const footY = H - PAD - qrSize;
	ctx.font = `64px ${SERIF}`;
	ctx.fillStyle = '#eef1f5';
	ctx.fillText('Uroboros', PAD, footY + 120);
	if (d.url) {
		ctx.font = `500 36px ${SANS}`;
		ctx.fillStyle = 'rgba(255,255,255,0.55)';
		for (const [i, line] of wrap(ctx, d.scanLabel, W - PAD * 2 - qrSize - 60, 2).entries())
			ctx.fillText(line, PAD, footY + 190 + i * 46);
		drawQr(ctx, d.url, W - PAD - qrSize, footY, qrSize);
	}

	return new Promise((resolve, reject) =>
		canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('canvas'))), 'image/png')
	);
}
