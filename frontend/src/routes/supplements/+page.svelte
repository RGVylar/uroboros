<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import { DAY_LABELS, type UserSupplement } from '$lib/types';
	import Aurora from '$lib/components/uro/Aurora.svelte';
	import ScreenHeader from '$lib/components/uro/ScreenHeader.svelte';
	import GlassCard from '$lib/components/uro/GlassCard.svelte';
	if (!auth.isLoggedIn) goto('/login');

	const LS_KEY = 'supplements_enabled';

	let supplements: UserSupplement[] = $state([]);
	let newName = $state('');
	let newDays: number[] | null = $state(null); // null = todos los días
	let adding = $state(false);
	let enabled = $state(true);

	$effect(() => {
		enabled = localStorage.getItem(LS_KEY) !== 'false';
	});

	async function load() {
		supplements = await api.get<UserSupplement[]>('/supplements').catch(() => []);
	}

	load();

	function toggleEnabled() {
		enabled = !enabled;
		localStorage.setItem(LS_KEY, String(enabled));
	}

	function toggleNewDay(d: number) {
		if (newDays === null) {
			newDays = DAY_LABELS.map((_, i) => i).filter(i => i !== d);
		} else if (newDays.includes(d)) {
			const next = newDays.filter(x => x !== d);
			newDays = next.length === 0 ? null : next;
		} else {
			const next = [...newDays, d].sort();
			newDays = next.length === 7 ? null : next;
		}
	}

	function isDayActive(days: number[] | null, d: number): boolean {
		return days === null || days.includes(d);
	}

	async function add() {
		const name = newName.trim();
		if (!name) return;
		adding = true;
		try {
			await api.post('/supplements', { name, days_of_week: newDays });
			newName = '';
			newDays = null;
			await load();
		} catch {
			// ignore
		} finally {
			adding = false;
		}
	}

	async function updateDays(s: UserSupplement, days: number[] | null) {
		await api.put(`/supplements/${s.id}`, { name: s.name, days_of_week: days }).catch(() => {});
		await load();
	}

	async function remove(id: number) {
		await api.del(`/supplements/${id}`).catch(() => {});
		await load();
	}

	function dayLabel(days: number[] | null): string {
		if (!days || days.length === 7) return 'Todos los días';
		return `${days.length} días/sem`;
	}

	function toggleExistingDay(s: UserSupplement, d: number) {
		const cur = s.days_of_week;
		let next: number[] | null;
		if (cur === null) {
			next = DAY_LABELS.map((_, i) => i).filter(i => i !== d);
		} else if (cur.includes(d)) {
			const r = cur.filter(x => x !== d);
			next = r.length === 0 ? null : r.length === 7 ? null : r;
		} else {
			const r = [...cur, d].sort();
			next = r.length === 7 ? null : r;
		}
		updateDays(s, next);
	}
</script>

<Aurora />

