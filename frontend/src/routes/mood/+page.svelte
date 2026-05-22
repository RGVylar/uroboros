<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { api } from '$lib/api';
	import Aurora from '$lib/components/uro/Aurora.svelte';
	import type { MoodEntry, MoodLevel } from '$lib/types';

	const day = $derived($page.url.searchParams.get('day') ?? new Date().toISOString().slice(0, 10));

	let energy: MoodLevel | null = $state(null);
	let digestion: MoodLevel | null = $state(null);
	let mood: MoodLevel | null = $state(null);
	let notes = $state('');
	let saving = $state(false);
	let loaded = $state(false);

	// Load existing entry for this day
	$effect(() => {
		api.get<MoodEntry | null>(`/mood/day?day=${day}`)
			.then(entry => {
				if (entry) {
					energy = entry.energy;
					digestion = entry.digestion;
					mood = entry.mood;
					notes = entry.notes ?? '';
				}
				loaded = true;
			})
			.catch(() => { loaded = true; });
	});

	async function save() {
		saving = true;
		try {
			await api.post('/mood/day', {
				entry_date: day,
				energy,
				digestion,
				mood,
				notes: notes.trim() || null,
			});
			history.back();
		} catch {
			saving = false;
		}
	}

	function goBack() {
		history.back();
	}

	const ENERGY = [
		{ level: 1 as MoodLevel, emoji: '🪫', label: 'Sin energía' },
		{ level: 2 as MoodLevel, emoji: '⚡', label: 'Normal' },
		{ level: 3 as MoodLevel, emoji: '🔥', label: 'Con energía' },
	];
	const DIGESTION = [
		{ level: 1 as MoodLevel, emoji: '🤢', label: 'Mal' },
		{ level: 2 as MoodLevel, emoji: '😐', label: 'Normal' },
		{ level: 3 as MoodLevel, emoji: '✅', label: 'Bien' },
	];
	const MOOD = [
		{ level: 1 as MoodLevel, emoji: '😞', label: 'Bajo' },
		{ level: 2 as MoodLevel, emoji: '🙂', label: 'Normal' },
		{ level: 3 as MoodLevel, emoji: '😄', label: 'Bien' },
	];

	const hasAny = $derived(energy !== null || digestion !== null || mood !== null);

	// Format date nicely
	const dateLabel = $derived(() => {
		const d = new Date(day + 'T12:00:00');
		return d.toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long' });
	});
</script>

<svelte:head>
	<title>Estado del día — uroboros</title>
</svelte:head>

<Aurora />

