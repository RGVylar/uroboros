<script lang="ts">
	/**
	 * Escaneo de tickets — detrás del flag `receipt_scan`.
	 *
	 * La regla que manda en esta pantalla: **nada entra en la despensa sin que
	 * alguien lo confirme**. Con un emparejado que acierta bastante pero no
	 * siempre, escribir directo significa corregir más de lo que se ahorra.
	 *
	 * Por eso cada línea llega con una decisión ya tomada por defecto, pero
	 * visible y reversible: lo que viene de un alias se da por bueno (es una
	 * decisión anterior del propio usuario), y lo que viene de un parecido se
	 * propone pero se marca como opinión nuestra.
	 *
	 * `capture="environment"` abre la cámara trasera en el móvil; en escritorio
	 * se ignora y sale el selector de ficheros, que es lo que quieres allí.
	 */
	import { api } from '$lib/api';
	import type { Product, ReceiptApplyResult, ReceiptLine, ReceiptScan } from '$lib/types';

	interface Props {
		onApplied?: () => void;
	}
	let { onApplied }: Props = $props();

	type Action = 'add' | 'ignore' | 'skip';
	type Row = {
		raw: string;
		quantity: number;
		unit: string;
		amount: number | null;
		arithmetic_ok: boolean | null;
		productId: number | null;
		productName: string;
		source: string;
		confident: boolean;
		action: Action;
		query: string;
		results: Product[];
		searching: boolean;
	};

	let fileInput: HTMLInputElement | undefined = $state();
	let busy = $state(false);
	let applying = $state(false);
	let error = $state('');
	let store = $state('');
	let rows: Row[] = $state([]);
	let rawText = $state('');
	let showRaw = $state(false);
	let lastImport: ReceiptApplyResult | null = $state(null);

	const pending = $derived(rows.filter((r) => r.action === 'add' && r.productId).length);

	function toRow(l: ReceiptLine): Row {
		return {
			raw: l.raw,
			quantity: l.quantity,
			unit: l.unit,
			amount: l.amount,
			arithmetic_ok: l.arithmetic_ok,
			productId: l.suggestion?.product_id ?? null,
			productName: l.suggestion?.product_name ?? '',
			source: l.suggestion?.source ?? '',
			confident: l.suggestion?.confident ?? false,
			// Lo ya marcado como "no es comida" llega decidido; lo que no tiene
			// producto no se puede añadir, así que arranca saltado.
			action: l.ignored ? 'ignore' : l.suggestion ? 'add' : 'skip',
			query: '',
			results: [],
			searching: false
		};
	}

	async function onPick(e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;

		busy = true;
		error = '';
		rows = [];
		lastImport = null;
		try {
			const form = new FormData();
			form.append('file', file);
			if (store.trim()) form.append('store', store.trim());
			const scan = await api.upload<ReceiptScan>('/receipts/scan', form);
			rawText = scan.text;
			rows = scan.lines.map(toRow);
			if (rows.length === 0) error = 'No he sabido leer ninguna línea de ese ticket.';
		} catch (err: unknown) {
			error = err instanceof Error ? err.message : 'No se ha podido leer el ticket';
		} finally {
			busy = false;
			input.value = ''; // sin esto, elegir la misma foto dos veces no dispara el change
		}
	}

	async function search(row: Row) {
		if (row.query.trim().length < 2) return;
		row.searching = true;
		try {
			row.results = await api.get<Product[]>(
				`/products?q=${encodeURIComponent(row.query.trim())}&limit=8`
			);
		} catch {
			row.results = [];
		} finally {
			row.searching = false;
		}
	}

	function choose(row: Row, p: Product) {
		row.productId = p.id;
		row.productName = p.name;
		row.source = 'manual';
		row.confident = true;
		row.action = 'add';
		row.results = [];
		row.query = '';
	}

	async function applyAll() {
		applying = true;
		error = '';
		try {
			lastImport = await api.post<ReceiptApplyResult>('/receipts/apply', {
				store: store.trim(),
				lines: rows.map((r) => ({
					raw: r.raw,
					action: r.action,
					product_id: r.action === 'add' ? r.productId : null,
					quantity: r.quantity,
					unit: r.unit,
					location: 'pantry'
				}))
			});
			rows = [];
			onApplied?.();
		} catch (err: unknown) {
			error = err instanceof Error ? err.message : 'No se ha podido guardar';
		} finally {
			applying = false;
		}
	}

	async function undo() {
		if (!lastImport) return;
		try {
			await api.del(`/receipts/imports/${lastImport.import_id}`);
			lastImport = null;
			onApplied?.();
		} catch (err: unknown) {
			error = err instanceof Error ? err.message : 'No se ha podido deshacer';
		}
	}

	const box =
		'background:rgba(255,255,255,0.04); border:1px dashed rgba(255,255,255,0.18); border-radius:16px; padding:0.875rem; margin-bottom:0.75rem;';
	const input =
		'background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12); border-radius:8px; color:#fff; font-family:inherit; padding:0.25rem 0.4rem; font-size:0.75rem;';
