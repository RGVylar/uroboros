<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import { DAY_LABELS, type UserSupplement } from '$lib/types';
	if (!auth.isLoggedIn) goto('/login');

	const LS_KEY = 'supplements_enabled';

	let supplements: UserSupplement[] = $state([]);
	let newName = $state('');
	let newDays: number[] | null = $state(null); // null = every day
	let adding = $state(false);
	let enabled = $state(localStorage.getItem(LS_KEY) !== 'false');

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
			// Switch from "all days" to specific: deselect just this one
			newDays = DAY_LABELS.map((_, i) => i).filter(i => i !== d);
		} else if (newDays.includes(d)) {
			const next = newDays.filter(x => x !== d);
			newDays = next.length === 7 || next.length === 0 ? null : next;
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
		return days.map(d => DAY_LABELS[d]).join(' ');
	}
</script>

<div style="max-width:480px; margin:0 auto; padding:1rem 1rem 6rem;">
	<div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:1.5rem;">
		<button onclick={() => goto('/settings')} style="background:none; border:none; cursor:pointer; font-size:1.4rem; color:var(--text-muted); padding:0; box-shadow:none; line-height:1;">‹</button>
		<h1 style="margin:0; font-size:1.1rem; font-weight:700;">Suplementos</h1>
	</div>

	<!-- Enable toggle -->
	<div class="card" style="display:flex; align-items:center; justify-content:space-between; padding:0.75rem 1rem; margin-bottom:1.5rem; cursor:default;">
		<div>
			<div style="font-size:0.9rem; font-weight:600;">Activar seguimiento</div>
			<div style="font-size:0.75rem; color:var(--text-muted);">Muestra la tarjeta en la pantalla principal</div>
		</div>
		<button
			onclick={toggleEnabled}
			class="toggle-btn"
			style="background:{enabled ? 'oklch(75% 0.18 165 / 0.35)' : 'rgba(255,255,255,0.08)'}; border-color:{enabled ? 'oklch(80% 0.17 165 / 0.5)' : 'rgba(255,255,255,0.1)'};"
		>
			<span class="toggle-knob" style="left:{enabled ? '18px' : '2px'};"></span>
		</button>
	</div>

	{#if enabled}
		<!-- Existing supplements -->
		{#if supplements.length > 0}
			<div style="display:flex; flex-direction:column; gap:0.6rem; margin-bottom:1.5rem;">
				{#each supplements as s (s.id)}
					<div class="card" style="padding:0.75rem 1rem;">
						<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.5rem;">
							<span style="font-size:0.9rem; font-weight:600;">{s.name}</span>
							<button
								onclick={() => remove(s.id)}
								style="background:none; border:none; cursor:pointer; color:var(--text-muted); font-size:1rem; padding:0; box-shadow:none; line-height:1;"
								aria-label="Eliminar"
							>✕</button>
						</div>
						<!-- Day picker for existing supplement -->
						<div style="display:flex; gap:0.3rem;">
							{#each DAY_LABELS as lbl, d}
								{@const active = isDayActive(s.days_of_week, d)}
								<button
									onclick={() => {
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
									}}
									style="flex:1; padding:0.25rem 0; font-size:0.72rem; font-weight:700; border-radius:6px; border:none; cursor:pointer;
										background:{active ? 'var(--primary)' : 'rgba(255,255,255,0.08)'};
										color:{active ? 'var(--primary-ink)' : 'var(--text-muted)'};
										box-shadow:none;"
								>{lbl}</button>
							{/each}
						</div>
					</div>
				{/each}
			</div>
		{/if}

		<!-- Add new supplement -->
		<div class="card" style="padding:0.85rem 1rem;">
			<div style="font-size:0.8rem; font-weight:600; color:var(--text-muted); margin-bottom:0.6rem; text-transform:uppercase; letter-spacing:0.06em;">Añadir suplemento</div>
			<input
				bind:value={newName}
				placeholder="Nombre..."
				onkeydown={(e) => e.key === 'Enter' && add()}
				style="width:100%; padding:0.6rem 0.75rem; border-radius:10px; border:1px solid rgba(255,255,255,0.12); background:rgba(255,255,255,0.06); color:inherit; font-size:0.88rem; font-family:inherit; box-sizing:border-box; margin-bottom:0.6rem;"
			/>
			<!-- Day picker for new supplement -->
			<div style="display:flex; gap:0.3rem; margin-bottom:0.75rem;">
				{#each DAY_LABELS as lbl, d}
					{@const active = isDayActive(newDays, d)}
					<button
						onclick={() => toggleNewDay(d)}
						style="flex:1; padding:0.25rem 0; font-size:0.72rem; font-weight:700; border-radius:6px; border:none; cursor:pointer;
							background:{active ? 'var(--primary)' : 'rgba(255,255,255,0.08)'};
							color:{active ? 'var(--primary-ink)' : 'var(--text-muted)'};
							box-shadow:none;"
					>{lbl}</button>
				{/each}
			</div>
			<div style="font-size:0.7rem; color:var(--text-muted); margin-bottom:0.75rem;">{dayLabel(newDays)}</div>
			<button onclick={add} disabled={adding || !newName.trim()} style="width:100%; padding:0.65rem; font-size:0.85rem; font-weight:700;">
				+ Añadir
			</button>
		</div>
	{/if}
</div>
