<script lang="ts">
	/**
	 * Escaneo de tickets — PROVISIONAL, detrás del flag `receipt_scan`.
	 *
	 * Enseña el OCR en crudo a propósito: todavía no hay parser, y lo que hace
	 * falta ahora es ver salida real de tickets de verdad para construirlo. La
	 * pantalla de revisión y el volcado a la despensa vienen después.
	 *
	 * `capture="environment"` hace que en el móvil el input abra directamente la
	 * cámara trasera en vez del carrete. En escritorio se ignora y sale el
	 * selector de ficheros de siempre, que es justo lo que quieres allí.
	 */
	import { api } from '$lib/api';
	import type { ReceiptScan } from '$lib/types';

	let fileInput: HTMLInputElement | undefined = $state();
	let busy = $state(false);
	let error = $state('');
	let result: ReceiptScan | null = $state(null);

	async function onPick(e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;

		busy = true;
		error = '';
		result = null;
		try {
			const form = new FormData();
			form.append('file', file);
			result = await api.upload<ReceiptScan>('/receipts/scan', form);
		} catch (err: unknown) {
			error = err instanceof Error ? err.message : 'No se ha podido leer el ticket';
		} finally {
			busy = false;
			// Sin esto, elegir la misma foto dos veces no dispara el change.
			input.value = '';
		}
	}
</script>

<div
	style="background:rgba(255,255,255,0.04); border:1px dashed rgba(255,255,255,0.18); border-radius:16px; padding:0.875rem; margin-bottom:0.75rem;"
>
	<div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.625rem;">
		<span style="font-size:0.8125rem; color:#fff; font-weight:600;">Escanear ticket</span>
		<span
			style="font-size:0.625rem; padding:0.125rem 0.375rem; border-radius:99px; background:rgba(255,255,255,0.1); color:rgba(255,255,255,0.6);"
			>en pruebas</span
		>
	</div>

	<input
		bind:this={fileInput}
		type="file"
		accept="image/*"
		capture="environment"
		onchange={onPick}
		style="display:none;"
	/>

	<button
		onclick={() => fileInput?.click()}
		disabled={busy}
		style="width:100%; padding:0.625rem; border-radius:12px; border:1px solid rgba(255,255,255,0.14); background:rgba(255,255,255,0.06); color:#fff; font-family:inherit; font-size:0.8125rem; cursor:pointer;"
	>
		{busy ? 'Leyendo…' : 'Hacer foto al ticket'}
	</button>

	{#if error}
		<div style="margin-top:0.5rem; font-size:0.75rem; color:oklch(70% 0.17 25);">{error}</div>
	{/if}

	{#if result}
		<div style="margin-top:0.625rem; font-size:0.6875rem; color:rgba(255,255,255,0.5);">
			{result.words.length} palabras · imagen {result.image_width}×{result.image_height}
		</div>
		<pre
			style="margin-top:0.375rem; max-height:260px; overflow:auto; font-size:0.6875rem; line-height:1.45; color:rgba(255,255,255,0.8); background:rgba(0,0,0,0.25); border-radius:10px; padding:0.5rem; white-space:pre-wrap; word-break:break-word;">{result.text ||
				'(sin texto)'}</pre>
	{/if}
</div>
