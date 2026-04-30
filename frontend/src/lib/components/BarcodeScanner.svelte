<script lang="ts">
	import { onDestroy } from 'svelte';

	interface Props {
		onScan: (barcode: string) => void;
		onError?: (error: string) => void;
	}

	let { onScan, onError }: Props = $props();

	let scanning = $state(false);
	let scanError = $state('');
	let videoEl: HTMLVideoElement | undefined = $state();
	let stream: MediaStream | null = null;
	let zxingReader: import('@zxing/browser').BrowserMultiFormatReader | null = null;

	async function startScan() {
		scanError = '';
		scanning = true;
		try {
			const { BrowserMultiFormatReader } = await import('@zxing/browser');
			zxingReader = new BrowserMultiFormatReader();
			stream = await navigator.mediaDevices.getUserMedia({
				video: { facingMode: 'environment' }
			});
			if (videoEl) {
				videoEl.srcObject = stream;
				videoEl.play();
				zxingReader.decodeFromVideoElement(videoEl, (result, err) => {
					if (result) {
						const barcode = result.getText();
						stopScan();
						onScan(barcode);
					}
				});
			}
		} catch (e: unknown) {
			const msg = e instanceof Error ? e.message : 'No se pudo acceder a la cámara';
			scanError = msg;
			onError?.(msg);
			scanning = false;
		}
	}

	function stopScan() {
		scanning = false;
		if (stream) {
			stream.getTracks().forEach(t => t.stop());
			stream = null;
		}
		if (zxingReader) {
			zxingReader.reset();
			zxingReader = null;
		}
	}

	onDestroy(() => {
		stopScan();
	});
</script>

{#if scanning}
	<div style="position:fixed; top:0; left:0; right:0; bottom:0; background:black; z-index:1000; display:flex; flex-direction:column; align-items:center; justify-content:center;">
		<video bind:this={videoEl} style="width:100%; height:100%; object-fit:cover;"></video>
		<div style="position:absolute; top:0; left:0; right:0; bottom:0; border:3px solid #0f0; pointer-events:none; display:flex; align-items:center; justify-content:center;">
			<div style="width:200px; height:200px; border:2px solid #0f0; border-radius:10px;"></div>
		</div>
		<button
			onclick={stopScan}
			style="position:absolute; top:2rem; right:2rem; width:50px; height:50px; border-radius:50%; background:#f00; color:#fff; border:none; font-size:1.5rem; cursor:pointer; z-index:1001;"
		>
			✕
		</button>
		{#if scanError}
			<div style="position:absolute; bottom:2rem; left:1rem; right:1rem; background:rgba(255,0,0,0.8); color:#fff; padding:1rem; border-radius:10px; text-align:center;">
				{scanError}
			</div>
		{/if}
	</div>
{:else}
	<button
		onclick={startScan}
		style="width:100%; padding:0.75rem; border-radius:12px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.05); color:#fff; cursor:pointer; font-family:inherit; font-weight:600; display:flex; align-items:center; justify-content:center; gap:0.5rem;"
	>
		📷 Escanear código de barras
	</button>
{/if}
