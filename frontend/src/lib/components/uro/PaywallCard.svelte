<script lang="ts">
	interface Props {
		title: string;
		description: string;
		/** Optional CTA override */
		cta?: string;
		onUpgrade?: () => void;
	}

	let { title, description, cta = 'Desbloquear Premium', onUpgrade }: Props = $props();
</script>

<div class="paywall">
	<div class="lock">🔒</div>
	<div class="title">{title}</div>
	<div class="desc">{description}</div>
	<button class="upgrade-btn" onclick={onUpgrade}>
		{cta}
	</button>
	<div class="hint">Prueba 14 días gratis · sin tarjeta</div>
</div>

<style>
	.paywall {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.625rem;
		padding: 2rem 1.5rem;
		background: rgba(255,255,255,0.04);
		border: 1px solid rgba(255,255,255,0.09);
		border-radius: 20px;
		text-align: center;
		color: #fff;
	}
	.lock { font-size: 2rem; }
	.title {
		font-size: 1rem;
		font-weight: 700;
		letter-spacing: -0.02em;
	}
	.desc {
		font-size: 0.8125rem;
		color: rgba(255,255,255,0.55);
		max-width: 280px;
		line-height: 1.5;
	}
	.upgrade-btn {
		margin-top: 0.5rem;
		padding: 0.75rem 1.75rem;
		border-radius: 99px;
		border: none;
		background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		color: #041010;
		font-family: inherit;
		font-weight: 800;
		font-size: 0.875rem;
		cursor: pointer;
		box-shadow: 0 6px 20px -4px oklch(75% 0.22 165 / 0.5);
	}
	.hint {
		font-size: 0.6875rem;
		color: rgba(255,255,255,0.3);
	}
</style>
