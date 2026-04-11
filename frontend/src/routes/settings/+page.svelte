<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import { pendingFriends } from '$lib/stores/friends.svelte';
	import type { Goals } from '$lib/types';

	if (!auth.isLoggedIn) goto('/login');

	let goals: Goals | null = $state(null);
	let savingCreatine = $state(false);

	async function loadGoals() {
		goals = await api.get<Goals>('/goals').catch(() => null);
	}

	loadGoals();

	async function toggleCreatine() {
		if (!goals) return;
		savingCreatine = true;
		try {
			goals = await api.put<Goals>('/goals', { ...goals, track_creatine: !goals.track_creatine });
		} catch {
			// ignore
		} finally {
			savingCreatine = false;
		}
	}

	function logout() {
		auth.logout();
		goto('/login');
	}
</script>

<h1 style="font-size:1.3rem; font-weight:800; margin-bottom:1.25rem;">Ajustes</h1>

<!-- User info -->
<div class="card" style="margin-bottom:1rem;">
	<div style="display:flex; align-items:center; gap:0.75rem;">
		<div style="width:42px; height:42px; border-radius:50%; background:var(--primary); display:flex; align-items:center; justify-content:center; font-size:1.1rem; font-weight:800; color:#000; flex-shrink:0;">
			{(auth.user?.name ?? '?')[0].toUpperCase()}
		</div>
		<div>
			<div style="font-weight:700; font-size:1rem;">{auth.user?.name}</div>
			<div style="font-size:0.8rem; color:var(--text-muted);">{auth.user?.email}</div>
		</div>
	</div>
</div>

<!-- Quick actions -->
<div style="display:flex; flex-direction:column; gap:0.5rem; margin-bottom:1.25rem;">

	<!-- Metas -->
	<button onclick={() => goto('/goals')} style="
		display:flex; align-items:center; gap:0.9rem;
		width:100%; text-align:left; background:var(--surface);
		border:1px solid var(--border); border-radius:14px;
		padding:0.85rem 1rem; cursor:pointer; transition:border-color 0.2s;
	">
		<span style="font-size:1.4rem;">🎯</span>
		<div style="flex:1;">
			<div style="font-weight:700; font-size:0.95rem;">Objetivos</div>
			<div style="font-size:0.75rem; color:var(--text-muted);">Calorías, macros y calculadora TDEE</div>
		</div>
		<span style="color:var(--text-muted); font-size:1rem;">›</span>
	</button>

	<!-- Peso -->
	<button onclick={() => goto('/weight')} style="
		display:flex; align-items:center; gap:0.9rem;
		width:100%; text-align:left; background:var(--surface);
		border:1px solid var(--border); border-radius:14px;
		padding:0.85rem 1rem; cursor:pointer; transition:border-color 0.2s;
	">
		<span style="font-size:1.4rem;">⚖️</span>
		<div style="flex:1;">
			<div style="font-weight:700; font-size:0.95rem;">Registro de peso</div>
			<div style="font-size:0.75rem; color:var(--text-muted);">Seguimiento de tu evolución</div>
		</div>
		<span style="color:var(--text-muted); font-size:1rem;">›</span>
	</button>

	<!-- Amigos -->
	<button onclick={() => goto('/friends')} style="
		display:flex; align-items:center; gap:0.9rem;
		width:100%; text-align:left; background:var(--surface);
		border:1px solid var(--border); border-radius:14px;
		padding:0.85rem 1rem; cursor:pointer; transition:border-color 0.2s;
	">
		<span style="font-size:1.4rem;">👥</span>
		<div style="flex:1;">
			<div style="font-weight:700; font-size:0.95rem; display:flex; align-items:center; gap:0.4rem;">
				Amigos
				{#if pendingFriends.count > 0}
					<span style="background:var(--danger); color:#fff; border-radius:99px; padding:0.05rem 0.45rem; font-size:0.65rem; font-weight:800; line-height:1.4;">
						{pendingFriends.count}
					</span>
				{/if}
			</div>
			<div style="font-size:0.75rem; color:var(--text-muted);">Gestiona amigos y permisos</div>
		</div>
		<span style="color:var(--text-muted); font-size:1rem;">›</span>
	</button>

	<!-- Creatina -->
	{#if goals}
		<div style="
			display:flex; align-items:center; gap:0.9rem;
			background:var(--surface);
			border:1px solid var(--border); border-radius:14px;
			padding:0.85rem 1rem;
		">
			<span style="font-size:1.4rem;">💊</span>
			<div style="flex:1;">
				<div style="font-weight:700; font-size:0.95rem;">Registro de creatina</div>
				<div style="font-size:0.75rem; color:var(--text-muted);">
					{goals.track_creatine ? 'Activo · check diario en el inicio' : 'Registra si te la tomas cada día'}
				</div>
			</div>
			<!-- Toggle switch -->
			<button
				onclick={toggleCreatine}
				disabled={savingCreatine}
				aria-label="Activar registro de creatina"
				style="
					position:relative; width:44px; height:24px; border-radius:12px;
					border:none; cursor:pointer; transition:background 0.2s;
					background:{goals.track_creatine ? 'var(--primary)' : 'var(--border-bright)'};
					flex-shrink:0; padding:0;
				"
			>
				<span style="
					position:absolute; top:3px;
					left:{goals.track_creatine ? '23px' : '3px'};
					width:18px; height:18px; border-radius:50%;
					background:#fff; transition:left 0.2s;
					box-shadow:0 1px 3px rgba(0,0,0,0.3);
					display:block;
				"></span>
			</button>
		</div>
	{/if}

</div>

<button class="btn-danger" onclick={logout} style="width:100%;">Cerrar sesión</button>

<div style="text-align:center; margin-top:2rem; color:var(--text-muted); font-size:0.75rem;">
	v0.3.0
</div>
