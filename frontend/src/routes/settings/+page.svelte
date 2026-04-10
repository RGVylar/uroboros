<script lang="ts">
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte';

	if (!auth.isLoggedIn) goto('/login');

	function logout() {
		auth.logout();
		goto('/login');
	}
</script>

<h1>Configuración</h1>

<div class="card" style="margin-bottom:1rem;">
	<div style="margin-bottom:0.5rem;">
		<span style="color:var(--text-muted); font-size:0.85rem;">Usuario</span>
		<div style="font-weight:600;">{auth.user?.name}</div>
	</div>
	<div>
		<span style="color:var(--text-muted); font-size:0.85rem;">Email</span>
		<div>{auth.user?.email}</div>
	</div>
</div>

<button class="btn-danger" onclick={logout} style="width:100%;">Cerrar sesión</button>

<div style="text-align:center; margin-top:2rem; color:var(--text-muted); font-size:0.75rem;">
	v0.2.0
</div>
