<script lang="ts">
	import type { InventoryUnit } from '$lib/types';

	interface Props {
		unit: InventoryUnit;
		size?: 'sm' | 'md';
		label?: string;
		showHint?: boolean;
		productHint?: string; // e.g. "1 unit ≈ 100g" displayed when relevant
	}

	let {
		unit = $bindable('g'),
		size = 'md',
		label,
		showHint = false,
		productHint
	}: Props = $props();

	const OPTIONS: { value: InventoryUnit; label: string }[] = [
		{ value: 'g',    label: 'g'      },
		{ value: 'ml',   label: 'ml'     },
		{ value: 'unit', label: 'unidad' },
	];
</script>

<div class="unit-picker" class:unit-picker-sm={size === 'sm'}>
	{#if label}
		<div class="unit-label">{label}</div>
	{/if}
	<div class="unit-chips">
		{#each OPTIONS as opt (opt.value)}
			<button
				type="button"
				class="unit-chip"
				class:unit-chip-active={unit === opt.value}
				onclick={() => (unit = opt.value)}
				aria-label="Unidad: {opt.label}"
			>
				{opt.label}
			</button>
		{/each}
	</div>
	{#if showHint && unit === 'unit' && productHint}
		<div class="unit-hint">{productHint}</div>
	{/if}
</div>

<style>
	.unit-picker {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
	}
	.unit-label {
		font-size: 0.6875rem;
		font-weight: 700;
		color: rgba(255, 255, 255, 0.5);
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}
	.unit-chips {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 0.25rem;
		background: rgba(255, 255, 255, 0.04);
		border-radius: 0.625rem;
		padding: 0.1875rem;
	}
	.unit-chip {
		padding: 0.4375rem 0.5rem;
		border-radius: 0.5rem;
		background: transparent;
		border: none;
		color: rgba(255, 255, 255, 0.55);
		font-family: inherit;
		font-size: 0.75rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.15s;
	}
	.unit-chip:hover {
		color: rgba(255, 255, 255, 0.85);
	}
	.unit-chip-active {
		background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		color: #041010;
		font-weight: 700;
	}
	.unit-picker-sm .unit-chip {
		padding: 0.3125rem 0.375rem;
		font-size: 0.6875rem;
	}
	.unit-hint {
		font-size: 0.625rem;
		color: rgba(255, 255, 255, 0.4);
		font-style: italic;
		padding-left: 0.25rem;
	}
</style>
