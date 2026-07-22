<!--
  Circular user avatar. Shows the chosen preset image when set, otherwise the
  classic initial disc with a hue derived from the name (unchanged look).
-->
<script lang="ts">
	import { avatarUrl, nameHue } from '$lib/avatars';

	let {
		name,
		avatarId = null,
		size = 46,
		ring = null,
		identityHue = null,
	}: {
		name: string;
		avatarId?: string | null;
		size?: number;
		ring?: string | null; // optional CSS border, e.g. "2px solid #fff"
		identityHue?: number | null; // overrides the name-derived disc hue
	} = $props();

	const url = $derived(avatarUrl(avatarId));

	const h = $derived(identityHue ?? nameHue(name || '?'));
	const initial = $derived((name || '?')[0].toUpperCase());
</script>

{#if url}
	<img
		src={url}
		alt={name}
		width={size}
		height={size}
		style="width:{size}px; height:{size}px; border-radius:50%; object-fit:cover; flex-shrink:0; {ring ? `border:${ring};` : ''}"
	/>
{:else}
	<div
		style="width:{size}px; height:{size}px; border-radius:50%; background:linear-gradient(135deg, oklch(72% 0.18 {h}), oklch(55% 0.16 {(h + 30) % 360})); display:flex; align-items:center; justify-content:center; font-size:{size * 0.42}px; font-weight:800; color:#fff; flex-shrink:0; {ring ? `border:${ring};` : ''}"
	>
		{initial}
	</div>
{/if}
