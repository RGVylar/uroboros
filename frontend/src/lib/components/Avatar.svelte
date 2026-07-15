<!--
  Circular user avatar. Shows the chosen preset image when set, otherwise the
  classic initial disc with a hue derived from the name (unchanged look).
-->
<script lang="ts">
	import { avatarUrl } from '$lib/avatars';

	let {
		name,
		avatarId = null,
		size = 46,
		ring = null,
	}: {
		name: string;
		avatarId?: string | null;
		size?: number;
		ring?: string | null; // optional CSS border, e.g. "2px solid #fff"
	} = $props();

	const url = $derived(avatarUrl(avatarId));

	function hue(n: string): number {
		let h = 0;
		for (const c of n) h = (h * 31 + c.charCodeAt(0)) % 360;
		return h;
	}
	const h = $derived(hue(name || '?'));
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
