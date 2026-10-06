<!--
  Explainer.svelte — la explicación que esté pidiendo el store `tips`.
  Se monta una sola vez, en el layout; las pantallas solo llaman a
  tips.request(id) (primera vez) o tips.open(id) (botón ⓘ, ver InfoTip).
-->
<script lang="ts">
	import Modal from './Modal.svelte';
	import TipVisual from './TipVisual.svelte';
	import { tips } from '$lib/stores/tips.svelte';
	import { t } from '$lib/i18n/index.svelte';
</script>

{#if tips.current}
	{@const id = tips.current}
	<Modal onClose={() => tips.close()} title={t(`tips.${id}.title`)} maxWidth={420}>
		<div class="tip">
			<TipVisual {id} />
			{#each t(`tips.${id}.body`).split('\n') as para}
				<p>{para}</p>
			{/each}
			<button class="ok" onclick={() => tips.close()}>{t('tips.ok')}</button>
		</div>
	</Modal>
{/if}

<style>
	.tip p {
		font-size: 0.875rem;
		line-height: 1.5;
		color: rgba(255, 255, 255, 0.78);
		margin: 0 0 0.75rem;
	}
	.ok {
		width: 100%;
		margin-top: 0.5rem;
	}
</style>
