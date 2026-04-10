<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { Product } from '$lib/types';

	if (!auth.isLoggedIn) goto('/login');

	const productId = page.params.id;

	let product: Product | null = $state(null);
	let name = $state('');
	let brand = $state('');
	let cal = $state(0);
	let prot = $state(0);
	let carbs = $state(0);
	let fat = $state(0);
	let saving = $state(false);
	let error = $state('');
	let saved = $state(false);

	$effect(() => {
		api.get<Product>(`/products/${productId}`).then(p => {
			product = p;
			name = p.name;
			brand = p.brand ?? '';
			cal = p.calories_per_100g;
			prot = p.protein_per_100g;
			carbs = p.carbs_per_100g;
			fat = p.fat_per_100g;
		}).catch(() => error = 'Producto no encontrado');
	});

	async function save() {
		saving = true;
		error = '';
		try {
			await api.patch(`/products/${productId}`, {
				name,
				brand: brand || null,
				calories_per_100g: cal,
				protein_per_100g: prot,
				carbs_per_100g: carbs,
				fat_per_100g: fat
			});
			saved = true;
			setTimeout(() => goto('/add'), 1000);
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Error';
		} finally {
			saving = false;
		}
	}
</script>

<h1>Editar producto</h1>

{#if !product && !error}
	<p style="color:var(--text-muted);">Cargando...</p>
{:else if error && !product}
	<p class="error">{error}</p>
{:else}
	<div class="card" style="margin-bottom:1rem;">
		<div style="font-size:0.8rem; color:var(--text-muted);">
			Fuente: {product?.source} · Barcode: {product?.barcode ?? 'ninguno'}
		</div>
	</div>

	<div class="form-group"><label for="e-name">Nombre</label><input id="e-name" bind:value={name} /></div>
	<div class="form-group"><label for="e-brand">Marca</label><input id="e-brand" bind:value={brand} /></div>
	<div class="form-group"><label for="e-cal">Kcal / 100g</label><input id="e-cal" type="number" bind:value={cal} min="0" step="0.1" /></div>
	<div class="form-group"><label for="e-prot">Proteína / 100g</label><input id="e-prot" type="number" bind:value={prot} min="0" step="0.1" /></div>
	<div class="form-group"><label for="e-carb">Carbos / 100g</label><input id="e-carb" type="number" bind:value={carbs} min="0" step="0.1" /></div>
	<div class="form-group"><label for="e-fat">Grasa / 100g</label><input id="e-fat" type="number" bind:value={fat} min="0" step="0.1" /></div>

	{#if error}<p class="error">{error}</p>{/if}

	<div style="display:flex; gap:0.5rem;">
		<button class="btn-secondary" onclick={() => history.back()} style="flex:1;">Cancelar</button>
		<button onclick={save} disabled={saving} style="flex:2;">
			{saved ? 'Guardado!' : saving ? 'Guardando...' : 'Guardar cambios'}
		</button>
	</div>
{/if}
