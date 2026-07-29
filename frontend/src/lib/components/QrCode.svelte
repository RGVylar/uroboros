<!--
  Código QR como SVG. En SVG y no en canvas porque escala sin pixelarse, no
  necesita devicePixelRatio y se puede pintar del color que haga falta.

  El módulo se pinta como un <rect> por celda. Son ~900 rects para un QR
  pequeño: nada para el navegador, y evita construir un path a mano.
-->
<script lang="ts">
	import qrcode from 'qrcode-generator';

	let {
		value,
		size = 180,
		dark = '#041010',
		light = '#ffffff',
	}: {
		value: string;
		size?: number;
		dark?: string;
		light?: string;
	} = $props();

	const qr = $derived.by(() => {
		// Tipo 0 = que la librería elija la versión mínima que quepa.
		// Corrección 'M': el equilibrio de siempre entre tamaño y tolerancia a
		// que el móvil lo lea torcido o con brillos.
		const q = qrcode(0, 'M');
		q.addData(value);
		q.make();
		return q;
	});

	const count = $derived(qr.getModuleCount());
	// Margen obligatorio del estándar: sin él muchos lectores no enganchan.
	const QUIET = 4;
	const total = $derived(count + QUIET * 2);

	const cells = $derived.by(() => {
		const out: { x: number; y: number }[] = [];
		for (let r = 0; r < count; r++) {
			for (let c = 0; c < count; c++) {
				if (qr.isDark(r, c)) out.push({ x: c + QUIET, y: r + QUIET });
			}
		}
		return out;
	});
</script>

<svg
	width={size}
	height={size}
	viewBox="0 0 {total} {total}"
	shape-rendering="crispEdges"
	role="img"
	aria-label="Código QR"
	style="border-radius:10px; display:block;"
>
	<rect width={total} height={total} fill={light} />
	{#each cells as cell}
		<rect x={cell.x} y={cell.y} width="1" height="1" fill={dark} />
	{/each}
</svg>
