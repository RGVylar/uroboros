<script lang="ts">
	import { goto } from '$app/navigation';
	import { subscription } from '$lib/stores/subscription.svelte';
	import Aurora from '$lib/components/uro/Aurora.svelte';
	import { t } from '$lib/i18n/index.svelte';

	// Premium features shown as a teaser. Pricing and purchase are intentionally
	// NOT here yet: Google Play rejects apps that show prices with a buy button
	// that doesn't complete a purchase. Billing (Play Billing / RevenueCat) will
	// be wired up in a later version — until then this is a "coming soon" page.
	let premiumFeatures = $derived([
		{ emoji: '📈', text: t('premium.feat1') },
		{ emoji: '💪', text: t('premium.feat2') },
		{ emoji: '📏', text: t('premium.feat3') },
		{ emoji: '🛒', text: t('premium.feat4') },
		{ emoji: '📖', text: t('premium.feat5') },
		{ emoji: '🔥', text: t('premium.feat6') },
		{ emoji: '📤', text: t('premium.feat7') },
		{ emoji: '♾️', text: t('premium.feat8') },
	]);
</script>

<svelte:head>
	<title>{t('premium.pageTitle')}</title>
</svelte:head>

<Aurora />

<div class="shell">
	<button class="back-btn" onclick={() => goto('/')}>{t('premium.back')}</button>

	<!-- Header -->
	<div class="hero">
		<div class="crown">👑</div>
		<h1>uroboros <span class="premium-label">Premium</span></h1>
		<p class="sub">{t('premium.tagline')}</p>
	</div>

	{#if subscription.is_premium}
		<!-- Grandfathered / premium users already have everything -->
		<div class="status-box ok">
			<div class="status-title">{t('premium.haveAccess')}</div>
			<div class="status-sub">{t('premium.haveAccessSub')}</div>
		</div>

		<div class="features">
			{#each premiumFeatures as f}
				<div class="feature-row">
					<span class="feature-emoji">{f.emoji}</span>
					<span class="feature-text">{f.text}</span>
				</div>
			{/each}
		</div>
	{:else}
		<!-- Free users: teaser of what's coming -->
		<div class="status-box soon">
			<div class="status-title">{t('premium.soon')}</div>
			<div class="status-sub">{t('premium.soonSub')}</div>
		</div>

		<div class="features">
			{#each premiumFeatures as f}
				<div class="feature-row locked">
					<span class="feature-emoji">{f.emoji}</span>
					<span class="feature-text">{f.text}</span>
					<span class="lock">🔒</span>
				</div>
			{/each}
		</div>

		<button class="cta-btn" onclick={() => goto('/')}>
			Seguir con la versión gratuita
		</button>
	{/if}
</div>

<style>
	.shell {
		position: relative;
		z-index: 1;
		max-width: 480px;
		margin: 0 auto;
		padding: 24px 16px 80px;
		min-height: 100dvh;
		color: #fff;
	}
	.back-btn {
		padding: 8px 14px;
		border-radius: 99px;
		background: rgba(255,255,255,0.05);
		border: 1px solid rgba(255,255,255,0.1);
		color: rgba(255,255,255,0.7);
		font-family: inherit;
		font-size: 13px;
		cursor: pointer;
		margin-bottom: 1.5rem;
	}

	.hero {
		text-align: center;
		margin-bottom: 1.5rem;
	}
	.crown { font-size: 2.5rem; margin-bottom: 0.5rem; }
	h1 {
		font-size: 1.75rem;
		font-weight: 800;
		letter-spacing: -0.04em;
		margin: 0 0 0.25rem;
	}
	.premium-label {
		background: linear-gradient(90deg, oklch(88% 0.19 160), oklch(80% 0.18 200));
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
	}
	.sub { font-size: 0.875rem; color: rgba(255,255,255,0.5); margin: 0; }

	.status-box {
		border-radius: 16px;
		padding: 1rem 1.125rem;
		text-align: center;
		margin-bottom: 1.25rem;
	}
	.status-box.soon {
		background: oklch(72% 0.2 170 / 0.08);
		border: 1px solid oklch(72% 0.2 170 / 0.25);
	}
	.status-box.ok {
		background: oklch(72% 0.18 145 / 0.1);
		border: 1px solid oklch(72% 0.18 145 / 0.3);
	}
	.status-title { font-size: 1rem; font-weight: 800; color: oklch(88% 0.19 160); margin-bottom: 0.35rem; }
	.status-sub { font-size: 0.8125rem; color: rgba(255,255,255,0.6); line-height: 1.45; }

	.features {
		background: rgba(255,255,255,0.04);
		border: 1px solid rgba(255,255,255,0.08);
		border-radius: 16px;
		padding: 0.75rem 1rem;
		margin-bottom: 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 0.625rem;
	}
	.feature-row { display: flex; align-items: center; gap: 0.75rem; font-size: 0.875rem; }
	.feature-row.locked { opacity: 0.7; }
	.feature-emoji { font-size: 1.125rem; flex-shrink: 0; }
	.feature-text { color: rgba(255,255,255,0.85); flex: 1; }
	.lock { font-size: 0.8125rem; opacity: 0.6; }

	.cta-btn {
		width: 100%;
		height: 54px;
		border-radius: 16px;
		border: none;
		background: rgba(255,255,255,0.06);
		border: 1px solid rgba(255,255,255,0.12);
		color: rgba(255,255,255,0.85);
		font-family: inherit;
		font-weight: 700;
		font-size: 0.9375rem;
		cursor: pointer;
	}
</style>