<div class="page">
	<ScreenHeader
		title="Suplementos"
		sub={enabled ? `${supplements.length} ${supplements.length === 1 ? 'activo' : 'activos'} · checks en el diario` : 'Tracking pausado'}
		onBack={() => goto('/settings')}
	/>

	<!-- Master toggle -->
	<div class="master">
		<div class="master-icon" class:on={enabled}>💊</div>
		<div class="master-text">
			<div class="master-title">Mostrar en el diario</div>
			<div class="master-sub">Checks rápidos según el día de la semana</div>
		</div>
		<button class="switch" class:on={enabled} onclick={toggleEnabled} aria-label="Activar suplementos">
			<span class="knob"></span>
		</button>
	</div>

	{#if enabled}
		<!-- Lista -->
		{#if supplements.length > 0}
			<div class="stack">
				{#each supplements as s (s.id)}
					<GlassCard padding={14}>
						<div class="row-head">
							<div class="row-icon">💊</div>
							<div class="row-texts">
								<div class="row-name">{s.name}</div>
								<div class="row-sub">{dayLabel(s.days_of_week)}</div>
							</div>
							<button class="row-remove" onclick={() => remove(s.id)} aria-label="Eliminar">✕</button>
						</div>
						<div class="days">
							{#each DAY_LABELS as l, d}
								{@const a = isDayActive(s.days_of_week, d)}
								<button class="day" class:on={a} onclick={() => toggleExistingDay(s, d)}>{l}</button>
							{/each}
						</div>
					</GlassCard>
				{/each}
			</div>
		{:else}
			<div class="empty">
				<div class="empty-icon">💊</div>
				<div class="empty-title">Sin suplementos aún</div>
				<div class="empty-sub">Añade el primero abajo</div>
			</div>
		{/if}

		<!-- Añadir nuevo -->
		<div class="add-card" accent>
			<div class="add-label">Nuevo suplemento</div>
			<input
				bind:value={newName}
				placeholder="Ej. Vitamina C"
				onkeydown={(e) => e.key === 'Enter' && add()}
			/>
			<div class="days-label">Días</div>
			<div class="days">
				{#each DAY_LABELS as l, d}
					{@const a = isDayActive(newDays, d)}
					<button class="day" class:on={a} onclick={() => toggleNewDay(d)}>{l}</button>
				{/each}
			</div>
			<div class="days-hint">{dayLabel(newDays)}</div>
			<button class="add-btn" onclick={add} disabled={adding || !newName.trim()}>
				{adding ? '…' : '＋ Añadir'}
			</button>
		</div>
	{/if}
</div>

<style>
	.page {
		position: relative;
		z-index: 1;
		max-width: 560px;
		margin: 0 auto;
		padding: 8px 16px 120px;
	}

	/* Master toggle */
	.master {
		display: flex; align-items: center; gap: 12px;
		padding: 14px;
		margin-bottom: 14px;
		border-radius: 18px;
		background: rgba(255, 255, 255, 0.05);
		backdrop-filter: blur(24px) saturate(160%);
		-webkit-backdrop-filter: blur(24px) saturate(160%);
		border: 1px solid rgba(255, 255, 255, 0.09);
	}
	.master-icon {
		width: 36px; height: 36px; border-radius: 12px;
		background: rgba(255, 255, 255, 0.05);
		border: 1px solid rgba(255, 255, 255, 0.08);
		display: flex; align-items: center; justify-content: center;
		font-size: 16px;
		flex-shrink: 0;
	}
	.master-icon.on {
		background: linear-gradient(135deg, oklch(78% 0.18 165 / 0.3), oklch(60% 0.2 200 / 0.15));
		border-color: oklch(75% 0.18 165 / 0.35);
	}
	.master-text { flex: 1; min-width: 0; color: #fff; }
	.master-title { font-size: 13px; font-weight: 700; }
	.master-sub { font-size: 10px; color: rgba(255, 255, 255, 0.5); margin-top: 2px; }

	.switch {
		width: 40px; height: 24px; border-radius: 99px;
		position: relative; flex-shrink: 0;
		background: rgba(255, 255, 255, 0.08);
		border: 1px solid rgba(255, 255, 255, 0.1);
		cursor: pointer;
		padding: 0;
	}
	.switch.on {
		background: oklch(75% 0.18 165 / 0.35);
		border-color: oklch(80% 0.17 165 / 0.5);
	}
	.knob {
		position: absolute; top: 2px; left: 2px;
		width: 18px; height: 18px; border-radius: 50%;
		background: #d0d4d8;
		box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3);
		transition: all 0.15s;
	}
	.switch.on .knob {
		left: 18px;
		background: linear-gradient(135deg, #fff, oklch(85% 0.1 165));
	}

	/* List */
	.stack { display: flex; flex-direction: column; gap: 10px; margin-bottom: 14px; }
	.row-head {
		display: flex; align-items: center; gap: 12px; margin-bottom: 10px;
	}
	.row-icon {
		width: 38px; height: 38px; border-radius: 12px;
		background: linear-gradient(135deg, oklch(72% 0.16 165 / 0.3), oklch(55% 0.18 185 / 0.15));
		border: 1px solid oklch(72% 0.16 165 / 0.3);
		display: flex; align-items: center; justify-content: center;
		font-size: 18px;
		flex-shrink: 0;
	}
	.row-texts { flex: 1; min-width: 0; }
	.row-name { font-size: 13px; font-weight: 700; color: #fff; }
	.row-sub { font-size: 10px; color: rgba(255, 255, 255, 0.5); margin-top: 2px; }
	.row-remove {
		width: 30px; height: 30px; border-radius: 50%;
		background: rgba(255, 255, 255, 0.04);
		border: 1px solid rgba(255, 255, 255, 0.08);
		color: rgba(255, 255, 255, 0.5);
		font-size: 12px;
		cursor: pointer;
		font-family: inherit;
		flex-shrink: 0;
		padding: 0;
		line-height: 1;
	}

	/* Day toggles */
	.days {
		display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px;
	}
	.day {
		padding: 6px 0;
		border-radius: 9px;
		background: rgba(255, 255, 255, 0.04);
		border: 1px solid rgba(255, 255, 255, 0.06);
		color: rgba(255, 255, 255, 0.35);
		font: inherit;
		font-weight: 500;
		font-size: 11px;
		cursor: pointer;
	}
	.day.on {
		background: linear-gradient(180deg, oklch(75% 0.16 165 / 0.3), oklch(55% 0.18 165 / 0.15));
		border-color: oklch(75% 0.16 165 / 0.4);
		color: #fff;
		font-weight: 700;
	}

	/* Empty */
	.empty {
		text-align: center;
		padding: 30px 20px;
		margin-bottom: 14px;
		border-radius: 18px;
		border: 1px dashed rgba(255, 255, 255, 0.1);
		background: rgba(255, 255, 255, 0.02);
	}
	.empty-icon { font-size: 30px; opacity: 0.5; margin-bottom: 8px; }
	.empty-title { font-size: 13px; font-weight: 700; color: #fff; }
	.empty-sub { font-size: 11px; color: rgba(255, 255, 255, 0.5); margin-top: 2px; }

	/* Add new */
	.add-card {
		padding: 14px;
		border-radius: 18px;
		background: rgba(255, 255, 255, 0.05);
		backdrop-filter: blur(24px) saturate(160%);
		-webkit-backdrop-filter: blur(24px) saturate(160%);
		border: 1px solid rgba(255, 255, 255, 0.12);
		position: relative;
	}
	.add-card::before {
		content: '';
		position: absolute;
		top: 0; left: 10%; right: 10%; height: 1px;
		background: linear-gradient(90deg, transparent, oklch(85% 0.17 160), transparent);
		opacity: 0.6;
		border-radius: inherit;
	}
	.add-label {
		font-size: 10px; color: rgba(255, 255, 255, 0.55);
		text-transform: uppercase; letter-spacing: 1px; font-weight: 700;
		margin-bottom: 8px;
	}
	.add-card input {
		width: 100%;
		padding: 12px 14px;
		margin-bottom: 10px;
		border-radius: 12px;
		background: rgba(0, 0, 0, 0.2);
		border: 1px solid rgba(255, 255, 255, 0.08);
		color: #fff;
		font-size: 13px;
		font-family: inherit;
		outline: none;
		box-sizing: border-box;
	}
	.add-card input:focus { border-color: oklch(75% 0.18 165 / 0.4); }

	.days-label {
		font-size: 10px; color: rgba(255, 255, 255, 0.5);
		margin-bottom: 6px;
	}
	.days-hint {
		font-size: 11px; color: rgba(255, 255, 255, 0.45);
		margin: 8px 2px 12px;
	}
	.add-btn {
		width: 100%; padding: 12px;
		border-radius: 12px;
		border: none;
		background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		color: #041010;
		font-family: inherit;
		font-weight: 800;
		font-size: 13px;
		cursor: pointer;
	}
	.add-btn:disabled { opacity: 0.5; cursor: default; }
</style>
