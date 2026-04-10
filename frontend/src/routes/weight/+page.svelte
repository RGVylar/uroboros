<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { WeightLog } from '$lib/types';

	if (!auth.isLoggedIn) goto('/login');

	let weights: WeightLog[] = $state([]);
	let newWeight = $state(0);
	let saving = $state(false);

	async function load() {
		weights = await api.get<WeightLog[]>('/weight');
	}

	$effect(() => { load(); });

	async function addWeight() {
		if (!newWeight) return;
		saving = true;
		await api.post('/weight', { weight: newWeight, logged_at: new Date().toISOString() });
		newWeight = 0;
		saving = false;
		load();
	}

	async function deleteWeight(id: number) {
		await api.del(`/weight/${id}`);
		load();
	}

	function fmt(iso: string) {
		return new Date(iso).toLocaleDateString('es', { day: 'numeric', month: 'short', year: '2-digit' });
	}
</script>

<h1>Registro de peso</h1>

<div class="card" style="margin-bottom:1rem;">
	<div style="display:flex; gap:0.5rem; align-items:end;">
		<div class="form-group" style="flex:1; margin:0;">
			<label for="w">Peso (kg)</label>
			<input id="w" type="number" bind:value={newWeight} step="0.1" min="0" />
		</div>
		<button onclick={addWeight} disabled={saving}>Añadir</button>
	</div>
</div>

{#if weights.length > 0}
	<div style="font-size:0.85rem; color:var(--text-muted); margin-bottom:0.5rem;">
		{#if weights.length >= 2}
			Cambio: {(weights[0].weight - weights[weights.length - 1].weight).toFixed(1)} kg
		{/if}
	</div>
{/if}

{#each weights as w (w.id)}
	<div class="card" style="margin-bottom:0.5rem; display:flex; justify-content:space-between; align-items:center;">
		<div>
			<span style="font-weight:700; font-size:1.1rem;">{w.weight} kg</span>
			<span style="color:var(--text-muted); font-size:0.8rem; margin-left:0.5rem;">{fmt(w.logged_at)}</span>
		</div>
		<button class="btn-danger" style="padding:0.3rem 0.5rem; font-size:0.75rem;" onclick={() => deleteWeight(w.id)}>X</button>
	</div>
{/each}
