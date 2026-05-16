<!--
  ScreenHeader.svelte — botón back + título serif + subtítulo
-->
<script lang="ts">
	let {
		title,
		sub = '',
		onBack,
		right,
	}: {
		title: string;
		sub?: string;
		onBack?: () => void;
		right?: any;
	} = $props();
</script>

<div class="head">
	{#if onBack}
		<button class="back" aria-label="Atrás" onclick={onBack}>‹</button>
	{/if}
	<div class="texts">
		<h1 class="title">{title}</h1>
		{#if sub}<div class="sub">{sub}</div>{/if}
	</div>
	{#if right}{@render right()}{/if}
</div>

<style>
	.head {
		padding: 4px 4px 14px;
		display: flex;
		align-items: center;
		gap: 12px;
	}
	.back {
		width: 36px;
		height: 36px;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.08);
		border: 1px solid rgba(255, 255, 255, 0.1);
		display: flex;
		align-items: center;
		justify-content: center;
		color: #fff;
		cursor: pointer;
		padding: 0;
		font-size: 18px;
		flex-shrink: 0;
		font-family: inherit;
		line-height: 1;
	}
	.back:hover {
		background: rgba(255, 255, 255, 0.12);
	}
	.texts {
		flex: 1;
		min-width: 0;
	}
	.title {
		font-size: 30px;
		letter-spacing: -1px;
		color: #fff;
		line-height: 1;
		font-weight: 400;
		margin: 0;
		font-family: 'Instrument Serif', 'Lora', Georgia, serif;
	}
	.sub {
		font-size: 11px;
		color: rgba(255, 255, 255, 0.5);
		margin-top: 4px;
		letter-spacing: 0.3px;
	}
</style>
