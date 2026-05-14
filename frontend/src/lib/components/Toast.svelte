<script lang="ts">
	import { toast } from '$lib/stores/toast.svelte';
</script>

{#if toast.toasts.length > 0}
	<div class="toast-stack" aria-live="polite" aria-atomic="false">
		{#each toast.toasts as t (t.id)}
			<div class="toast toast--{t.type}" role="alert">
				<span class="toast-icon">
					{#if t.type === 'error'}✕{:else if t.type === 'success'}✓{:else}i{/if}
				</span>
				<span class="toast-msg">{t.message}</span>
				<button class="toast-close" onclick={() => toast.remove(t.id)} aria-label="Cerrar">×</button>
			</div>
		{/each}
	</div>
{/if}

<style>
	.toast-stack {
		position: fixed;
		bottom: calc(72px + env(safe-area-inset-bottom));
		left: 50%;
		transform: translateX(-50%);
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		z-index: 9999;
		width: min(92vw, 360px);
		pointer-events: none;
	}

	.toast {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		padding: 0.65rem 0.85rem;
		border-radius: 10px;
		font-size: 0.82rem;
		font-weight: 500;
		pointer-events: all;
		animation: toast-in 0.22s ease;
		backdrop-filter: blur(8px);
		box-shadow: 0 4px 18px rgba(0, 0, 0, 0.35);
	}

	@keyframes toast-in {
		from { opacity: 0; transform: translateY(10px); }
		to   { opacity: 1; transform: translateY(0); }
	}

	.toast--error {
		background: oklch(28% 0.08 20 / 0.95);
		border: 1px solid oklch(50% 0.18 20 / 0.5);
		color: oklch(90% 0.06 20);
	}
	.toast--success {
		background: oklch(25% 0.07 160 / 0.95);
		border: 1px solid oklch(55% 0.16 160 / 0.5);
		color: oklch(90% 0.06 160);
	}
	.toast--info {
		background: oklch(25% 0.06 260 / 0.95);
		border: 1px solid oklch(55% 0.12 260 / 0.5);
		color: oklch(88% 0.05 260);
	}

	.toast-icon {
		font-size: 0.75rem;
		font-weight: 800;
		flex-shrink: 0;
		width: 16px;
		text-align: center;
	}

	.toast-msg {
		flex: 1;
		line-height: 1.35;
	}

	.toast-close {
		background: none;
		border: none;
		color: inherit;
		opacity: 0.6;
		cursor: pointer;
		font-size: 1rem;
		line-height: 1;
		padding: 0 0.1rem;
		flex-shrink: 0;
	}
	.toast-close:hover { opacity: 1; }

	@media (min-width: 900px) {
		.toast-stack {
			bottom: 1.5rem;
			left: auto;
			right: 1.5rem;
			transform: none;
		}
	}
</style>
