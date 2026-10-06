<!--
  BugReportModal.svelte
  "Reportar un problema" desde Ajustes. La persona solo escribe qué ha pasado
  (y si quiere adjunta una captura); versión, plataforma, idioma y pantalla los
  pone la app. El primer bug de la beta costó una tarde porque venía de un APK
  de julio y nadie lo sabía: con la versión en el informe se ve a la primera.
-->
<script lang="ts">
	import Icon from './Icon.svelte';
	import { Capacitor } from '@capacitor/core';
	import { api } from '$lib/api';
	import { APP_VERSION } from '$lib/changelog';
	import { t, i18n } from '$lib/i18n/index.svelte';
	import { toast } from '$lib/stores/toast.svelte';
	import Modal from './Modal.svelte';

	interface Props {
		onClose: () => void;
		/** Pantalla en la que estaba antes de entrar en Ajustes. */
		fromRoute?: string;
	}
	let { onClose, fromRoute = '' }: Props = $props();

	let message = $state('');
	let screenshot = $state<File | null>(null);
	let sending = $state(false);
	let error = $state('');

	// 'android' | 'ios' en la app nativa; en navegador, PWA instalada o web suelta.
	function platform(): string {
		const native = Capacitor.getPlatform();
		if (native !== 'web') return native;
		return window.matchMedia('(display-mode: standalone)').matches ? 'pwa' : 'web';
	}

	function pickScreenshot(e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		screenshot = input.files?.[0] ?? null;
	}

	async function send() {
		if (!message.trim() || sending) return;
		sending = true;
		error = '';
		const form = new FormData();
		form.append('message', message.trim());
		form.append('app_version', APP_VERSION);
		form.append('platform', platform());
		form.append('locale', i18n.locale);
		form.append('route', fromRoute);
		if (screenshot) form.append('screenshot', screenshot);
		try {
			await api.upload('/feedback', form);
			toast.success(t('bugReport.sent'));
			onClose();
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : t('bugReport.error');
		} finally {
			sending = false;
		}
	}
</script>

<Modal {onClose} title={t('bugReport.title')} subtitle={t('bugReport.subtitle')}>
	<textarea
		bind:value={message}
		placeholder={t('bugReport.placeholder')}
		maxlength="2000"
		rows="5"
		style="width:100%; resize:vertical; font-family:inherit;"
	></textarea>

	<!-- text-transform y compañía: el `label` global es el de los títulos de campo -->
	<label style="display:flex; align-items:center; gap:0.625rem; margin-top:0.625rem; text-transform:none; letter-spacing:normal; font-weight:400; padding:0.625rem 0.75rem; border-radius:12px; border:1px dashed rgba(255,255,255,0.15); background:rgba(255,255,255,0.03); cursor:pointer;">
		<Icon name="attach" size="1.125rem" />
		<span style="flex:1; min-width:0; font-size:0.75rem; color:rgba(255,255,255,0.65); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
			{screenshot ? screenshot.name : t('bugReport.attach')}
		</span>
		{#if screenshot}
			<button type="button" onclick={(e) => { e.preventDefault(); screenshot = null; }} aria-label={t('bugReport.removeAttach')}
				style="padding:0.125rem 0.5rem; border-radius:8px; border:1px solid rgba(255,255,255,0.12); background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.6); font-size:0.75rem; font-family:inherit; cursor:pointer; box-shadow:none;"><Icon name="close" /></button>
		{/if}
		<input type="file" accept="image/*" onchange={pickScreenshot} style="display:none;" />
	</label>

	<!-- Lo que se adjunta solo, a la vista: que nadie se sorprenda de qué se manda -->
	<p style="font-size:0.6875rem; color:rgba(255,255,255,0.45); margin:0.625rem 0 0; line-height:1.45;">
		{t('bugReport.context', { version: APP_VERSION })}
	</p>

	{#if error}<p style="color:oklch(75% 0.2 25); font-size:0.75rem; margin:0.5rem 0 0;">{error}</p>{/if}

	<div style="display:flex; gap:0.5rem; margin-top:0.875rem;">
		<button class="btn-secondary" onclick={onClose} style="flex:1;">{t('common.cancel')}</button>
		<button onclick={send} disabled={sending || !message.trim()} style="flex:1;">
			{sending ? '...' : t('bugReport.send')}
		</button>
	</div>
</Modal>
