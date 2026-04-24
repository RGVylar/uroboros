<!--
  EmptyState.svelte
  Placeholder consistente para "sin resultados" / "sin datos".

  Uso:
    <EmptyState
      icon="🥣"
      title="Sin registros"
      description="Añade tu primera comida del día"
      actionLabel="Añadir comida"
      actionHref="/add"
    />
-->
<script lang="ts">
	interface Props {
		icon?: string;
		title: string;
		description?: string;
		actionLabel?: string;
		actionHref?: string;
		onAction?: () => void;
	}
	let {
		icon = '',
		title,
		description,
		actionLabel,
		actionHref,
		onAction,
	}: Props = $props();
</script>

<div class="empty">
	{#if icon}<div class="icon" aria-hidden="true">{icon}</div>{/if}
	<div class="title">{title}</div>
	{#if description}<div class="desc">{description}</div>{/if}
	{#if actionLabel}
		{#if actionHref}
			<a href={actionHref} class="action">{actionLabel}</a>
		{:else if onAction}
			<button class="action" onclick={onAction}>{actionLabel}</button>
		{/if}
	{/if}
</div>

<style>
	.empty {
		text-align: center;
		padding: 2.5rem 1.25rem;
		color: var(--text-muted);
	}
	.icon {
		font-size: 2.5rem;
		margin-bottom: 0.5rem;
		filter: grayscale(0.2);
		opacity: 0.8;
	}
	.title {
		font-size: 1rem;
		font-weight: 700;
		color: var(--text);
		margin-bottom: 0.25rem;
	}
	.desc {
		font-size: 0.85rem;
		line-height: 1.4;
		max-width: 280px;
		margin: 0 auto 1.25rem;
	}
	.action {
		display: inline-block;
		margin-top: 0.5rem;
		padding: 0.6rem 1.3rem;
		border-radius: 99px;
		background: linear-gradient(180deg, var(--primary), var(--primary-dim));
		color: var(--primary-ink);
		font-weight: 800;
		font-size: 0.85rem;
		text-decoration: none;
		border: none;
		box-shadow:
			0 1px 0 rgba(255, 255, 255, 0.25) inset,
			0 8px 20px -6px var(--primary-glow);
		cursor: pointer;
	}
</style>
