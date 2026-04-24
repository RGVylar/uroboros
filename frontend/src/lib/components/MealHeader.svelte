<!--
  MealHeader.svelte
  Cabecera de una comida en el diario (Desayuno/Almuerzo/Cena/Snack) con kcal + acciones.
  Reemplaza el bloque inline "flex + flex + spans" que ahora se repite en cada <meal>.

  Uso:
    <MealHeader
      label={meal.label}
      kcal={meal.totals.calories}
      protein={meal.totals.protein}
      hasEntries={meal.entries.length > 0}
    >
      {#snippet actions()}
        <button class="btn-ghost" onclick={...}>Guardar receta</button>
      {/snippet}
    </MealHeader>
-->
<script lang="ts">
	interface Props {
		label: string;
		kcal: number;
		protein?: number;
		hasEntries?: boolean;
		actions?: import('svelte').Snippet;
	}
	let { label, kcal, protein, hasEntries = true, actions }: Props = $props();
</script>

<div class="meal-header" class:empty={!hasEntries}>
	<div class="left">
		<span class="label">{label}</span>
		{#if actions}<div class="actions">{@render actions()}</div>{/if}
	</div>
	<div class="totals">
		<span class="kcal"><strong>{Math.round(kcal)}</strong> kcal</span>
		{#if protein !== undefined}
			<span class="prot">P{Math.round(protein)}g</span>
		{/if}
	</div>
</div>

<style>
	.meal-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 0.5rem;
		padding: 0 0.25rem 0.5rem;
	}
	.meal-header.empty { opacity: 0.55; }
	.left {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		min-width: 0;
		flex: 1;
	}
	.label {
		font-weight: 800;
		font-size: 0.88rem;
		letter-spacing: -0.01em;
	}
	.actions { display: inline-flex; gap: 0.3rem; }
	.totals {
		display: inline-flex;
		align-items: baseline;
		gap: 0.5rem;
		font-variant-numeric: tabular-nums;
	}
	.kcal {
		font-size: 0.8rem;
		color: var(--cal);
	}
	.kcal strong {
		font-weight: 800;
	}
	.prot {
		font-size: 0.72rem;
		color: var(--prot);
		font-weight: 700;
	}
</style>
