<script lang="ts">
	// Botón de escanear código de barras suelto, para ponerlo junto a un campo
	// que ya existe (p. ej. el código de barras de una receta). En la APK abre el
	// escáner nativo; en la web, la cámara en línea debajo. Quien lo use pone el
	// contenedor con flex-wrap para que el vídeo baje a su propia fila.
	import Icon from './Icon.svelte';
	import { t } from '$lib/i18n/index.svelte';
	import { onDestroy, tick } from 'svelte';
	import { Capacitor } from '@capacitor/core';

	let { onScan }: { onScan: (barcode: string) => void } = $props();

	const isNative = Capacitor.isNativePlatform();
	let scanning = $state(false);
	let scanError = $state('');
	let videoEl: HTMLVideoElement | undefined = $state();
	let controls: import('@zxing/browser').IScannerControls | null = null;

	async function startWebScan() {
		scanError = '';
		scanning = true;
		try {
			const { BrowserMultiFormatReader } = await import('@zxing/browser');
			await tick();
			if (!videoEl) return;
			// controls.stop() apaga la cámara y el bucle de lectura a la vez.
			controls = await new BrowserMultiFormatReader().decodeFromConstraints(
				{ video: { facingMode: 'environment' } },
				videoEl,
				(result) => {
					if (result) {
						stopScan();
						onScan(result.getText());
					}
				},
			);
			// Cerrado (o ya leído) mientras arrancaba la cámara.
			if (!scanning) stopScan();
		} catch (e: unknown) {
			const name = e instanceof DOMException ? e.name : '';
			scanError = name === 'NotAllowedError' ? t('shopping.errCameraDenied') : t('shopping.errCamera');
			stopScan();
		}
	}

	function stopScan() {
		scanning = false;
		controls?.stop();
		controls = null;
	}

	async function scanNative() {
		scanError = '';
		try {
			const { BarcodeScanner } = await import('@capacitor-mlkit/barcode-scanning');
			const { supported } = await BarcodeScanner.isSupported();
			if (!supported) { scanError = t('shopping.errScannerUnsupported'); return; }
			const granted = await BarcodeScanner.requestPermissions();
			if (granted.camera !== 'granted') { scanError = t('shopping.errCameraDenied'); return; }
			const { barcodes } = await BarcodeScanner.scan();
			const code = barcodes[0]?.rawValue;
			if (code) onScan(code);
		} catch {
			scanError = t('shopping.errScanner');
		}
	}

	onDestroy(() => stopScan());
</script>

<button
	type="button"
	class="scan-btn"
	onclick={isNative ? scanNative : startWebScan}
	disabled={scanning}
	aria-label={t('scanner.aria')}
>
	<svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
		<path d="M4 6v12M7 6v12M10 6v12M13 6v12M17 6v12M20 6v12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
	</svg>
</button>

{#if scanning}
	<div class="scan-video">
		<!-- svelte-ignore a11y_media_has_caption -->
		<video bind:this={videoEl} playsinline></video>
		<button type="button" class="scan-stop" onclick={stopScan} aria-label={t('scanner.stopAria')}>
			<Icon name="close" />
		</button>
	</div>
{/if}

{#if scanError}
	<p class="scan-error">{scanError}</p>
{/if}

<style>
	.scan-btn {
		width: 44px;
		height: 44px;
		flex-shrink: 0;
		border-radius: 12px;
		border: 1px solid rgba(255, 255, 255, 0.1);
		background: rgba(255, 255, 255, 0.06);
		color: oklch(85% 0.15 160);
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 0;
		transition: background 0.15s;
	}
	.scan-btn:hover { background: rgba(255, 255, 255, 0.1); }
	.scan-btn:disabled { opacity: 0.5; cursor: default; }
	.scan-video {
		flex-basis: 100%;
		width: 100%;
		position: relative;
	}
	.scan-video video {
		width: 100%;
		border-radius: 16px;
		background: #000;
		display: block;
	}
	.scan-stop {
		position: absolute;
		top: 0.5rem;
		right: 0.5rem;
		width: 32px;
		height: 32px;
		border-radius: 50%;
		background: rgba(0, 0, 0, 0.6);
		border: none;
		color: #fff;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.scan-error {
		flex-basis: 100%;
		color: oklch(75% 0.2 25);
		font-size: 0.75rem;
		margin: 0;
	}
</style>
