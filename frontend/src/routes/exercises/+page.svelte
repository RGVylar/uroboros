<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { Exercise, ExerciseSession, ExerciseSessionEntry } from '$lib/types';

	if (!auth.isLoggedIn) goto('/login');

	// ── Estado ─────────────────────────────────────────────────────────────
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

	// ── Sesión del día ──────────────────────────────────────────────────────
	const today = new Date().toISOString().slice(0, 10);
	let session: ExerciseSession | null = $state(null);
	let sessionLoading = $state(false);
	let selectedExerciseId: number | null = $state(null);
	let quantity = $state(0);
	let addError = $state('');

	// ── Derived ─────────────────────────────────────────────────────────────
	let myExercises = $derived(exercises.filter(e => !e.is_predefined));
	let predefinedExercises = $derived(exercises.filter(e => e.is_predefined));

	// ── Secciones desplegables ───────────────────────────────────────────────
	let showMyExercises = $state(true);
	let showPredefined = $state(false);

	// ── Carga ────────────────────────────────────────────────────────────────
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
	$effect(() => { loadExercises(); loadSession(); });

	// ── CRUD mis ejercicios ──────────────────────────────────────────────────
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
				unit: newUnit || 'repeticiones',
			});
			exercises = [...exercises, ex];
			showNewForm = false;
			newName = ''; newKcal = 0; newUnit = 'repeticiones';
		} catch (e: unknown) {
			createError = e instanceof Error ? e.message : 'Error';
		}
	}

	function startEdit(ex: Exercise) {
		editingId = ex.id; editName = ex.name; editKcal = ex.kcal_per_unit; editUnit = ex.unit;
	}

	async function saveEdit() {
		if (!editingId) return;
		try {
			const updated = await api.patch<Exercise>(`/exercises/${editingId}`, {
				name: editName.trim(), kcal_per_unit: editKcal, unit: editUnit.trim(),
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

	// Copiar un ejercicio predefinido a 'Mis ejercicios' para poder editarlo
	async function personalizeExercise(ex: Exercise) {
		try {
			const created = await api.post<Exercise>('/exercises', {
				name: ex.name,
				kcal_per_unit: ex.kcal_per_unit,
				unit: ex.unit,
			});
			exercises = [...exercises, created];
			// Abrir editor para la copia creada
			startEdit(created);
		} catch (e: unknown) {
			createError = e instanceof Error ? e.message : 'Error';
		}
	}

	// ── Sesión ───────────────────────────────────────────────────────────────
	async function addToSession() {
		if (!selectedExerciseId || quantity <= 0) {
			addError = 'Selecciona un ejercicio e indica la cantidad';
			return;
		}
		addError = ''; sessionLoading = true;
		try {
			session = await api.post<ExerciseSession>('/exercise-sessions/day/entry', {
				date: today, exercise_id: selectedExerciseId, quantity,
			});
			selectedExerciseId = null; quantity = 0;
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

	// Editar / sumar a una entrada existente
	let editingEntryId: number | null = $state(null);
	let editAddAmount = $state(0);
	let entryEditError = $state('');

	function startAddToEntry(entry: ExerciseSessionEntry) {
		editingEntryId = entry.id;
		editAddAmount = 0;
		entryEditError = '';
	}

	function cancelEditEntry() {
		editingEntryId = null;
		editAddAmount = 0;
		entryEditError = '';
	}

	async function saveAddToEntry(entryId: number) {
		if (editAddAmount <= 0) {
			entryEditError = 'Indica una cantidad positiva';
			return;
		}
		entryEditError = '';
		sessionLoading = true;
		try {
			const current = session?.entries.find(e => e.id === entryId);
			const newQuantity = (current?.quantity ?? 0) + editAddAmount;
			session = await api.patch<ExerciseSession>(`/exercise-sessions/day/entry/${entryId}`, {
				quantity: newQuantity,
			});
			editingEntryId = null;
			editAddAmount = 0;
		} catch (e: unknown) {
			entryEditError = e instanceof Error ? e.message : 'Error';
		} finally {
			sessionLoading = false;
		}
	}

	function getExercise(id: number) {
		return exercises.find(e => e.id === id);
	}

	const UNIT_SUGGESTIONS = ['repeticiones', 'minutos', 'segundos', 'km', 'series', 'pasos'];
</script>

<!-- Header -->
<div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:1rem;">
	<div style="flex:1;">
		<div style="font-size:0.625rem; letter-spacing:0.15em; color:rgba(255,255,255,0.45); text-transform:uppercase; font-weight:600;">Actividad</div>
		<div style="font-size:1.25rem; font-weight:800; color:#fff; letter-spacing:-0.02em;">Ejercicios</div>
	</div>
</div>

<!-- ═══════════════════════ MIS EJERCICIOS ════════════════════════════════ -->
<button
	onclick={() => showMyExercises = !showMyExercises}
	style="display:flex; align-items:center; justify-content:space-between; width:100%; background:none; border:none; padding:0; margin-bottom:0.5rem; cursor:pointer;">
	<h2 style="margin:0; font-size:0.9rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em;">
		Mis ejercicios
		{#if myExercises.length > 0}
			<span style="font-weight:400;">({myExercises.length})</span>
		{/if}
	</h2>
	<span style="color:var(--text-muted); font-size:0.85rem; transition:transform 0.2s; display:inline-block; transform:{showMyExercises ? 'rotate(180deg)' : 'rotate(0deg)'};">▼</span>
</button>

{#if showMyExercises}
	{#if !showNewForm}
		<button onclick={() => { showNewForm = true; createError = ''; }}
			style="font-size:0.8rem; padding:0.3rem 0.75rem; color:black; margin-bottom:0.5rem;">+ Nuevo ejercicio</button>
	{/if}

	{#if showNewForm}
		<div class="glass-card" style="margin-bottom:1rem;">
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

	{#if myExercises.length === 0 && !showNewForm}
		<div style="text-align:center; padding:1.5rem 0; color:rgba(255,255,255,0.4);">
			<div style="font-size:2rem; margin-bottom:0.375rem;">💪</div>
			<div style="font-size:0.8125rem; font-weight:600;">Sin ejercicios propios</div>
			<div style="font-size:0.6875rem; margin-top:0.25rem;">Crea uno o usa los predefinidos</div>
		</div>
	{/if}

	{#each myExercises as ex (ex.id)}
		{#if editingId === ex.id}
			<div class="glass-card" style="margin-bottom:0.5rem; border-color:var(--primary);">
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
			<div class="glass-card" style="margin-bottom:0.5rem; display:flex; align-items:center; justify-content:space-between;">
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

<!-- ═══════════════════════ PREDEFINIDOS ════════════════════════════════════ -->
<button
	onclick={() => showPredefined = !showPredefined}
	style="display:flex; align-items:center; justify-content:space-between; width:100%; background:none; border:none; padding:0; margin:1.25rem 0 0.5rem; cursor:pointer;">
	<h2 style="margin:0; font-size:0.9rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em;">
		Ejercicios predefinidos
		<span style="font-weight:400;">({predefinedExercises.length})</span>
	</h2>
	<span style="color:var(--text-muted); font-size:0.85rem; transition:transform 0.2s; display:inline-block; transform:{showPredefined ? 'rotate(180deg)' : 'rotate(0deg)'};">▼</span>
</button>

{#if showPredefined}
	{#each predefinedExercises as ex (ex.id)}
		<div class="glass-card" style="margin-bottom:0.4rem; display:flex; align-items:center; justify-content:space-between; opacity:0.85;">
			<div>
				<div style="font-weight:600; font-size:0.9rem; color:var(--text);">{ex.name}</div>
				<div style="font-size:0.72rem; color:var(--text-muted);">{ex.kcal_per_unit} kcal / {ex.unit}</div>
			</div>
			<div style="display:flex; gap:0.5rem; align-items:center;">
				<span style="font-size:0.65rem; color:var(--text-muted); border:1px solid var(--border); border-radius:4px; padding:0.15rem 0.4rem;">Global</span>
				<button class="btn-secondary" style="font-size:0.75rem; padding:0.3rem 0.6rem;" onclick={() => personalizeExercise(ex)}>Personalizar</button>
			</div>
		</div>
	{/each}
{/if}

<!-- ═══════════════════════ SESIÓN DEL DÍA ══════════════════════════════════ -->
<div style="margin-top:1.5rem; margin-bottom:0.5rem; display:flex; align-items:center; justify-content:space-between;">
	<h2 style="margin:0; font-size:1rem; color:var(--text);">Hoy</h2>
	{#if session}
		<span style="font-size:0.85rem; color:var(--primary); font-weight:700;">
			🔥 {Math.round(session.total_calories)} kcal quemadas
		</span>
	{/if}
</div>

{#if exercises.length > 0}
	<div class="glass-card" style="margin-bottom:0.75rem;">
		<div style="display:flex; gap:0.5rem; align-items:flex-end; flex-wrap:wrap;">
			<div class="form-group" style="margin-bottom:0; flex:2; min-width:120px;">
				<label for="sel-exercise" style="font-size:0.8rem;">Ejercicio</label>
				<select id="sel-exercise" bind:value={selectedExerciseId}
					style="width:100%; padding:0.5rem; border-radius:8px; border:1px solid var(--border); background:var(--surface); color:var(--text);">
					<option value={null}>Seleccionar...</option>
					{#if myExercises.length > 0}
						<optgroup label="Mis ejercicios">
							{#each myExercises as ex}
								<option value={ex.id}>{ex.name} ({ex.kcal_per_unit} kcal/{ex.unit})</option>
							{/each}
						</optgroup>
					{/if}
					<optgroup label="Predefinidos">
						{#each predefinedExercises as ex}
							<option value={ex.id}>{ex.name} ({ex.kcal_per_unit} kcal/{ex.unit})</option>
						{/each}
					</optgroup>
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

{#if session && session.entries.length > 0}
	{#each session.entries as entry (entry.id)}
		{@const ex = entry.exercise ?? getExercise(entry.exercise_id)}
		<div class="glass-card" style="margin-bottom:0.4rem; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap;">
			<div>
				<div style="font-weight:600; font-size:0.9rem; color:var(--text);">{ex?.name ?? '—'}</div>
				<div style="font-size:0.75rem; color:var(--text-muted);">
					{entry.quantity} {ex?.unit ?? ''} · {Math.round(entry.calories)} kcal
				</div>
			</div>
			{#if editingEntryId === entry.id}
				<div style="display:flex; gap:0.5rem; align-items:center;">
					<input type="number" bind:value={editAddAmount} min="1" step="1" style="width:6rem; padding:0.3rem;" />
					<button class="btn-secondary" style="padding:0.3rem 0.6rem;" onclick={() => saveAddToEntry(entry.id)}>+ Sumar</button>
					<button class="btn-secondary" style="padding:0.3rem 0.6rem;" onclick={cancelEditEntry}>Cancelar</button>
				</div>
				{#if entryEditError}<p class="error">{entryEditError}</p>{/if}
			{:else}
				<div style="display:flex; gap:0.4rem;">
					<button class="btn-secondary" style="font-size:0.75rem; padding:0.3rem 0.6rem;" onclick={() => startAddToEntry(entry)}>+ Añadir</button>
					<button class="btn-danger" style="padding:0.3rem 0.65rem; font-size:0.8rem;" onclick={() => deleteEntry(entry.id)}>✕</button>
				</div>
			{/if}
		</div>
	{/each}
{:else}
	<p style="text-align:center; color:var(--text-muted); font-size:0.85rem; padding:0.75rem 0;">
		Sin ejercicio registrado hoy.
	</p>
{/if}

<!-- Bottom spacing for mobile nav -->
<div style="height:6rem;"></div>