</script>

<div style={box}>
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

	<div style="display:flex; gap:0.375rem; margin-bottom:0.5rem;">
		<input
			bind:value={store}
			placeholder="Súper (mercadona, lidl…)"
			style="{input} flex:1;"
		/>
		<button
			onclick={() => fileInput?.click()}
			disabled={busy}
			style="padding:0.375rem 0.75rem; border-radius:10px; border:1px solid rgba(255,255,255,0.14); background:rgba(255,255,255,0.08); color:#fff; font-family:inherit; font-size:0.75rem; cursor:pointer; white-space:nowrap;"
		>
			{busy ? 'Leyendo…' : '📷 Foto'}
		</button>
	</div>
	<div style="font-size:0.625rem; color:rgba(255,255,255,0.4); margin-bottom:0.5rem;">
		El súper se recuerda con cada corrección, así que la próxima compra ahí sale sola.
	</div>

	{#if error}
		<div style="margin-top:0.5rem; font-size:0.75rem; color:oklch(70% 0.17 25);">{error}</div>
	{/if}

	{#if lastImport}
		<div
			style="display:flex; align-items:center; justify-content:space-between; gap:0.5rem; background:oklch(70% 0.16 160 / 0.1); border:1px solid oklch(70% 0.16 160 / 0.25); border-radius:12px; padding:0.5rem 0.625rem;"
		>
			<span style="font-size:0.75rem; color:oklch(85% 0.12 160);">
				{lastImport.applied}
				{lastImport.applied === 1 ? 'producto añadido' : 'productos añadidos'}
			</span>
			<button
				onclick={undo}
				style="padding:0.25rem 0.625rem; border-radius:99px; border:1px solid rgba(255,255,255,0.2); background:transparent; color:#fff; font-family:inherit; font-size:0.6875rem; cursor:pointer;"
				>Deshacer</button
			>
		</div>
	{/if}

	{#if rows.length}
		<div
			style="font-size:0.6875rem; color:rgba(255,255,255,0.5); margin:0.5rem 0 0.375rem;"
		>
			{rows.length} líneas leídas · revisa antes de guardar
		</div>

		{#each rows as row (row.raw + row.quantity)}
			<div
				style="border-top:1px solid rgba(255,255,255,0.07); padding:0.5rem 0; opacity:{row.action ===
				'add'
					? 1
					: 0.5};"
			>
				<div style="display:flex; align-items:baseline; gap:0.375rem; flex-wrap:wrap;">
					<span style="font-size:0.75rem; color:rgba(255,255,255,0.55); font-family:monospace;"
						>{row.raw}</span
					>
					{#if row.amount !== null}
						<span style="font-size:0.6875rem; color:rgba(255,255,255,0.35);"
							>{row.amount.toFixed(2)} €</span
						>
					{/if}
					{#if row.arithmetic_ok === false}
						<span
							title="Cantidad × precio no da el importe: el OCR ha leído mal algún número"
							style="font-size:0.625rem; padding:0.05rem 0.35rem; border-radius:99px; background:oklch(65% 0.2 60 / 0.18); color:oklch(80% 0.16 60);"
							>revisa el número</span
						>
					{/if}
				</div>

				<div
					style="display:flex; align-items:center; gap:0.375rem; margin-top:0.3rem; flex-wrap:wrap;"
				>
					<input
						type="number"
						bind:value={row.quantity}
						min="0"
						step="any"
						style="{input} width:72px;"
					/>
					<select bind:value={row.unit} style={input}>
						<option value="unit">ud</option>
						<option value="g">g</option>
						<option value="ml">ml</option>
					</select>

					{#if row.productId}
						<span style="font-size:0.75rem; color:#fff; flex:1; min-width:110px;"
							>{row.productName}</span
						>
						{#if !row.confident}
							<span
								title="Es un parecido que hemos calculado, no una decisión tuya anterior"
								style="font-size:0.625rem; color:rgba(255,255,255,0.4);">¿es este?</span
							>
						{/if}
					{:else}
						<span style="font-size:0.75rem; color:rgba(255,255,255,0.35); flex:1;"
							>sin producto</span
						>
					{/if}
				</div>

				<div style="display:flex; gap:0.3rem; margin-top:0.3rem; flex-wrap:wrap;">
					{#each [['add', 'Añadir'], ['ignore', 'No es comida'], ['skip', 'Saltar']] as [value, label]}
						<button
							onclick={() => (row.action = value as Action)}
							disabled={value === 'add' && !row.productId}
							style="padding:0.15rem 0.5rem; border-radius:99px; font-family:inherit; font-size:0.625rem; cursor:pointer; border:1px solid {row.action ===
							value
								? 'oklch(75% 0.18 165)'
								: 'rgba(255,255,255,0.12)'}; background:{row.action === value
								? 'oklch(75% 0.18 165 / 0.15)'
								: 'transparent'}; color:{row.action === value ? 'oklch(85% 0.14 165)' : 'rgba(255,255,255,0.5)'};"
							>{label}</button
						>
					{/each}
				</div>

				<div style="display:flex; gap:0.3rem; margin-top:0.3rem;">
					<input
						bind:value={row.query}
						onkeydown={(e) => e.key === 'Enter' && search(row)}
						placeholder={row.productId ? 'Cambiar producto…' : 'Buscar producto…'}
						style="{input} flex:1;"
					/>
					<button
						onclick={() => search(row)}
						style="padding:0.25rem 0.5rem; border-radius:8px; border:1px solid rgba(255,255,255,0.12); background:transparent; color:rgba(255,255,255,0.7); font-family:inherit; font-size:0.6875rem; cursor:pointer;"
						>{row.searching ? '…' : 'Buscar'}</button
					>
				</div>
				{#each row.results as p}
					<button
						onclick={() => choose(row, p)}
						style="display:block; width:100%; text-align:left; margin-top:0.2rem; padding:0.25rem 0.4rem; border-radius:8px; border:1px solid rgba(255,255,255,0.08); background:rgba(255,255,255,0.03); color:#fff; font-family:inherit; font-size:0.6875rem; cursor:pointer;"
						>{p.name}{#if p.brand}<span style="color:rgba(255,255,255,0.4);"> · {p.brand}</span
							>{/if}</button
					>
				{/each}
			</div>
		{/each}

		<button
			onclick={applyAll}
			disabled={applying}
			style="width:100%; margin-top:0.625rem; padding:0.5rem; border-radius:12px; border:none; cursor:pointer; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-weight:700; font-size:0.75rem; font-family:inherit;"
		>
			{applying ? 'Guardando…' : `Añadir ${pending} a la despensa`}
		</button>
	{/if}

	{#if rawText}
		<button
			onclick={() => (showRaw = !showRaw)}
			style="margin-top:0.5rem; padding:0; border:none; background:transparent; color:rgba(255,255,255,0.35); font-family:inherit; font-size:0.625rem; cursor:pointer;"
			>{showRaw ? 'Ocultar' : 'Ver'} texto en crudo</button
		>
		{#if showRaw}
			<pre
				style="margin-top:0.375rem; max-height:200px; overflow:auto; font-size:0.625rem; line-height:1.45; color:rgba(255,255,255,0.6); background:rgba(0,0,0,0.25); border-radius:10px; padding:0.5rem; white-space:pre-wrap; word-break:break-word;">{rawText}</pre>
		{/if}
	{/if}
</div>
