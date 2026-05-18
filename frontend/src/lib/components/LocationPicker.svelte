<script lang="ts">
	import type { InventoryLocation } from '$lib/types';

	interface Props {
		location: InventoryLocation;
		size?: 'sm' | 'md';
		label?: string;
	}

	let { location = $bindable('pantry'), size = 'md', label }: Props = $props();

	const OPTIONS: { value: InventoryLocation; label: string; emoji: string }[] = [
		{ value: 'pantry',   label: 'Despensa',    emoji: '🏠' },
		{ value: 'fridge',   label: 'Nevera',      emoji: '❄️' },
		{ value: 'freezer',  label: 'Congelador',  emoji: '🧊' },
	];
</script>

<div class="loc-picker" class:loc-picker-sm={size === 'sm'}>
	{#if label}
		<div class="loc-label">{label}</div>
	{/if}
	<div class="loc-chips">
		{#each OPTIONS as opt (opt.value)}
			<button
				type="button"
				class="loc-chip"
				class:loc-chip-active={location === opt.value}
				onclick={() => (location = opt.value)}
				aria-label="Ubicación: {opt.label}"
			>
				<span class="loc-emoji">{opt.emoji}</span>
				<span>{opt.label}</span>
			</button>
		{/each}
	</div>
</div>

<style>
	.loc-picker {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
	}
	.loc-label {
		font-size: 0.6875rem;
		font-weight: 700;
		color: rgba(255, 255, 255, 0.5);
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}
	.loc-chips {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 0.375rem;
	}
	.loc-chip {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.125rem;
		padding: 0.5rem 0.25rem;
		border-radius: 0.75rem;
		background: rgba(255, 255, 255, 0.04);
		border: 1px solid rgba(255, 255, 255, 0.08);
		color: rgba(255, 255, 255, 0.55);
		font-family: inherit;
		font-size: 0.6875rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.15s;
	}
	.loc-chip:hover {
		background: rgba(255, 255, 255, 0.07);
		color: rgba(255, 255, 255, 0.85);
	}
	.loc-chip-active {
		background: linear-gradient(135deg, oklch(72% 0.18 200 / 0.25), oklch(60% 0.2 220 / 0.15));
		border-color: oklch(75% 0.18 200 / 0.45);
		color: #fff;
	}
	.loc-emoji {
		font-size: 1rem;
		line-height: 1;
	}
	.loc-picker-sm .loc-chip {
		padding: 0.375rem 0.25rem;
		font-size: 0.625rem;
	}
	.loc-picker-sm .loc-emoji {
		font-size: 0.875rem;
	}
</style>
