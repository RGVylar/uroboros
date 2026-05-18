<script lang="ts">
	import { api } from '$lib/api';
	import type { InventoryItem, InventoryUnit } from '$lib/types';
	import UnitSelector from './UnitSelector.svelte';

	interface Props {
		item: InventoryItem;
		// Optional pre-fill quantity (e.g. from diary entry)
		initialQuantity?: number;
		initialUnit?: InventoryUnit;
		onclose: () => void;
		onconsumed?: (updated: InventoryItem) => void;
	}

	let {
		item,
		initialQuantity,
		initialUnit,
		onclose,
		onconsumed
	}: Props = $props();

	let quantity = $state(initialQuantity ?? Math.min(1, item.quantity_base));
	let unit = $state<InventoryUnit>(initialUnit ?? item.unit);
	let notes = $state('');
	let saving = $state(false);
	let error = $state('');

	async function confirm() {
		if (quantity <= 0) {
			error = 'La cantidad debe ser mayor que 0';
			return;
		}
		saving = true;
		error = '';
		try {
			const updated = await api.post<InventoryItem>(`/inventory/${item.id}/consume`, {
				quantity,
				unit,
				notes: notes.trim() || null,
			});
			onconsumed?.(updated);
			onclose();
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'No se pudo consumir del inventario';
		} finally {
			saving = false;
		}
	}

	// Helpful display of remaining stock after this consume
	let remaining = $derived(
		Math.max(0, item.quantity_base - (unit === item.unit ? quantity : 0))
	);
</script>

<div class="backdrop" onclick={onclose} role="presentation"></div>
<div class="modal" role="dialog" aria-modal="true" aria-label="Consumir del inventario">
	<div class="modal-icon">📦</div>
	<h2 class="modal-title">Consumir del inventario</h2>
	<p class="modal-sub">{item.product_name}</p>

	<div class="stock-info">
		<div class="stock-label">Stock actual</div>
		<div class="stock-value">
			{item.quantity_base.toLocaleString()} <span class="stock-unit">{item.unit}</span>
		</div>
	</div>

	<div class="field-group">
		<label for="cf-qty" class="field-label">Cantidad a restar</label>
		<input
			id="cf-qty"
			type="number"
			bind:value={quantity}
			min="0.1"
			step="any"
			class="qty-input"
		/>
	</div>

	<div class="field-group">
		<UnitSelector bind:unit label="Unidad" size="sm" />
	</div>

	<div class="field-group">
		<label for="cf-notes" class="field-label">Notas (opcional)</label>
		<input
			id="cf-notes"
			type="text"
			bind:value={notes}
			placeholder="Ej. desayuno, sobras..."
			class="notes-input"
		/>
	</div>

	{#if unit === item.unit}
		<div class="preview">
			Quedará: <strong>{remaining.toLocaleString()} {item.unit}</strong>
		</div>
	{/if}

	{#if error}
		<p class="error-msg">{error}</p>
	{/if}

	<div class="actions">
		<button type="button" class="btn-cancel" onclick={onclose} disabled={saving}>
			Cancelar
		</button>
		<button type="button" class="btn-confirm" onclick={confirm} disabled={saving}>
			{saving ? 'Restando…' : '✓ Restar del stock'}
		</button>
	</div>
</div>

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.6);
		backdrop-filter: blur(4px);
		z-index: 100;
		animation: fade-in 0.2s ease;
	}
	@keyframes fade-in {
		from { opacity: 0; }
		to   { opacity: 1; }
	}

	.modal {
		position: fixed;
		bottom: 0;
		left: 50%;
		transform: translateX(-50%);
		width: min(480px, 100vw);
		background: oklch(18% 0.03 260);
		border: 1px solid oklch(35% 0.06 260 / 0.5);
		border-bottom: none;
		border-radius: 20px 20px 0 0;
		padding: 1.5rem 1.5rem 2.5rem;
		z-index: 101;
		animation: slide-up 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		max-height: 92dvh;
		overflow-y: auto;
	}
	@keyframes slide-up {
		from { transform: translateX(-50%) translateY(100%); }
		to   { transform: translateX(-50%) translateY(0); }
	}

	.modal-icon {
		font-size: 2rem;
		text-align: center;
		margin-bottom: 0;
	}
	.modal-title {
		font-size: 1.125rem;
		font-weight: 800;
		color: #fff;
		margin: 0;
		text-align: center;
	}
	.modal-sub {
		font-size: 0.875rem;
		color: rgba(255, 255, 255, 0.65);
		margin: 0 0 0.75rem;
		text-align: center;
	}

	.stock-info {
		display: flex;
		align-items: center;
		justify-content: space-between;
		background: rgba(255, 255, 255, 0.04);
		border: 1px solid rgba(255, 255, 255, 0.08);
		border-radius: 0.75rem;
		padding: 0.625rem 0.875rem;
		margin-bottom: 0.5rem;
	}
	.stock-label {
		font-size: 0.6875rem;
		color: rgba(255, 255, 255, 0.5);
		text-transform: uppercase;
		letter-spacing: 0.06em;
		font-weight: 700;
	}
	.stock-value {
		font-size: 1.125rem;
		font-weight: 800;
		color: oklch(85% 0.17 160);
	}
	.stock-unit {
		font-size: 0.75rem;
		font-weight: 500;
		color: rgba(255, 255, 255, 0.55);
	}

	.field-group {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
	}
	.field-label {
		font-size: 0.6875rem;
		font-weight: 700;
		color: rgba(255, 255, 255, 0.5);
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}
	.qty-input,
	.notes-input {
		width: 100%;
		background: rgba(255, 255, 255, 0.06);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 0.75rem;
		color: #fff;
		font-family: inherit;
		font-size: 0.9375rem;
		padding: 0.625rem 0.875rem;
		outline: none;
		box-sizing: border-box;
	}
	.qty-input:focus,
	.notes-input:focus {
		border-color: oklch(75% 0.18 165 / 0.5);
	}

	.preview {
		font-size: 0.75rem;
		color: rgba(255, 255, 255, 0.55);
		padding: 0.25rem 0.25rem 0;
	}
	.preview strong {
		color: #fff;
	}

	.error-msg {
		color: oklch(75% 0.2 25);
		font-size: 0.75rem;
		margin: 0.25rem 0;
		text-align: center;
	}

	.actions {
		display: flex;
		gap: 0.5rem;
		margin-top: 0.75rem;
	}
	.btn-cancel,
	.btn-confirm {
		flex: 1;
		padding: 0.75rem;
		border-radius: 0.75rem;
		font-family: inherit;
		font-weight: 700;
		font-size: 0.875rem;
		cursor: pointer;
		transition: opacity 0.15s;
	}
	.btn-cancel {
		background: rgba(255, 255, 255, 0.06);
		border: 1px solid rgba(255, 255, 255, 0.1);
		color: rgba(255, 255, 255, 0.7);
	}
	.btn-confirm {
		flex: 2;
		background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		border: none;
		color: #041010;
	}
	.btn-cancel:disabled,
	.btn-confirm:disabled {
		opacity: 0.5;
		cursor: wait;
	}
</style>
