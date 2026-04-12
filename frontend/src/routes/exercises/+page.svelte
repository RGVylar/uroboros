<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { Exercise, ExerciseSession } from '$lib/types';

	if (!auth.isLoggedIn) goto('/login');

	// ── Estado ejercicios predefinidos ──────────────────────────────────────
	let exercises: Exercise[] = $state([]);
	let showNewForm = $state(false);
	let newName = $state('');
	let newKcal = $state(0);
	let newUnit = $state('repeticiones');
	let createError = $state('');

	let editingId: number | null = $state(null);
	let editName = $state('');
	let editKcal = $state(0);
	let editUnit = $state('');

	// ── Estado sesión del día ───────────────────────────────────────────────
	const today = new Date().toISOString().slice(0, 10);
	let session: ExerciseSession | null = $state(null);
	let sessionLoading = $state(false);

	let selectedExerciseId: number | null = $state(null);
	let quantity = $state(0);
	let addError = $state('');

	// ── Carga de datos ──────────────────────────────────────────────────────
	async function loadExercises() {
		exercises = await api.get<Exercise[]>('/exercises');
	}

	async function loadSession() {
		try {
			session = await api.get<ExerciseSession | null>(`/exercise-sessions/day?day=${today}`);
		} catch {
			session = null;
		}
	}

	$effect(() => {
		loadExercises();
		loadSession();
	});

	// ── CRUD ejercicios predefinidos ────────────────────────────────────────
	async function createExercise() {
		if (!newName.trim() || newKcal <= 0) {
			createError = 'Rellena nombre y calorías por unidad';
			return;
		}
		createError = '';
		try {
			const ex = await api.post<Exercise>('/exercises', {
				name: newName.trim(),
				kcal_per_unit: newKcal,
				unit: newUnit.trim() || 'repeticiones',
			});
			exercises = [...exercises, ex];
			showNewForm = false;
			newName = '';
			newKcal = 0;
			newUnit = 'repeticiones';
		} catch (e: unknown) {
			createError = e instanceof Error ? e.message : 'Error';
		}
	}

	function startEdit(ex: Exercise) {
		editingId = ex.id;
		editName = ex.name;
		editKcal = ex.kcal_per_unit;
		editUnit = ex.unit;
	}

	async function saveEdit() {
		if (!editingId) return;
		try {
			const updated = await api.patch<Exercise>(`/exercises/${editingId}`, {
				name: editName.trim(),
				kcal_per_unit: editKcal,
				unit: editUnit.trim(),
			});
			exercises = exercises.map(e => (e.id === editingId ? updated : e));
			editingId = null;
		} catch (e: unknown) {
			createError = e instanceof Error ? e.message : 'Error';
		}
	}

	async function deleteExercise(id: number) {
		await api.del(`/exercises/${id}`);
		exercises = exercises.filter(e => e.id !== id);
	}

	// ── Registro en sesión del día ──────────────────────────────────────────
	async function addToSession() {
		if (!selectedExerciseId || quantity <= 0) {
			addError = 'Selecciona un ejercicio e indica la cantidad';
			return;
		}
		addError = '';
		sessionLoading = true;
		try {
			session = await api.post<ExerciseSession>('/exercise-sessions/day/entry', {
				date: today,
				exercise_id: selectedExerciseId,
				quantity,
			});
			selectedExerciseId = null;
			quantity = 0;
		} catch (e: unknown) {
			addError = e instanceof Error ? e.message : 'Error';
		} finally {
			sessionLoading = false;
		}
	}

	async function deleteEntry(entryId: number) {
		sessionLoading = true;
		try {
			const result = await api.del<ExerciseSession | null>(`/exercise-sessions/day/entry/${entryId}`);
			session = result ?? null;
		} catch {
			session = null;
		} finally {
			sessionLoading = false;
		}
	}

	// ── Helpers ─────────────────────────────────────────────────────────────
	function getExercise(id: number) {
		return exercises.find(e => e.id === id);
	}

	const UNIT_SUGGESTIONS = ['repeticiones', 'minutos', 'segundos', 'km', 'series', 'pasos'];
