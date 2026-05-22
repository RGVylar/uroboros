<script lang="ts">
	import { subscription } from '$lib/stores/subscription.svelte';

	let days = $derived(subscription.trial_days_left);
	// Only show during trial, and only when ≤3 days left (urgency)
	let visible = $derived(subscription.status === 'trial' && days !== null && days <= 3);
</script>

{#if visible}
	<div class="banner">
		<span class="emoji">⏳</span>
		<span class="text">
			{#if days === 0}
				Tu prueba termina hoy
			{:else}
				{days} {days === 1 ? 'día' : 'días'} de prueba restantes
			{/if}
		</span>
		<a href="/premium" class="cta">Ver planes</a>
	</div>
{/if}

<style>
	.banner {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.625rem 1rem;
		background: oklch(72% 0.18 55 / 0.15);
		border: 1px solid oklch(72% 0.18 55 / 0.3);
		border-radius: 12px;
		margin-bottom: 0.75rem;
		font-size: 0.8125rem;
		color: oklch(88% 0.14 55);
	}
	.emoji { font-size: 1rem; flex-shrink: 0; }
	.text { flex: 1; font-weight: 600; }
	.cta {
		font-size: 0.75rem;
		font-weight: 700;
		color: oklch(88% 0.19 160);
		text-decoration: none;
		white-space: nowrap;
	}
</style>
