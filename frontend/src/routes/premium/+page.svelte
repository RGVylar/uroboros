<script lang="ts">
	import { goto } from '$app/navigation';
	import { subscription } from '$lib/stores/subscription.svelte';
	import Aurora from '$lib/components/uro/Aurora.svelte';

	const plans = [
		{
			id: 'monthly',
			label: 'Mensual',
			price: '€5,99',
			period: '/mes',
			highlight: false,
			note: '',
		},
		{
			id: 'annual',
			label: 'Anual',
			price: '€39,99',
			period: '/año',
			highlight: true,
			note: 'Ahorra 40% · €3,33/mes',
		},
		{
			id: 'couple',
			label: 'Pareja',
			price: '€59,99',
			period: '/año',
			highlight: false,
			note: '2 usuarios · €2,50/mes cada uno',
		},
	];

	const premiumFeatures = [
		{ emoji: '📊', text: 'Historial y calendario ilimitado' },
		{ emoji: '📈', text: 'Tendencias y gráficas avanzadas' },
		{ emoji: '💪', text: 'Sesiones de ejercicio' },
		{ emoji: '📏', text: 'Medidas corporales' },
		{ emoji: '🛒', text: 'Inventario y lista de la compra compartidos' },
		{ emoji: '🔥', text: 'Cheat days para proteger la racha' },
		{ emoji: '📤', text: 'Exportar a Excel' },
		{ emoji: '🔔', text: 'Notificaciones avanzadas' },
		{ emoji: '⚙️', text: 'Ajuste de macros proporcional / rendimiento' },
	];

	let selected = $state('annual');

	function subscribe(planId: string) {
		// TODO: integrate RevenueCat / Google Play Billing
		alert('Próximamente — integración con Google Play en proceso');
	}
</script>

<svelte:head>
	<title>Premium — uroboros</title>
</svelte:head>

<Aurora />