</script>

<h1>Ejercicios</h1>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!-- PANEL SUPERIOR: Ejercicios predefinidos                                -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

{#if !showNewForm}
	<button onclick={() => { showNewForm = true; createError = ''; }}
		style="width:100%; margin-bottom:1rem; color:black;">
		+ Nuevo ejercicio
	</button>
{:else}
	<div class="card" style="margin-bottom:1rem;">
		<h2 style="margin-top:0; font-size:1rem; color:var(--text);">Nuevo ejercicio</h2>

		<div class="form-group">
			<label for="ex-name">Nombre</label>
			<input id="ex-name" bind:value={newName} placeholder="Ej: Sentadillas" />
		</div>

		<div style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem;">
			<div class="form-group" style="margin-bottom:0;">
				<label for="ex-kcal">Kcal por unidad</label>
				<input id="ex-kcal" type="number" bind:value={newKcal} min="0.1" step="0.1" />
			</div>
			<div class="form-group" style="margin-bottom:0;">
				<label for="ex-unit">Unidad</label>
				<select id="ex-unit" bind:value={newUnit}
					style="width:100%; padding:0.5rem; border-radius:8px; border:1px solid var(--border); background:var(--surface); color:var(--text);">
					{#each UNIT_SUGGESTIONS as u}
						<option value={u}>{u}</option>
					{/each}
				</select>
			</div>
		</div>

		{#if newKcal > 0 && newName}
			<p style="font-size:0.8rem; color:var(--text-muted); margin:0.5rem 0 0;">
				Ejemplo: 10 {newUnit} = {(newKcal * 10).toFixed(0)} kcal
			</p>
		{/if}

		{#if createError}<p class="error">{createError}</p>{/if}

		<div style="display:flex; gap:0.5rem; margin-top:0.75rem;">
			<button class="btn-secondary" onclick={() => showNewForm = false} style="flex:1;">Cancelar</button>
			<button onclick={createExercise} style="flex:2; color:black;">Guardar</button>
		</div>
	</div>
{/if}

<!-- Lista de ejercicios predefinidos -->
{#if exercises.length === 0}
	<p style="text-align:center; color:var(--text-muted); padding:1rem 0;">
		No tienes ejercicios definidos aún. Crea uno para empezar.
	</p>
{:else}
	{#each exercises as ex (ex.id)}
		{#if editingId === ex.id}
			<!-- Modo edición inline -->
			<div class="card" style="margin-bottom:0.5rem; border-color:var(--primary);">
				<div style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem; margin-bottom:0.5rem;">
					<input bind:value={editName} placeholder="Nombre" />
					<input type="number" bind:value={editKcal} min="0.1" step="0.1" placeholder="Kcal/unidad" />
				</div>
				<select bind:value={editUnit} style="width:100%; padding:0.5rem; border-radius:8px; border:1px solid var(--border); background:var(--surface); color:var(--text); margin-bottom:0.5rem;">
					{#each UNIT_SUGGESTIONS as u}
						<option value={u}>{u}</option>
					{/each}
				</select>
				<div style="display:flex; gap:0.5rem;">
					<button class="btn-secondary" onclick={() => editingId = null} style="flex:1;">Cancelar</button>
					<button onclick={saveEdit} style="flex:2; color:black;">Guardar cambios</button>
				</div>
			</div>
		{:else}
			<div class="card" style="margin-bottom:0.5rem; display:flex; align-items:center; justify-content:space-between;">
				<div>
					<div style="font-weight:700; font-size:0.95rem; color:var(--text);">{ex.name}</div>
					<div style="font-size:0.75rem; color:var(--text-muted);">
						{ex.kcal_per_unit} kcal / {ex.unit}
					</div>
				</div>
				<div style="display:flex; gap:0.4rem;">
					<button class="btn-secondary" style="font-size:0.75rem; padding:0.3rem 0.6rem;"
						onclick={() => startEdit(ex)}>✏️</button>
					<button class="btn-danger" style="font-size:0.75rem; padding:0.3rem 0.6rem;"
						onclick={() => deleteExercise(ex.id)}>✕</button>
				</div>
			</div>
		{/if}
	{/each}
{/if}

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!-- PANEL INFERIOR: Sesión del día                                         -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

<div style="margin-top:1.5rem; margin-bottom:0.5rem; display:flex; align-items:center; justify-content:space-between;">
	<h2 style="margin:0; font-size:1rem; color:var(--text);">Hoy</h2>
	{#if session}
		<span style="font-size:0.85rem; color:var(--primary); font-weight:700;">
			🔥 {Math.round(session.total_calories)} kcal quemadas
		</span>
	{/if}
</div>

{#if exercises.length > 0}
	<!-- Formulario para añadir ejercicio al día -->
	<div class="card" style="margin-bottom:0.75rem;">
		<div style="display:flex; gap:0.5rem; align-items:flex-end; flex-wrap:wrap;">
			<div class="form-group" style="margin-bottom:0; flex:2; min-width:120px;">
				<label for="sel-exercise" style="font-size:0.8rem;">Ejercicio</label>
				<select id="sel-exercise" bind:value={selectedExerciseId}
					style="width:100%; padding:0.5rem; border-radius:8px; border:1px solid var(--border); background:var(--surface); color:var(--text);">
					<option value={null}>Seleccionar...</option>
					{#each exercises as ex}
						<option value={ex.id}>{ex.name} ({ex.kcal_per_unit} kcal/{ex.unit})</option>
					{/each}
				</select>
			</div>
			<div class="form-group" style="margin-bottom:0; flex:1; min-width:80px;">
				<label for="qty-input" style="font-size:0.8rem;">
					{selectedExerciseId ? (getExercise(selectedExerciseId)?.unit ?? 'Cantidad') : 'Cantidad'}
				</label>
				<input id="qty-input" type="number" bind:value={quantity} min="1" step="1" />
			</div>
			<button onclick={addToSession} disabled={sessionLoading}
				style="padding:0.5rem 0.75rem; color:black; flex-shrink:0;">
				{sessionLoading ? '...' : '+ Añadir'}
			</button>
		</div>

		{#if selectedExerciseId && quantity > 0}
			{@const ex = getExercise(selectedExerciseId)}
			{#if ex}
				<p style="font-size:0.78rem; color:var(--text-muted); margin:0.4rem 0 0;">
					= {(ex.kcal_per_unit * quantity).toFixed(0)} kcal quemadas
				</p>
			{/if}
		{/if}

		{#if addError}<p class="error">{addError}</p>{/if}
	</div>
{/if}

<!-- Lista de ejercicios de la sesión de hoy -->
{#if session && session.entries.length > 0}
	{#each session.entries as entry (entry.id)}
		{@const ex = entry.exercise ?? getExercise(entry.exercise_id)}
		<div class="card" style="margin-bottom:0.4rem; display:flex; align-items:center; justify-content:space-between;">
			<div>
				<div style="font-weight:600; font-size:0.9rem; color:var(--text);">
					{ex?.name ?? '—'}
				</div>
				<div style="font-size:0.75rem; color:var(--text-muted);">
					{entry.quantity} {ex?.unit ?? ''} · {Math.round(entry.calories)} kcal
				</div>
			</div>
			<button class="btn-danger" style="padding:0.3rem 0.65rem; font-size:0.8rem;"
				onclick={() => deleteEntry(entry.id)}>✕</button>
		</div>
	{/each}
{:else}
	<p style="text-align:center; color:var(--text-muted); font-size:0.85rem; padding:0.75rem 0;">
		Sin ejercicio registrado hoy.
	</p>
{/if}
