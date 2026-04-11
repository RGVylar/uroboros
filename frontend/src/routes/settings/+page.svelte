<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import { pendingFriends } from '$lib/stores/friends.svelte';

	if (!auth.isLoggedIn) goto('/login');

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

</div>

<button class="btn-danger" onclick={logout} style="width:100%;">Cerrar sesión</button>

<div style="text-align:center; margin-top:2rem; color:var(--text-muted); font-size:0.75rem;">
	v0.3.0
</div>
