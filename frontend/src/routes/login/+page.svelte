<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { TokenResponse } from '$lib/types';

	let mode: 'login' | 'register' = $state('login');
	let email = $state('');
	let password = $state('');
	let name = $state('');
	let error = $state('');
	let loading = $state(false);

	async function submit() {
		error = '';
		loading = true;
		try {
			let res: TokenResponse;
			if (mode === 'register') {
				res = await api.post<TokenResponse>('/auth/register', { email, password, name });
			} else {
				res = await api.post<TokenResponse>('/auth/login', { email, password });
			}
			auth.login(res.access_token, res.user);
			goto('/');
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Error';
		} finally {
			loading = false;
		}
	}
</script>

<div style="display:flex; flex-direction:column; justify-content:center; min-height:80dvh;">
	<h1 style="text-align:center; font-size:2rem; margin-bottom:0.5rem;">Uroboros</h1>
	<p style="text-align:center; color:var(--text-muted); margin-bottom:2rem;">Tracking de macros para dos</p>

	<div class="card">
		<div style="display:flex; gap:0.5rem; margin-bottom:1rem;">
			<button class:btn-secondary={mode !== 'login'} onclick={() => mode = 'login'} style="flex:1;">Login</button>
			<button class:btn-secondary={mode !== 'register'} onclick={() => mode = 'register'} style="flex:1;">Registro</button>
		</div>

		<form onsubmit={e => { e.preventDefault(); submit(); }}>
			{#if mode === 'register'}
				<div class="form-group">
					<label for="name">Nombre</label>
					<input id="name" bind:value={name} required />
				</div>
			{/if}
			<div class="form-group">
				<label for="email">Email</label>
				<input id="email" type="email" bind:value={email} required />
			</div>
			<div class="form-group">
				<label for="password">Contraseña</label>
				<input id="password" type="password" bind:value={password} minlength="8" required />
			</div>

			{#if error}<p class="error">{error}</p>{/if}

			<button type="submit" disabled={loading} style="width:100%; margin-top:0.5rem;">
				{loading ? '...' : mode === 'login' ? 'Entrar' : 'Crear cuenta'}
			</button>
		</form>
	</div>
</div>
