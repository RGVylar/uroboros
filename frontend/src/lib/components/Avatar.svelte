<!--
  Circular user avatar. Por orden: la foto que ha subido el usuario, el avatar
  predefinido que haya elegido, y si no hay ninguno el disco de la inicial de
  siempre (con el tono derivado del nombre).
-->
<script lang="ts">
	import { avatarUrl, nameHue, photoUrl } from '$lib/avatars';

	let {
		name,
		avatarId = null,
		avatarPhoto = null,
		size = 46,
		ring = null,
		identityHue = null,
	}: {
		name: string;
		avatarId?: string | null;
		avatarPhoto?: string | null; // foto subida; gana al preset cuando cabe
		size?: number;
		ring?: string | null; // optional CSS border, e.g. "2px solid #fff"
		identityHue?: number | null; // overrides the name-derived disc hue
	} = $props();

	// Por debajo de esto una cara es una mancha, y los avatares ilustrados están
	// dibujados para leerse justo a ese tamaño. El chip del diario compartido se
	// pinta a 16px: ahí no entra ninguna foto.
	const MIN_PHOTO_PX = 24;

	// La foto viene del servidor, no del bundle: sin cobertura no carga. Cuando
	// falla se vuelve al preset o al disco en vez de dejar el icono roto.
	let photoFailed = $state(false);
	$effect(() => {
		avatarPhoto; // re-intentar si el usuario cambia de foto
		photoFailed = false;
	});

	const photo = $derived(
		size >= MIN_PHOTO_PX && !photoFailed ? photoUrl(avatarPhoto) : null
	);
	const url = $derived(photo ?? avatarUrl(avatarId));

	const h = $derived(identityHue ?? nameHue(name || '?'));
	const initial = $derived((name || '?')[0].toUpperCase());
</script>

{#if url}
	<img
		src={url}
		alt={name}
		width={size}
		height={size}
		onerror={() => { if (photo) photoFailed = true; }}
		style="width:{size}px; height:{size}px; border-radius:50%; object-fit:cover; flex-shrink:0; {ring ? `border:${ring};` : ''}"
	/>
{:else}
	<div
		style="width:{size}px; height:{size}px; border-radius:50%; background:linear-gradient(135deg, oklch(72% 0.18 {h}), oklch(55% 0.16 {(h + 30) % 360})); display:flex; align-items:center; justify-content:center; font-size:{size * 0.42}px; font-weight:800; color:#fff; flex-shrink:0; {ring ? `border:${ring};` : ''}"
	>
		{initial}
	</div>
{/if}