<div class="shell">
	<!-- Header -->
	<div class="header">
		<button class="back-btn" onclick={goBack}>← Atrás</button>
		<div class="header-text">
			<div class="label">Estado del día</div>
			<div class="date">{dateLabel()}</div>
		</div>
	</div>

	{#if !loaded}
		<div class="loading">Cargando...</div>
	{:else}
		<!-- Energy -->
		<section class="card">
			<div class="cat-label">Energía</div>
			<div class="options">
				{#each ENERGY as opt}
					<button
						class="opt-btn"
						class:selected={energy === opt.level}
						onclick={() => energy = energy === opt.level ? null : opt.level}
					>
						<span class="opt-emoji">{opt.emoji}</span>
						<span class="opt-label">{opt.label}</span>
					</button>
				{/each}
			</div>
		</section>

		<!-- Digestion -->
		<section class="card">
			<div class="cat-label">Digestión</div>
			<div class="options">
				{#each DIGESTION as opt}
					<button
						class="opt-btn"
						class:selected={digestion === opt.level}
						onclick={() => digestion = digestion === opt.level ? null : opt.level}
					>
						<span class="opt-emoji">{opt.emoji}</span>
						<span class="opt-label">{opt.label}</span>
					</button>
				{/each}
			</div>
		</section>

		<!-- Mood -->
		<section class="card">
			<div class="cat-label">Ánimo</div>
			<div class="options">
				{#each MOOD as opt}
					<button
						class="opt-btn"
						class:selected={mood === opt.level}
						onclick={() => mood = mood === opt.level ? null : opt.level}
					>
						<span class="opt-emoji">{opt.emoji}</span>
						<span class="opt-label">{opt.label}</span>
					</button>
				{/each}
			</div>
		</section>

		<!-- Notes -->
		<section class="card">
			<div class="cat-label">Notas <span class="optional">(opcional)</span></div>
			<textarea
				class="notes"
				bind:value={notes}
				placeholder="¿Algo que quieras recordar de hoy?"
				rows="3"
			></textarea>
		</section>

		<!-- Save -->
		<button class="save-btn" onclick={save} disabled={saving || !hasAny}>
			{saving ? 'Guardando...' : 'Guardar'}
		</button>
	{/if}
</div>

<style>
	.shell {
		position: relative;
		z-index: 1;
		max-width: 480px;
		margin: 0 auto;
		padding: 24px 16px 80px;
		min-height: 100dvh;
		color: #fff;
	}

	.header {
		display: flex;
		align-items: center;
		gap: 12px;
		margin-bottom: 24px;
	}
	.back-btn {
		padding: 8px 14px;
		border-radius: 99px;
		background: rgba(255,255,255,0.05);
		border: 1px solid rgba(255,255,255,0.1);
		color: rgba(255,255,255,0.85);
		font-family: inherit;
		font-size: 13px;
		cursor: pointer;
		white-space: nowrap;
	}
	.header-text { flex: 1; }
	.label {
		font-size: 11px;
		color: rgba(255,255,255,0.4);
		text-transform: uppercase;
		letter-spacing: 0.1em;
	}
	.date {
		font-size: 17px;
		font-weight: 700;
		text-transform: capitalize;
	}

	.loading {
		text-align: center;
		color: rgba(255,255,255,0.4);
		margin-top: 48px;
	}

	.card {
		background: rgba(255,255,255,0.05);
		border: 1px solid rgba(255,255,255,0.09);
		border-radius: 16px;
		padding: 16px;
		margin-bottom: 12px;
	}

	.cat-label {
		font-size: 11px;
		color: rgba(255,255,255,0.45);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		margin-bottom: 12px;
	}
	.optional {
		font-size: 10px;
		color: rgba(255,255,255,0.25);
		text-transform: none;
		letter-spacing: 0;
	}

	.options {
		display: flex;
		gap: 8px;
	}
	.opt-btn {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 6px;
		padding: 12px 8px;
		border-radius: 12px;
		background: rgba(255,255,255,0.04);
		border: 1px solid rgba(255,255,255,0.07);
		cursor: pointer;
		transition: all 0.15s;
	}
	.opt-btn:hover {
		background: rgba(255,255,255,0.08);
	}
	.opt-btn.selected {
		background: rgba(255,255,255,0.12);
		border-color: rgba(255,255,255,0.25);
	}
	.opt-emoji { font-size: 28px; line-height: 1; }
	.opt-label {
		font-size: 10px;
		color: rgba(255,255,255,0.5);
		font-family: inherit;
	}
	.opt-btn.selected .opt-label { color: rgba(255,255,255,0.85); }

	.notes {
		width: 100%;
		background: rgba(0,0,0,0.2);
		border: 1px solid rgba(255,255,255,0.08);
		border-radius: 10px;
		color: #fff;
		font-family: inherit;
		font-size: 13px;
		padding: 10px 12px;
		resize: none;
		outline: none;
		box-sizing: border-box;
	}
	.notes::placeholder { color: rgba(255,255,255,0.25); }
	.notes:focus { border-color: oklch(75% 0.18 165 / 0.4); }

	.save-btn {
		width: 100%;
		height: 52px;
		border-radius: 14px;
		border: none;
		background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		color: #041010;
		font-family: inherit;
		font-weight: 800;
		font-size: 15px;
		cursor: pointer;
		margin-top: 8px;
		box-shadow: 0 8px 24px -6px oklch(75% 0.22 165 / 0.55);
	}
	.save-btn:disabled {
		opacity: 0.4;
		cursor: default;
	}
</style>
