<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { UserSupplement } from '$lib/types';
	if (!auth.isLoggedIn) goto('/login');

	const LS_KEY = 'supplements_enabled';

	let supplements: UserSupplement[] = $state([]);
	let newName = $state('');
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

	async function add() {
		const name = newName.trim();
		if (!name) return;
		adding = true;
		try {
			await api.post('/supplements', { name });
			newName = '';
			await load();
		} catch {
			// ignore
		} finally {
			adding = false;
		}
	}

	async function remove(id: number) {
		await api.del(`/supplements/${id}`).catch(() => {});
		await load();
	}
</script>

<div style="max-width:480px; margin:0 auto; padding:1rem;">
	<div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:1.5rem;">
		<button onclick={() => goto('/settings')} style="background:none; border:none; cursor:pointer; font-size:1.2rem; color:var(--text-muted); padding:0; box-shadow:none;">‹</button>
		<h1 style="margin:0; font-size:1.1rem; font-weight:700;">Suplementos</h1>
	</div>

	<!-- Enable toggle -->
	<div class="card" style="display:flex; align-items:center; justify-content:space-between; padding:0.75rem 1rem; margin-bottom:1.25rem; cursor:default;">
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
		<p style="font-size:0.82rem; color:var(--text-muted); margin-bottom:1rem;">
			Suplementos que tomas a diario. Márcalos cada día desde la pantalla principal.
		</p>

		{#if supplements.length === 0}
			<div style="text-align:center; padding:2rem 0; color:var(--text-muted); font-size:0.88rem;">
				Sin suplementos todavía
			</div>
		{:else}
			<div style="display:flex; flex-direction:column; gap:0.5rem; margin-bottom:1.25rem;">
				{#each supplements as s (s.id)}
					<div class="card" style="display:flex; align-items:center; justify-content:space-between; padding:0.75rem 1rem;">
						<span style="font-size:0.9rem; font-weight:600;">{s.name}</span>
						<button
							onclick={() => remove(s.id)}
							style="background:none; border:none; cursor:pointer; color:var(--text-muted); font-size:1rem; padding:0; box-shadow:none; line-height:1;"
							aria-label="Eliminar"
						>✕</button>
					</div>
				{/each}
			</div>
		{/if}

		<div style="display:flex; gap:0.5rem;">
			<input
				bind:value={newName}
				placeholder="Nombre del suplemento..."
				onkeydown={(e) => e.key === 'Enter' && add()}
				style="flex:1; padding:0.65rem 0.85rem; border-radius:12px; border:1px solid rgba(255,255,255,0.12); background:rgba(255,255,255,0.06); color:inherit; font-size:0.88rem; font-family:inherit;"
			/>
			<button onclick={add} disabled={adding || !newName.trim()} style="padding:0.65rem 1.1rem; font-size:0.85rem; font-weight:700;">
				+ Añadir
			</button>
		</div>
	{/if}
</div>
