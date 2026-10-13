<script lang="ts">
	// Una olla dibujada con el caldo a la altura de lo que queda, con vapor
	// mientras quede algo. `take` es lo que se va a sacar ahora: se pinta rayado
	// arriba del caldo, en el color de quien come (dos colores si son los dos).
	let {
		left,
		take = 0,
		takeColors = [],
		size = 92,
		label,
	}: {
		left: number; // 0..1 de la olla
		take?: number; // 0..1 de la olla
		takeColors?: string[];
		size?: number;
		label?: string;
	} = $props();

	const uid = Math.random().toString(36).slice(2, 8);
	const BODY = 'M18 34 h84 v44 a18 18 0 0 1 -18 18 h-48 a18 18 0 0 1 -18 -18 z';
	const WAVE = 'M-60 4 q15 -6 30 0 t30 0 t30 0 t30 0 t30 0 t30 0 v120 h-180 z';
	// Interior útil, en coordenadas del viewBox.
	const TOP = 34;
	const H = 62;
	const clamp = (n: number) => Math.max(0, Math.min(1, n));
	const level = $derived(TOP + (1 - clamp(left)) * H);
	const takeH = $derived(clamp(Math.min(take, left)) * H);
</script>

<svg viewBox="0 0 120 104" width={size} height={(size * 104) / 120} role="img" aria-label={label} style="flex-shrink:0; overflow:visible;">
	<defs>
		<clipPath id="b-{uid}"><path d={BODY} /></clipPath>
		<linearGradient id="s-{uid}" x1="0" y1="0" x2="0" y2="1">
			<stop offset="0" stop-color="oklch(85% 0.17 150)" />
			<stop offset="1" stop-color="oklch(62% 0.19 170)" />
		</linearGradient>
		<pattern id="t-{uid}" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
			<rect width="4" height="8" fill={takeColors[0] ?? '#fff'} />
			<rect x="4" width="4" height="8" fill={takeColors[1] ?? 'transparent'} />
		</pattern>
	</defs>

	{#if left > 0.001}
		<g class="steam" stroke="rgba(255,255,255,0.35)" stroke-width="3" fill="none" stroke-linecap="round">
			<path d="M44 24 q-5 -7 0 -14" /><path d="M60 26 q-5 -8 0 -16" /><path d="M76 24 q-5 -7 0 -14" />
		</g>
	{/if}
	<path d="M8 42 h10 M102 42 h10" stroke="rgba(255,255,255,0.35)" stroke-width="6" stroke-linecap="round" />
	<path d={BODY} fill="rgba(255,255,255,0.06)" />
	<g clip-path="url(#b-{uid})">
		<!-- Las tres olas se mueven juntas: el caldo, lo que te llevas (rayado,
		     misma ola) y, tapándolo por abajo, el caldo que quedará. Así el
		     rayado sigue la superficie arriba y acaba en ola abajo. -->
		<g class="wave">
			<g class="level" style="transform: translateY({level}px);">
				<path d={WAVE} fill="url(#s-{uid})" />
			</g>
			{#if takeH > 0}
				<g class="level" style="transform: translateY({level}px);">
					<path d={WAVE} fill="url(#t-{uid})" opacity="0.9" />
				</g>
				<g class="level" style="transform: translateY({level + takeH}px);">
					<path d={WAVE} fill="url(#s-{uid})" />
				</g>
			{/if}
		</g>
	</g>
	<path d={BODY} fill="none" stroke="rgba(255,255,255,0.28)" stroke-width="2.5" />
	<rect x="12" y="30" width="96" height="6" rx="3" fill="rgba(255,255,255,0.3)" />
</svg>

<style>
	.steam path { animation: steam 2.4s ease-in-out infinite; }
	.steam path:nth-child(2) { animation-delay: 0.5s; }
	.steam path:nth-child(3) { animation-delay: 1s; }
	@keyframes steam {
		0%, 100% { opacity: 0.15; transform: translateY(2px); }
		50% { opacity: 0.7; transform: translateY(-2px); }
	}
	.level { transition: transform 0.6s cubic-bezier(0.3, 1.3, 0.5, 1); }
	.wave { animation: wave 3s linear infinite; }
	@keyframes wave { from { transform: translateX(0); } to { transform: translateX(60px); } }
	@media (prefers-reduced-motion: reduce) {
		.steam path, .wave { animation: none; }
	}
</style>
