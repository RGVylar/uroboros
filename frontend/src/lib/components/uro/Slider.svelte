<!--
  Slider.svelte — fila etiquetada con track + dot + <input type=range> invisible.
  El número también se puede escribir: con el dedo, acertar 62 kg exactos en un
  slider de 110 valores es una lotería.
  Props:
    - label, unit
    - value (bindable), min, max, step
-->
<script lang="ts">
	let {
		label,
		value = $bindable(),
		min,
		max,
		step = 1,
		unit = '',
	}: {
		label: string;
		value: number;
		min: number;
		max: number;
		step?: number;
		unit?: string;
	} = $props();

	const pct = $derived(((value - min) / (max - min)) * 100);
	// El pulgar nativo (invisible, 18px) recorre el ancho menos su tamaño; el
	// punto que se ve tiene que hacer lo mismo o al cogerlo "salta".
	const thumbLeft = $derived(`calc((100% - 18px) * ${pct / 100})`);

	function typed(e: Event & { currentTarget: HTMLInputElement }) {
		const v = e.currentTarget.valueAsNumber;
		if (Number.isFinite(v) && v >= min && v <= max) value = v;
	}
	// Al salir, lo que quede fuera de rango vuelve al último valor válido.
	function settle(e: Event & { currentTarget: HTMLInputElement }) {
		e.currentTarget.value = String(value);
	}
</script>

<div class="row">
	<div class="header">
		<span class="label">{label}</span>
		<span class="value">
			<input
				class="num"
				type="number"
				inputmode="numeric"
				{min}
				{max}
				{step}
				value={value}
				aria-label={label}
				oninput={typed}
				onblur={settle}
			/><span class="unit">{unit}</span>
		</span>
	</div>
	<div class="track">
		<div class="fill" style:width="calc({thumbLeft} + 9px)"></div>
		<div class="dot" style:left={thumbLeft}></div>
		<input type="range" {min} {max} {step} bind:value aria-label={label} />
	</div>
</div>

<style>
	.row {
		padding: 14px;
		border-radius: 16px;
		background: rgba(255, 255, 255, 0.04);
		border: 1px solid rgba(255, 255, 255, 0.08);
		margin-bottom: 10px;
	}
	.header {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		margin-bottom: 10px;
	}
	.label {
		font-size: 12px;
		color: rgba(255, 255, 255, 0.55);
		font-weight: 600;
	}
	.value {
		font-size: 18px;
		color: #fff;
		font-weight: 800;
		font-variant-numeric: tabular-nums;
	}
	.num {
		width: 3.2em;
		padding: 0;
		border: none;
		border-bottom: 1px dashed rgba(255, 255, 255, 0.25);
		border-radius: 0;
		background: none;
		backdrop-filter: none;
		color: inherit;
		font: inherit;
		text-align: right;
		-moz-appearance: textfield;
		appearance: textfield;
	}
	.num::-webkit-outer-spin-button,
	.num::-webkit-inner-spin-button {
		-webkit-appearance: none;
		margin: 0;
	}
	.num:focus {
		outline: none;
		border-bottom-color: oklch(78% 0.18 165);
	}
	.unit {
		font-size: 11px;
		color: rgba(255, 255, 255, 0.4);
		font-weight: 500;
		margin-left: 4px;
	}
	.track {
		position: relative;
		height: 6px;
		border-radius: 99px;
		background: rgba(255, 255, 255, 0.06);
	}
	.fill {
		position: absolute;
		left: 0;
		top: 0;
		height: 6px;
		border-radius: 99px;
		background: linear-gradient(90deg, oklch(78% 0.18 165), oklch(65% 0.2 200));
		pointer-events: none;
	}
	.dot {
		position: absolute;
		top: -6px;
		width: 18px;
		height: 18px;
		border-radius: 50%;
		background: linear-gradient(135deg, #fff, oklch(85% 0.1 165));
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
		pointer-events: none;
	}
	input[type='range'] {
		position: absolute;
		inset: -10px 0;
		width: 100%;
		opacity: 0;
		cursor: pointer;
		margin: 0;
		-webkit-appearance: none;
		appearance: none;
	}
	input[type='range']::-webkit-slider-thumb {
		-webkit-appearance: none;
		width: 18px;
		height: 18px;
	}
	input[type='range']::-moz-range-thumb {
		width: 18px;
		height: 18px;
		border: none;
	}
</style>
