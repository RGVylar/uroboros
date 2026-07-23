<script lang="ts">
	import type { Locale } from '$lib/i18n/index.svelte';

	// Los emoji 🇪🇸🇬🇧🇵🇹 no se ven en Windows (no hay glifo de bandera y el
	// navegador dibuja las letras del par de indicadores: "ES", "GB", "PT"),
	// así que las banderas van dibujadas a mano.
	interface Props {
		locale: Locale;
		size?: number;
	}

	let { locale, size = 20 }: Props = $props();
</script>

{#if locale === 'es'}
	<svg class="flag" viewBox="0 0 60 40" width={size} height={size * 2 / 3} aria-hidden="true">
		<rect width="60" height="40" fill="#c60b1e" />
		<rect y="10" width="60" height="20" fill="#ffc400" />
	</svg>
{:else if locale === 'en'}
	<svg class="flag" viewBox="0 0 60 40" width={size} height={size * 2 / 3} aria-hidden="true">
		<clipPath id="flag-gb-tl"><path d="M30 20 60 20 60 40z M30 20 30 40 0 40z M30 20 0 20 0 0z M30 20 30 0 60 0z" /></clipPath>
		<rect width="60" height="40" fill="#012169" />
		<path d="M0 0 60 40M60 0 0 40" stroke="#fff" stroke-width="8" />
		<path d="M0 0 60 40M60 0 0 40" stroke="#c8102e" stroke-width="5" clip-path="url(#flag-gb-tl)" />
		<path d="M30 0V40M0 20H60" stroke="#fff" stroke-width="13" />
		<path d="M30 0V40M0 20H60" stroke="#c8102e" stroke-width="8" />
	</svg>
{:else}
	<svg class="flag" viewBox="0 0 60 40" width={size} height={size * 2 / 3} aria-hidden="true">
		<rect width="60" height="40" fill="#da291c" />
		<rect width="24" height="40" fill="#046a38" />
		<circle cx="24" cy="20" r="8" fill="none" stroke="#ffe900" stroke-width="2" />
		<path d="M20.5 16h7v4a3.5 4 0 0 1-7 0z" fill="#fff" stroke="#da291c" stroke-width="1.4" />
	</svg>
{/if}

<style>
	.flag {
		display: block;
		border-radius: 2px;
		box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.16);
	}
</style>
