<!--
	Icono de la interfaz. Hereda el color del texto (currentColor) y por defecto
	mide como la letra que lo rodea, así sustituye a un emoji sin tocar el CSS
	de alrededor. Sin `label` es decorativo y el lector de pantalla lo salta.
-->
<script lang="ts">
	import { ICONS, type IconName } from '$lib/icons';

	let {
		name,
		size = '1.15em',
		strokeWidth = 2,
		label,
		fill,
		class: cls = '',
		style
	}: {
		name: IconName;
		size?: number | string;
		strokeWidth?: number;
		label?: string;
		fill?: string;
		class?: string;
		style?: string;
	} = $props();

	const Cmp = $derived(ICONS[name]);
</script>

<Cmp
	{size}
	{strokeWidth}
	fill={fill ?? 'none'}
	class="uro-icon {cls}"
	{style}
	aria-hidden={label ? undefined : 'true'}
	aria-label={label}
	role={label ? 'img' : undefined}
/>

<style>
	:global(.uro-icon) {
		display: inline-block;
		vertical-align: -0.15em;
		flex-shrink: 0;
	}
</style>
