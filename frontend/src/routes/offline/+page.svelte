<!--
	Por qué no hay conexión. Se llega desde el aviso "Sin conexión" del layout.
	Va dentro de la app (no pide nada al servidor), así que se puede leer
	justo cuando hace falta: sin conexión.
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import Aurora from '$lib/components/uro/Aurora.svelte';
	import ScreenHeader from '$lib/components/uro/ScreenHeader.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import type { IconName } from '$lib/icons';
	import { connectivity } from '$lib/stores/connectivity.svelte';
	import { syncQueue } from '$lib/stores/sync-queue.svelte';
	import { t, tc } from '$lib/i18n/index.svelte';

	function goBack() {
		if (history.length > 1) history.back();
		else goto('/');
	}

	const SECTIONS: { icon: IconName; key: 'what' | 'safe' | 'vpn' | 'why'; color: string }[] = [
		{ icon: 'sport', key: 'what', color: 'oklch(80% 0.14 60)' },
		{ icon: 'success', key: 'safe', color: 'var(--primary)' },
		{ icon: 'globe', key: 'vpn', color: 'var(--water)' },
		{ icon: 'info', key: 'why', color: 'oklch(80% 0.13 300)' },
	];
</script>

<svelte:head><title>{t('offline.title')} — uroboros</title></svelte:head>

<Aurora />

<div class="wrap">
	<ScreenHeader title={t('offline.title')} onBack={goBack} />

	<div class="status" class:on={!connectivity.isOffline}>
		<Icon name={connectivity.isOffline ? 'offline' : 'check'} />
		<div>
			<div class="status-title">{connectivity.isOffline ? t('offline.statusOff') : t('offline.statusOn')}</div>
			{#if syncQueue.count > 0}
				<div class="status-sub">{tc('offline.pending', syncQueue.count)}</div>
			{/if}
		</div>
	</div>

	{#each SECTIONS as s (s.key)}
		<section class="card sec" style="--c:{s.color}">
			<div class="sec-icon"><Icon name={s.icon} /></div>
			<div>
				<h2>{t(`offline.${s.key}.title`)}</h2>
				<p>{t(`offline.${s.key}.body`)}</p>
			</div>
		</section>
	{/each}
</div>

<style>
	.wrap {
		position: relative;
		z-index: 1;
		max-width: 640px;
		margin: 0 auto;
		padding: 0 0 6rem;
	}
	.status {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin: 0.5rem 0 1rem;
		padding: 0.8rem 1rem;
		border-radius: 14px;
		font-size: 1.1rem;
		color: oklch(80% 0.05 260);
		background: oklch(28% 0.04 260 / 0.6);
		border: 1px solid oklch(45% 0.06 260 / 0.4);
	}
	.status.on {
		color: var(--primary);
		background: oklch(75% 0.15 160 / 0.1);
		border-color: oklch(75% 0.15 160 / 0.3);
	}
	.status-title { font-size: 0.875rem; font-weight: 700; }
	.status-sub { font-size: 0.75rem; color: var(--text-muted); margin-top: 0.1rem; }
	.sec {
		display: flex;
		gap: 0.85rem;
		align-items: flex-start;
		margin-bottom: 0.75rem;
	}
	.sec-icon {
		flex-shrink: 0;
		width: 36px;
		height: 36px;
		border-radius: 11px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1.05rem;
		color: var(--c);
		background: color-mix(in oklch, var(--c) 18%, transparent);
	}
	h2 { margin: 0.15rem 0 0.3rem; font-size: 0.95rem; font-weight: 700; }
	p { margin: 0; font-size: 0.82rem; line-height: 1.55; color: var(--text-muted); }
</style>
