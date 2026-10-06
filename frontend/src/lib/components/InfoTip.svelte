<!--
  InfoTip.svelte — botón ⓘ junto a un concepto difícil. Abre la misma
  explicación que salió la primera vez, para que no se pierda al cerrarla.

  Uso: <InfoTip id="duel" />
-->
<script lang="ts">
	import { tips, type TipId } from '$lib/stores/tips.svelte';
	import { t } from '$lib/i18n/index.svelte';

	let { id }: { id: TipId } = $props();
</script>

<button
	class="info"
	type="button"
	aria-label={t('tips.infoAria', { topic: t(`tips.${id}.title`) })}
	onclick={(e) => { e.stopPropagation(); tips.open(id); }}
>ⓘ</button>

<style>
	.info {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 1.25rem;
		height: 1.25rem;
		padding: 0;
		margin-left: 0.25rem;
		border-radius: 50%;
		border: none;
		background: transparent;
		box-shadow: none;
		color: rgba(255, 255, 255, 0.45);
		font-size: 0.85rem;
		line-height: 1;
		vertical-align: middle;
		cursor: pointer;
	}
	.info:hover { color: rgba(255, 255, 255, 0.85); filter: none; }
</style>
