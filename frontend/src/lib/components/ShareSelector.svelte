<script lang="ts">
	// Para quién se registra: solo yo, los dos, o solo la pareja. Lo usan el
	// detalle de un producto y el de una olla. Los subtítulos se pueden cambiar
	// (en una olla dicen cuánto se lleva cada uno).
	import Icon from '$lib/components/Icon.svelte';
	import { t } from '$lib/i18n/index.svelte';
	import type { ShareMode } from '$lib/types';

	let {
		mode = $bindable(null),
		partnerName,
		subNone,
		subAlso,
		subOnly,
		style = '',
	}: {
		mode?: ShareMode;
		partnerName: string;
		subNone?: string;
		subAlso?: string;
		subOnly?: string;
		style?: string;
	} = $props();
</script>

<div class="share-card" class:share-card-also={mode === 'also'} class:share-card-only={mode === 'only'} {style}>
	<div class="share-badge-icon" class:share-badge-icon-also={mode === 'also'} class:share-badge-icon-only={mode === 'only'}>
		{#if mode === null}<Icon name="user" />{:else if mode === 'also'}<Icon name="users" />{:else}<Icon name="forPartner" />{/if}
	</div>
	<div style="flex:1; min-width:0; text-align:left;">
		{#if mode === null}
			<div style="font-size:0.8125rem; font-weight:700; color:rgba(255,255,255,0.5);">{t('add.shareNone')}</div>
			<div class="share-sub" style="color:rgba(255,255,255,0.35);">{subNone ?? t('add.shareNoneSub')}</div>
		{:else if mode === 'also'}
			<div style="font-size:0.8125rem; font-weight:700;">{t('add.shareAlsoTitle', { name: partnerName })}</div>
			<div class="share-sub">{subAlso ?? t('add.shareBothSub')}</div>
		{:else}
			<div style="font-size:0.8125rem; font-weight:700; color:oklch(80% 0.18 45);">{t('add.shareOnlyTitle', { name: partnerName })}</div>
			<div class="share-sub">{subOnly ?? t('add.shareOnlyPartnerSub')}</div>
		{/if}
	</div>
	<!-- Segmented pill con sliding thumb -->
	<div class="seg-pill">
		<div class="seg-pill-thumb" style="
			left: {mode === null ? '3px' : mode === 'also' ? '33px' : '63px'};
			background: {mode === 'only'
				? 'linear-gradient(135deg, oklch(85% 0.18 45), oklch(68% 0.22 40))'
				: mode === 'also'
					? 'linear-gradient(135deg, oklch(82% 0.18 160), oklch(68% 0.2 170))'
					: 'rgba(255,255,255,0.12)'};
		"></div>
		<button class="seg-pill-btn" class:seg-pill-active={mode === null}
			onclick={() => (mode = null)} aria-label={t('add.shareOnlyMe')}><Icon name="user" /></button>
		<button class="seg-pill-btn" class:seg-pill-active={mode === 'also'}
			onclick={() => (mode = 'also')} aria-label={t('add.shareBoth')}><Icon name="users" /></button>
		<button class="seg-pill-btn" class:seg-pill-active={mode === 'only'}
			onclick={() => (mode = 'only')} aria-label={t('add.shareOnlyPartner', { name: partnerName })}><Icon name="forPartner" /></button>
	</div>
</div>

<style>
	.share-card {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		width: 100%;
		background: rgba(255,255,255,0.05);
		border: 1px solid rgba(255,255,255,0.09);
		border-radius: 20px;
		padding: 0.875rem;
		transition: background 0.25s, border-color 0.25s;
	}
	.share-card-also {
		background: oklch(75% 0.18 165 / 0.08);
		border-color: oklch(80% 0.17 165 / 0.3);
	}
	.share-card-only {
		background: oklch(65% 0.2 45 / 0.08);
		border-color: oklch(70% 0.2 45 / 0.3);
	}
	.share-sub { font-size: 0.6875rem; color: rgba(255,255,255,0.55); margin-top: 0.125rem; }
	.share-badge-icon {
		width: 40px;
		height: 40px;
		border-radius: 12px;
		background: rgba(255,255,255,0.06);
		border: 1px solid rgba(255,255,255,0.08);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1.125rem;
		flex-shrink: 0;
		transition: background 0.25s, border-color 0.25s;
	}
	.share-badge-icon-also {
		background: oklch(75% 0.18 165 / 0.18);
		border-color: oklch(80% 0.17 165 / 0.4);
	}
	.share-badge-icon-only {
		background: oklch(65% 0.2 45 / 0.18);
		border-color: oklch(70% 0.2 45 / 0.4);
	}

	/* ── Segmented pill con sliding thumb ── */
	.seg-pill {
		position: relative;
		display: flex;
		background: rgba(255,255,255,0.06);
		border: 1px solid rgba(255,255,255,0.1);
		border-radius: 99px;
		padding: 3px;
		gap: 2px;
		flex-shrink: 0;
	}
	.seg-pill-thumb {
		position: absolute;
		top: 3px;
		width: 28px;
		height: 28px;
		border-radius: 99px;
		box-shadow: 0 2px 8px rgba(0,0,0,0.35);
		transition: left 0.28s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.22s ease;
		pointer-events: none;
		z-index: 1;
	}
	.seg-pill-btn {
		width: 28px;
		height: 28px;
		border-radius: 99px;
		border: none;
		background: transparent;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.75rem;
		position: relative;
		z-index: 2;
		opacity: 0.3;
		transition: opacity 0.18s;
		padding: 0;
		line-height: 1;
	}
	.seg-pill-active { opacity: 1; }
</style>