<div class="shell">
	<button class="back-btn" onclick={() => goto('/')}>← Atrás</button>

	<!-- Header -->
	<div class="hero">
		<div class="crown">👑</div>
		<h1>uroboros <span class="premium-label">Premium</span></h1>
		<p class="sub">Todo lo que necesitas para cuidarte de verdad</p>
	</div>

	<!-- Trial status (if in trial) -->
	{#if subscription.status === 'trial' && subscription.trial_days_left !== null}
		<div class="trial-box">
			<div class="trial-title">
				{#if subscription.trial_days_left === 0}
					Tu prueba termina hoy
				{:else}
					Te quedan <strong>{subscription.trial_days_left} días</strong> de prueba
				{/if}
			</div>
			<div class="trial-sub">Suscríbete antes de que acabe para no perder nada</div>
		</div>
	{/if}

	<!-- Feature list -->
	<div class="features">
		{#each premiumFeatures as f}
			<div class="feature-row">
				<span class="feature-emoji">{f.emoji}</span>
				<span class="feature-text">{f.text}</span>
			</div>
		{/each}
	</div>

	<!-- Plan selector -->
	<div class="plans">
		{#each plans as plan}
			<button
				class="plan-card"
				class:selected={selected === plan.id}
				class:highlight={plan.highlight}
				onclick={() => selected = plan.id}
			>
				{#if plan.highlight}
					<div class="popular-badge">Más popular</div>
				{/if}
				<div class="plan-label">{plan.label}</div>
				<div class="plan-price">
					{plan.price}<span class="plan-period">{plan.period}</span>
				</div>
				{#if plan.note}
					<div class="plan-note">{plan.note}</div>
				{/if}
			</button>
		{/each}
	</div>

	<!-- Social perk — always visible -->
	<div class="social-box">
		<div class="social-header">
			<span class="social-icon">💑</span>
			<span class="social-title">Con cualquier plan, tu pareja también gana</span>
		</div>
		<div class="social-body">
			Al conectaros en uroboros, si <strong>uno de los dos tiene Premium</strong>, el otro accede automáticamente a las funciones compartidas:
		</div>
		<div class="social-perks">
			<div class="social-perk">🏠 Inventario doméstico compartido</div>
			<div class="social-perk">🛒 Lista de la compra sincronizada</div>
			<div class="social-perk">📖 Recetas compartidas</div>
		</div>
		<div class="social-note">
			Para que <strong>cada uno tenga su propio historial ilimitado, gráficas y medidas personales</strong>, los dos necesitáis Premium — o usar el plan pareja.
		</div>
	</div>

	<!-- Couple plan explainer (shown when couple is selected) -->
	{#if selected === 'couple'}
		<div class="couple-box">
			<div class="couple-title">💑 Cómo funciona el plan pareja</div>
			<div class="couple-rule">
				<span class="couple-check">✓</span>
				<span>Los dos tenéis <strong>Premium completo</strong> — historial, gráficas, medidas, ejercicio, exportar…</span>
			</div>
			<div class="couple-rule">
				<span class="couple-check">✓</span>
				<span><strong>Inventario compartido</strong> — gestiona la despensa, nevera y congelador juntos en tiempo real</span>
			</div>
			<div class="couple-rule">
				<span class="couple-check">✓</span>
				<span><strong>Lista de la compra</strong> sincronizada — uno añade, el otro lo ve al instante</span>
			</div>
			<div class="couple-rule">
				<span class="couple-check">✓</span>
				<span><strong>Recetas compartidas</strong> — cread y compartid vuestras recetas favoritas</span>
			</div>
			<div class="couple-divider"></div>
			<div class="couple-note">
				Con el plan pareja los dos tenéis Premium completo al precio más bajo por persona.
			</div>
		</div>
	{/if}

	<!-- CTA -->
	<button class="cta-btn" onclick={() => subscribe(selected)}>
		Continuar con {plans.find(p => p.id === selected)?.label}
	</button>
	<div class="legal">
		Cancela cuando quieras · Sin permanencia · Gestionado por Google Play
	</div>

	<!-- Free tier reminder -->
	<button class="free-link" onclick={() => goto('/')}>
		Seguir con la versión gratuita
	</button>
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

	.trial-box {
		background: oklch(72% 0.18 55 / 0.12);
		border: 1px solid oklch(72% 0.18 55 / 0.3);
		border-radius: 14px;
		padding: 0.875rem 1rem;
		text-align: center;
		margin-bottom: 1.25rem;
	}
	.trial-title { font-size: 0.9375rem; font-weight: 700; color: oklch(88% 0.14 55); }
	.trial-sub { font-size: 0.75rem; color: rgba(255,255,255,0.45); margin-top: 0.25rem; }

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
	.feature-emoji { font-size: 1.125rem; flex-shrink: 0; }
	.feature-text { color: rgba(255,255,255,0.85); }

	.plans {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}
	.plan-card {
		flex: 1;
		position: relative;
		padding: 0.875rem 0.5rem;
		border-radius: 16px;
		border: 1.5px solid rgba(255,255,255,0.1);
		background: rgba(255,255,255,0.04);
		color: #fff;
		font-family: inherit;
		cursor: pointer;
		text-align: center;
		transition: all 0.15s;
	}
	.plan-card.selected {
		border-color: oklch(75% 0.2 165 / 0.7);
		background: oklch(75% 0.2 165 / 0.08);
	}
	.plan-card.highlight.selected {
		border-color: oklch(88% 0.19 160);
	}
	.popular-badge {
		position: absolute;
		top: -10px;
		left: 50%;
		transform: translateX(-50%);
		background: linear-gradient(90deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		color: #041010;
		font-size: 0.6rem;
		font-weight: 800;
		padding: 2px 8px;
		border-radius: 99px;
		white-space: nowrap;
	}
	.plan-label { font-size: 0.6875rem; color: rgba(255,255,255,0.5); margin-bottom: 0.25rem; }
	.plan-price { font-size: 1.125rem; font-weight: 800; }
	.plan-period { font-size: 0.6875rem; font-weight: 400; color: rgba(255,255,255,0.45); }
	.plan-note { font-size: 0.6rem; color: oklch(85% 0.17 160); margin-top: 0.25rem; }

	.cta-btn {
		width: 100%;
		height: 54px;
		border-radius: 16px;
		border: none;
		background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		color: #041010;
		font-family: inherit;
		font-weight: 800;
		font-size: 1rem;
		cursor: pointer;
		box-shadow: 0 8px 24px -6px oklch(75% 0.22 165 / 0.55);
		margin-bottom: 0.625rem;
	}
	.legal {
		text-align: center;
		font-size: 0.6875rem;
		color: rgba(255,255,255,0.3);
		margin-bottom: 1.5rem;
	}
	.free-link {
		display: block;
		width: 100%;
		background: none;
		border: none;
		color: rgba(255,255,255,0.35);
		font-family: inherit;
		font-size: 0.8125rem;
		cursor: pointer;
		text-align: center;
		padding: 0.5rem;
	}
	.free-link:hover { color: rgba(255,255,255,0.6); }

	/* ── Social perk (always visible) ── */
	.social-box {
		background: oklch(72% 0.2 170 / 0.06);
		border: 1px solid oklch(72% 0.2 170 / 0.2);
		border-radius: 16px;
		padding: 1rem 1.125rem;
		margin-bottom: 1rem;
		display: flex;
		flex-direction: column;
		gap: 0.625rem;
	}
	.social-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	.social-icon { font-size: 1.125rem; flex-shrink: 0; }
	.social-title {
		font-size: 0.875rem;
		font-weight: 800;
		color: oklch(88% 0.19 160);
	}
	.social-body {
		font-size: 0.8125rem;
		color: rgba(255,255,255,0.7);
		line-height: 1.4;
	}
	.social-perks {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
		padding-left: 0.25rem;
	}
	.social-perk {
		font-size: 0.8125rem;
		color: rgba(255,255,255,0.85);
		font-weight: 600;
	}
	.social-note {
		font-size: 0.75rem;
		color: rgba(255,255,255,0.4);
		line-height: 1.5;
		border-top: 1px solid rgba(255,255,255,0.07);
		padding-top: 0.5rem;
		margin-top: 0.125rem;
	}

	/* ── Couple explainer ── */
	.couple-box {
		background: oklch(72% 0.2 170 / 0.08);
		border: 1px solid oklch(72% 0.2 170 / 0.25);
		border-radius: 16px;
		padding: 1rem 1.125rem;
		margin-bottom: 1rem;
		display: flex;
		flex-direction: column;
		gap: 0.625rem;
	}
	.couple-title {
		font-size: 0.875rem;
		font-weight: 800;
		color: oklch(88% 0.19 160);
		margin-bottom: 0.125rem;
	}
	.couple-rule {
		display: flex;
		gap: 0.625rem;
		font-size: 0.8125rem;
		color: rgba(255,255,255,0.8);
		line-height: 1.4;
	}
	.couple-check {
		color: oklch(85% 0.19 160);
		font-weight: 800;
		flex-shrink: 0;
		margin-top: 0.05rem;
	}
	.couple-divider {
		border-top: 1px solid rgba(255,255,255,0.08);
		margin: 0.25rem 0;
	}
	.couple-note {
		font-size: 0.75rem;
		color: rgba(255,255,255,0.45);
		line-height: 1.5;
	}
</style>
