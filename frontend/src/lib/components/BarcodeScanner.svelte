<script lang="ts">
	import { onDestroy } from 'svelte';
	import { Capacitor } from '@capacitor/core';

	interface Props {
		onScan: (barcode: string) => void;
		placeholder?: string;
		bind_query?: string;
		onSearch?: () => void;
	}

	let { onScan, placeholder = 'Buscar...', bind_query = $bindable(''), onSearch }: Props = $props();

	let isNative = Capacitor.isNativePlatform();
	let scanning = $state(false);
	let scanError = $state('');
	let videoEl: HTMLVideoElement | undefined = $state();
	let stream: MediaStream | null = null;
	let zxingReader: import('@zxing/browser').BrowserMultiFormatReader | null = null;

	async function startWebScan() {
		scanError = '';
		scanning = true;
		try {
			const { BrowserMultiFormatReader } = await import('@zxing/browser');
			zxingReader = new BrowserMultiFormatReader();
			stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
			if (videoEl) {
				videoEl.srcObject = stream;
				videoEl.play();
				zxingReader.decodeFromVideoElement(videoEl, (result) => {
					if (result) {
						stopScan();
						onScan(result.getText());
					}
				});
			}
		} catch (e: unknown) {
			scanError = e instanceof Error ? e.message : 'No se pudo acceder a la cámara';
			scanning = false;
		}
	}

	function stopScan() {
		scanning = false;
		if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
		if (zxingReader) { zxingReader.reset(); zxingReader = null; }
	}

	async function scanNative() {
		try {
			const { BarcodeScanner } = await import('@capacitor-mlkit/barcode-scanning');
			const { supported } = await BarcodeScanner.isSupported();
			if (!supported) { scanError = 'Escáner no soportado'; return; }
			const granted = await BarcodeScanner.requestPermissions();
			if (granted.camera !== 'granted') { scanError = 'Permiso de cámara denegado'; return; }
			const { barcodes } = await BarcodeScanner.scan();
			if (barcodes.length > 0) onScan(barcodes[0].rawValue);
		} catch (e: unknown) {
			scanError = e instanceof Error ? e.message : 'Error del escáner';
		}
	}

	onDestroy(() => stopScan());
</script>

<!-- Search bar + barcode button -->
<div style="display:flex; align-items:center; gap:0.375rem; background:rgba(255,255,255,0.05); backdrop-filter:blur(24px) saturate(160%); -webkit-backdrop-filter:blur(24px) saturate(160%); border:1px solid rgba(255,255,255,0.09); border-radius:16px; padding:0.375rem 0.5rem;">
	<svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true" style="color:rgba(255,255,255,0.4); flex-shrink:0; margin:0 0.125rem 0 0.125rem;">
		<circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2"/>
		<path d="M16.5 16.5l4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
	</svg>
	<input
		bind:value={bind_query}
		{placeholder}
		onkeydown={(e) => { if (e.key === 'Enter') onSearch?.(); }}
		style="flex:1; background:none; border:none; outline:none; color:#fff; font-family:inherit; font-size:0.875rem; padding:0.5rem 0;"
	/>
	<button
		onclick={isNative ? scanNative : startWebScan}
		disabled={scanning}
		aria-label="Escanear código de barras"
		style="width:38px; height:38px; border-radius:12px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.06); color:oklch(85% 0.15 160); cursor:pointer; display:flex; align-items:center; justify-content:center; flex-shrink:0; transition:background 0.15s; padding:0;"
	>
		<svg width="20" height="20" viewBox="0 0 24 24" fill="none">
			<path d="M4 6v12M7 6v12M10 6v12M13 6v12M17 6v12M20 6v12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
		</svg>
	</button>
</div>

<!-- Video inline (igual que /add) -->
{#if scanning}
	<div style="margin-bottom:0.75rem; position:relative;">
		<!-- svelte-ignore a11y_media_has_caption -->
		<video bind:this={videoEl} style="width:100%; border-radius:16px; background:#000;" playsinline></video>
		<button
			onclick={stopScan}
			style="position:absolute; top:0.5rem; right:0.5rem; width:32px; height:32px; border-radius:50%; background:rgba(0,0,0,0.6); border:none; color:#fff; cursor:pointer; display:flex; align-items:center; justify-content:center;"
			aria-label="Detener escáner"
		>✕</button>
	</div>
{/if}

{#if scanError}
	<p style="color:oklch(75% 0.2 25); font-size:0.75rem; margin:0 0 0.5rem;">{scanError}</p>
{/if}
