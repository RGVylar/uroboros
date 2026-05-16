<!--
  Aurora.svelte — fondo de gradientes oklch + grano
  Montar UNA VEZ en +layout.svelte. Position absolute, no captura clicks.
-->
<script lang="ts">
	let { intensity = 1 }: { intensity?: number } = $props();
</script>

<div class="aurora" aria-hidden="true" style:--uro-int={intensity}>
	<div class="blob blob-green"></div>
	<div class="blob blob-blue"></div>
	<div class="blob blob-violet"></div>
	<div class="grain"></div>
</div>

<style>
	.aurora {
		position: fixed;
		inset: 0;
		overflow: hidden;
		z-index: 0;
		pointer-events: none;
		background: radial-gradient(ellipse at 50% -10%, #0d1a1e 0%, #06080c 60%, #04050a 100%);
	}
	.blob {
		position: absolute;
		border-radius: 50%;
		filter: blur(48px);
	}
	.blob-green {
		top: -10%;
		left: -15%;
		width: 70%;
		height: 55%;
		background: radial-gradient(circle, oklch(78% 0.18 165 / calc(0.55 * var(--uro-int, 1))) 0%, transparent 65%);
	}
	.blob-blue {
		top: 25%;
		right: -20%;
		width: 75%;
		height: 60%;
		background: radial-gradient(circle, oklch(65% 0.2 260 / calc(0.45 * var(--uro-int, 1))) 0%, transparent 65%);
	}
	.blob-violet {
		bottom: -15%;
		left: 20%;
		width: 65%;
		height: 50%;
		background: radial-gradient(circle, oklch(60% 0.22 310 / calc(0.3 * var(--uro-int, 1))) 0%, transparent 65%);
	}
	.grain {
		position: absolute;
		inset: 0;
		opacity: 0.5;
		mix-blend-mode: overlay;
		background-image: radial-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px);
		background-size: 3px 3px;
	}
</style>
