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

	// ── UI state ─────────────────────────────────────────────────────────────
	let activeTab = $state<'today'|'catalog'>('today');
	let showDetail: Exercise | null = $state(null);
	let detailQuantity = $state(30);
	let catalogQuery = $state('');

	// ── Derived ─────────────────────────────────────────────────────────────
	let myExercises = $derived(exercises.filter(e => !e.is_predefined));
	let predefinedExercises = $derived(exercises.filter(e => e.is_predefined));
	let allExercises = $derived(exercises);
	let filteredCatalog = $derived(
		catalogQuery
			? exercises.filter(e => e.name.toLowerCase().includes(catalogQuery.toLowerCase()))
			: exercises
	);
	let totalKcal = $derived(session ? Math.round(session.total_calories) : 0);
	let totalSessions = $derived(session?.entries.length ?? 0);

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

	// ── Sesión ───────────────────────────────────────────────────────────────
	async function addToSession(exerciseId: number, qty: number) {
		if (!exerciseId || qty <= 0) return;
		addError = ''; sessionLoading = true;
		try {
			session = await api.post<ExerciseSession>('/exercise-sessions/day/entry', {
				date: today, exercise_id: exerciseId, quantity: qty,
			});
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

	function getExercise(id: number) {
		return exercises.find(e => e.id === id);
	}

	function exerciseEmoji(name: string): string {
		const n = name.toLowerCase();
		if (/corr|run/.test(n)) return '🏃';
		if (/cicl|bici/.test(n)) return '🚴';
		if (/nata|swim/.test(n)) return '🏊';
		if (/pesa|gym|muscul|fuerza|weight/.test(n)) return '🏋️';
		if (/yoga|estira|flex/.test(n)) return '🧘';
		if (/camin|walk/.test(n)) return '🚶';
		if (/hiit|intens|interval/.test(n)) return '⚡';
		if (/escal/.test(n)) return '🧗';
		if (/baile|dance/.test(n)) return '💃';
		if (/futbol|basket|tenis|padel/.test(n)) return '⚽';
		if (/creat/.test(n)) return '💊';
		return '💪';
	}

	// Ring SVG helper: r=40, cx=cy=50, viewBox 0 0 100 100
	const RING_R = 40;
	const RING_CIRC = 2 * Math.PI * RING_R; // ~251.3
	function ringDash(pct: number) {
		const p = Math.min(100, Math.max(0, pct));
		return `${(p / 100) * RING_CIRC} ${RING_CIRC}`;
	}

	const UNIT_SUGGESTIONS = ['repeticiones', 'minutos', 'segundos', 'km', 'series', 'pasos'];

	// Open detail sheet
	function openDetail(ex: Exercise) {
		showDetail = ex;
		detailQuantity = ex.unit === 'minutos' || ex.unit === 'segundos' ? 30 : 10;
	}

	// Register from detail sheet
	async function registerFromDetail() {
		if (!showDetail) return;
		await addToSession(showDetail.id, detailQuantity);
		showDetail = null;
		activeTab = 'today';
	}
</script>

<!-- ── Header ── -->
<div style="display:flex; align-items:center; gap:0.75rem; padding:0.25rem 0 1rem;">
	<button onclick={() => goto('/')} style="width:36px; height:36px; border-radius:50%; background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.1); display:flex; align-items:center; justify-content:center; color:#fff; cursor:pointer; font-family:inherit; font-size:1rem; flex-shrink:0;">←</button>
	<div style="flex:1; min-width:0;">
		<h1 style="font-size:1.875rem; font-weight:400; letter-spacing:-0.05em; color:#fff; line-height:1; margin:0; font-family:'Lora','Georgia',serif;">Ejercicios</h1>
		<div style="font-size:0.6875rem; color:rgba(255,255,255,0.5); margin-top:0.25rem;">Energía gastada hoy</div>
	</div>
</div>

<!-- ── Hero: burn ring ── -->
<div class="glass-card" style="margin-bottom:0.875rem; background:linear-gradient(135deg, oklch(75% 0.18 30 / 0.18), rgba(255,255,255,0.04)); border-color:oklch(75% 0.18 30 / 0.25);">
	<div style="display:flex; align-items:center; gap:1rem;">
		<!-- Ring -->
		<div style="flex-shrink:0;">
			<svg width="100" height="100" viewBox="0 0 100 100">
				<!-- track -->
				<circle cx="50" cy="50" r={RING_R} fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="10"/>
				<!-- progress -->
				<circle cx="50" cy="50" r={RING_R} fill="none"
					stroke="oklch(78% 0.18 30)"
					stroke-width="10"
					stroke-linecap="round"
					stroke-dasharray={ringDash((totalKcal / 500) * 100)}
					stroke-dashoffset="0"
					transform="rotate(-90 50 50)"
					style="filter: drop-shadow(0 0 6px oklch(75% 0.2 30 / 0.6)); transition: stroke-dasharray 0.4s ease;"/>
				<!-- inner text -->
				<text x="50" y="46" text-anchor="middle" fill="#fff" font-size="20" font-family="'Lora','Georgia',serif" font-weight="400">{totalKcal}</text>
				<text x="50" y="58" text-anchor="middle" fill="rgba(255,255,255,0.5)" font-size="8" font-family="Geist,sans-serif" letter-spacing="1">KCAL</text>
			</svg>
		</div>
		<!-- Stats -->
		<div style="flex:1;">
			<div style="font-size:0.625rem; letter-spacing:0.15em; text-transform:uppercase; color:rgba(255,255,255,0.45); font-weight:700;">Quemadas hoy</div>
			<div style="font-size:2.25rem; font-weight:400; letter-spacing:-0.05em; color:#fff; line-height:1; margin-top:0.25rem; font-family:'Lora','Georgia',serif;">
				{totalKcal} <span style="font-size:0.875rem; color:rgba(255,255,255,0.5); font-weight:400;">kcal</span>
			</div>
			<div style="display:flex; gap:0.625rem; margin-top:0.625rem; font-size:0.6875rem;">
				<div><span style="color:rgba(255,255,255,0.5);">Sesiones:</span> <span style="color:#fff; font-weight:600;">{totalSessions}</span></div>
			</div>
		</div>
	</div>
</div>

<!-- ── Tab switcher ── -->
<div style="display:flex; gap:0.375rem; margin-bottom:1rem; padding:3px; border-radius:99px; background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.06);">
	{#each [{ id:'today', label:'Hoy' }, { id:'catalog', label:'Catálogo' }] as t}
		<button onclick={() => activeTab = t.id as 'today'|'catalog'} style="
			flex:1; padding:0.5625rem 0.75rem; border-radius:99px; border:none; cursor:pointer; font-family:inherit;
			background:{activeTab === t.id ? 'rgba(255,255,255,0.1)' : 'transparent'};
			color:{activeTab === t.id ? '#fff' : 'rgba(255,255,255,0.5)'};
			font-size:0.75rem; font-weight:700; transition:all 0.15s;
		">{t.label}</button>
	{/each}
</div>

<!-- ── TAB: HOY ── -->
{#if activeTab === 'today'}
	<div style="font-size:0.625rem; letter-spacing:0.1em; text-transform:uppercase; color:rgba(255,255,255,0.45); font-weight:700; margin:0 0.25rem 0.625rem;">Sesiones registradas</div>

	{#if session && session.entries.length > 0}
		<div class="glass-card" style="padding:0.375rem;">
			{#each session.entries as entry, i (entry.id)}
				{@const ex = entry.exercise ?? getExercise(entry.exercise_id)}
				<div style="
					display:flex; align-items:center; gap:0.75rem; padding:0.75rem 0.875rem;
					border-bottom:{i < session.entries.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none'};
				">
					<div style="width:40px; height:40px; border-radius:12px; background:oklch(75% 0.18 30 / 0.15); border:1px solid oklch(75% 0.18 30 / 0.2); display:flex; align-items:center; justify-content:center; font-size:1.125rem; flex-shrink:0;">{exerciseEmoji(ex?.name ?? '')}</div>
					<div style="flex:1; min-width:0;">
						<div style="font-size:0.8125rem; font-weight:600; color:#fff;">{ex?.name ?? '—'}</div>
						<div style="font-size:0.6875rem; color:rgba(255,255,255,0.4); margin-top:0.125rem;">{entry.quantity} {ex?.unit ?? ''}</div>
					</div>
					<div style="text-align:right; flex-shrink:0;">
						<div style="font-size:0.875rem; font-weight:700; color:oklch(82% 0.17 30);">-{Math.round(entry.calories)}</div>
						<div style="font-size:0.625rem; color:rgba(255,255,255,0.4);">kcal</div>
					</div>
					<button onclick={() => deleteEntry(entry.id)} disabled={sessionLoading} style="width:28px; height:28px; border-radius:8px; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.08); color:rgba(255,255,255,0.5); cursor:pointer; display:flex; align-items:center; justify-content:center; font-size:0.75rem; flex-shrink:0;">✕</button>
				</div>
			{/each}
		</div>
	{:else}
		<div style="text-align:center; padding:2rem 0; color:rgba(255,255,255,0.4);">
			<div style="font-size:2rem; margin-bottom:0.5rem;">🏃</div>
			<div style="font-size:0.8125rem; font-weight:600; color:rgba(255,255,255,0.5);">Sin actividad registrada hoy</div>
			<div style="font-size:0.6875rem; margin-top:0.25rem; color:rgba(255,255,255,0.3);">Ve al Catálogo para añadir</div>
		</div>
	{/if}

	<!-- Quick add from catalog button -->
	<button onclick={() => activeTab = 'catalog'} style="width:100%; margin-top:0.875rem; padding:0.875rem; border-radius:14px; background:rgba(255,255,255,0.04); border:1px dashed rgba(255,255,255,0.12); color:rgba(255,255,255,0.5); font-family:inherit; font-size:0.8125rem; cursor:pointer;">+ Añadir actividad</button>

<!-- ── TAB: CATÁLOGO ── -->
{:else}
	<!-- Search -->
	<div style="position:relative; margin-bottom:0.75rem;">
		<div style="position:absolute; left:0.875rem; top:50%; transform:translateY(-50%); color:rgba(255,255,255,0.4); pointer-events:none; font-size:0.875rem;">🔍</div>
		<input
			bind:value={catalogQuery}
			placeholder="Buscar ejercicio…"
			style="width:100%; padding:0.8125rem 1rem 0.8125rem 2.5rem; border-radius:16px; font-size:0.8125rem; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); color:#fff; outline:none; font-family:inherit; box-sizing:border-box;"
		/>
	</div>

	<!-- Add new exercise button -->
	<button onclick={() => { showNewForm = !showNewForm; createError = ''; }} style="width:100%; margin-bottom:0.75rem; padding:0.75rem; border-radius:14px; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); border:none; color:#041010; font-family:inherit; font-size:0.8125rem; font-weight:700; cursor:pointer; box-shadow:inset 0 1px 0 rgba(255,255,255,0.4);">
		{showNewForm ? '✕ Cancelar' : '+ Crear ejercicio propio'}
	</button>

	{#if showNewForm}
		<div class="glass-card" style="margin-bottom:0.875rem;">
			<div style="font-size:0.75rem; font-weight:700; color:#fff; margin-bottom:0.75rem;">Nuevo ejercicio</div>
			<div style="display:flex; flex-direction:column; gap:0.625rem;">
				<input bind:value={newName} placeholder="Nombre" style="width:100%; padding:0.625rem 0.75rem; border-radius:10px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); color:#fff; font-family:inherit; font-size:0.8125rem; outline:none; box-sizing:border-box;" />
				<div style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem;">
					<input type="number" bind:value={newKcal} min="0.1" step="0.1" placeholder="Kcal / unidad" style="width:100%; padding:0.625rem 0.75rem; border-radius:10px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); color:#fff; font-family:inherit; font-size:0.8125rem; outline:none; box-sizing:border-box;" />
					<select bind:value={newUnit} style="width:100%; padding:0.625rem 0.75rem; border-radius:10px; background:rgba(18,20,26,0.95); border:1px solid rgba(255,255,255,0.1); color:#fff; font-family:inherit; font-size:0.8125rem; outline:none; box-sizing:border-box;">
						{#each UNIT_SUGGESTIONS as u}<option value={u}>{u}</option>{/each}
					</select>
				</div>
				{#if createError}<div style="font-size:0.6875rem; color:oklch(75% 0.2 25);">{createError}</div>{/if}
				<button onclick={createExercise} style="padding:0.75rem; border-radius:12px; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); border:none; color:#041010; font-family:inherit; font-size:0.8125rem; font-weight:700; cursor:pointer;">Guardar</button>
			</div>
		</div>
	{/if}

	<!-- Catalog grid -->
	{#if filteredCatalog.length > 0}
		<div style="display:grid; grid-template-columns:1fr 1fr; gap:0.625rem;">
			{#each filteredCatalog as ex (ex.id)}
				<button onclick={() => openDetail(ex)} style="
					padding:0.875rem 0.75rem; border-radius:20px; text-align:left; cursor:pointer;
					background:rgba(255,255,255,0.05); backdrop-filter:blur(24px) saturate(160%);
					border:1px solid rgba(255,255,255,0.09); color:#fff; font-family:inherit;
					display:flex; flex-direction:column; gap:0.375rem;
					transition:background 0.15s;
				">
					<div style="font-size:1.75rem;">{exerciseEmoji(ex.name)}</div>
					<div style="font-size:0.8125rem; font-weight:600; color:#fff; line-height:1.2;">{ex.name}</div>
					<div style="font-size:0.625rem; color:rgba(255,255,255,0.45);">{ex.kcal_per_unit} kcal/{ex.unit}</div>
					{#if !ex.is_predefined}
						<div style="font-size:0.5625rem; color:oklch(80% 0.15 160); font-weight:600;">· Personalizado</div>
					{/if}
				</button>
			{/each}
		</div>
	{:else}
		<div style="text-align:center; padding:2rem 0; color:rgba(255,255,255,0.4);">
			<div style="font-size:0.8125rem;">Sin resultados para «{catalogQuery}»</div>
		</div>
	{/if}
{/if}

<!-- Bottom spacing -->
<div style="height:6rem;"></div>

<!-- ── Detail bottom sheet ── -->
{#if showDetail}
	<!-- Backdrop -->
	<div onclick={() => showDetail = null} style="position:fixed; inset:0; z-index:100; background:rgba(0,0,0,0.5); backdrop-filter:blur(8px); -webkit-backdrop-filter:blur(8px);"></div>

	<!-- Sheet -->
	<div style="position:fixed; bottom:0; left:0; right:0; z-index:101; padding:1.5rem 1.25rem max(2.25rem, calc(env(safe-area-inset-bottom, 0px) + 2.25rem)); background:rgba(18,20,26,0.95); backdrop-filter:blur(40px) saturate(180%); -webkit-backdrop-filter:blur(40px) saturate(180%); border-top-left-radius:28px; border-top-right-radius:28px; border:1px solid rgba(255,255,255,0.1); border-bottom:none;">
		<!-- Handle -->
		<div style="width:40px; height:4px; border-radius:99px; background:rgba(255,255,255,0.2); margin:0 auto 1.125rem;"></div>

		<!-- Exercise info -->
		<div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:1.125rem;">
			<div style="font-size:2.5rem;">{exerciseEmoji(showDetail.name)}</div>
			<div>
				<div style="font-size:1.625rem; font-weight:400; letter-spacing:-0.04em; color:#fff; font-family:'Lora','Georgia',serif;">{showDetail.name}</div>
				<div style="font-size:0.6875rem; color:rgba(255,255,255,0.5);">{showDetail.kcal_per_unit} kcal / {showDetail.unit}</div>
			</div>
		</div>

		<!-- Quantity -->
		<div style="font-size:0.6875rem; color:rgba(255,255,255,0.55); margin-bottom:0.5rem; font-weight:600; letter-spacing:0.05em;">CANTIDAD ({showDetail.unit})</div>
		<input
			type="range"
			min="1"
			max={showDetail.unit === 'minutos' ? 180 : showDetail.unit === 'segundos' ? 600 : 100}
			step={showDetail.unit === 'minutos' || showDetail.unit === 'segundos' ? 5 : 1}
			bind:value={detailQuantity}
			style="width:100%; accent-color:oklch(78% 0.18 30); margin-bottom:0.375rem;"
		/>
		<div style="display:flex; justify-content:space-between; font-size:0.625rem; color:rgba(255,255,255,0.4); margin-bottom:1.25rem;">
			<span>1</span>
			<span style="color:#fff; font-weight:700; font-size:0.875rem;">{detailQuantity} {showDetail.unit}</span>
			<span>{showDetail.unit === 'minutos' ? 180 : showDetail.unit === 'segundos' ? 600 : 100}</span>
		</div>

		<!-- Kcal preview -->
		<div style="display:flex; gap:0.625rem; margin-bottom:1.25rem;">
			<div style="flex:1; padding:0.875rem 1rem; border-radius:18px; background:oklch(75% 0.18 30 / 0.12); border:1px solid oklch(75% 0.18 30 / 0.25);">
				<div style="font-size:0.5625rem; letter-spacing:0.1em; color:rgba(255,255,255,0.5); text-transform:uppercase; font-weight:700;">Gasto estimado</div>
				<div style="display:flex; align-items:baseline; gap:0.25rem; margin-top:0.375rem;">
					<div style="font-size:2rem; font-weight:400; color:#fff; letter-spacing:-0.04em; font-family:'Lora','Georgia',serif;">{Math.round(showDetail.kcal_per_unit * detailQuantity)}</div>
					<div style="font-size:0.625rem; color:rgba(255,255,255,0.4);">kcal</div>
				</div>
			</div>
		</div>

		{#if addError}<div style="font-size:0.6875rem; color:oklch(75% 0.2 25); margin-bottom:0.75rem;">{addError}</div>{/if}

		<button onclick={registerFromDetail} disabled={sessionLoading} style="width:100%; padding:0.875rem; border-radius:16px; border:none; cursor:pointer; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-weight:800; font-size:0.9375rem; font-family:inherit; box-shadow:0 10px 30px -8px oklch(75% 0.22 165 / 0.55), inset 0 1px 0 rgba(255,255,255,0.4);">
			{sessionLoading ? 'Registrando...' : 'Registrar sesión'}
		</button>
	</div>
{/if}

<style>
	.glass-card {
		background: rgba(255,255,255,0.05);
		backdrop-filter: blur(24px) saturate(160%);
		-webkit-backdrop-filter: blur(24px) saturate(160%);
		border: 1px solid rgba(255,255,255,0.09);
		border-radius: 20px;
		padding: 1rem;
	}
</style>
