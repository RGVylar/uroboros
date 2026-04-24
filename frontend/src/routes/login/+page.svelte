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
			goto(mode === 'register' ? '/goals?new=1' : '/');
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Error';
		} finally {
			loading = false;
		}
	}
</script>

<div style="display:flex; flex-direction:column; justify-content:center; min-height:85dvh; padding:1.25rem;">
	<!-- Logo -->
	<div style="text-align:center; margin-bottom:2.25rem;">
		<div style="width:64px; height:64px; border-radius:20px; margin:0 auto 0.875rem; background:linear-gradient(135deg, oklch(82% 0.18 160), oklch(62% 0.2 210)); display:flex; align-items:center; justify-content:center; font-weight:800; color:#041010; font-size:2rem; letter-spacing:-0.125em; box-shadow:0 14px 40px oklch(75% 0.2 190 / 0.45);">U</div>
		<h1 style="font-size:2.625rem; color:#fff; letter-spacing:-0.075em; line-height:1; font-family:'Lora','Georgia',serif; font-weight:400; margin:0;">uroboros</h1>
		<div style="font-size:0.75rem; color:rgba(255,255,255,0.5); margin-top:0.375rem;">Come mejor. Juntos.</div>
	</div>

	<!-- Mode tabs -->
	<div style="display:flex; padding:3px; background:rgba(255,255,255,0.04); border-radius:99px; margin-bottom:1.25rem; border:1px solid rgba(255,255,255,0.08);">
		<button onclick={() => mode = 'login'} style="flex:1; padding:0.625rem; border-radius:99px; border:none; cursor:pointer; font-family:inherit; font-weight:700; font-size:0.75rem; transition:background 0.15s, color 0.15s; background:{mode==='login' ? 'rgba(255,255,255,0.09)' : 'transparent'}; color:{mode==='login' ? '#fff' : 'rgba(255,255,255,0.5)'};">Entrar</button>
		<button onclick={() => mode = 'register'} style="flex:1; padding:0.625rem; border-radius:99px; border:none; cursor:pointer; font-family:inherit; font-weight:700; font-size:0.75rem; transition:background 0.15s, color 0.15s; background:{mode==='register' ? 'rgba(255,255,255,0.09)' : 'transparent'}; color:{mode==='register' ? '#fff' : 'rgba(255,255,255,0.5)'};">Crear cuenta</button>
	</div>

	<!-- Form -->
	<div style="background:rgba(255,255,255,0.05); backdrop-filter:blur(24px) saturate(160%); -webkit-backdrop-filter:blur(24px) saturate(160%); border:1px solid rgba(255,255,255,0.09); border-radius:22px; padding:1.25rem;">
		<form onsubmit={e => { e.preventDefault(); submit(); }}>
			{#if mode === 'register'}
				<div class="form-group">
					<label for="name" style="font-size:0.6875rem; font-weight:600; color:rgba(255,255,255,0.6); text-transform:uppercase; letter-spacing:0.05em;">Nombre</label>
					<input id="name" bind:value={name} placeholder="Rubén" required />
				</div>
			{/if}
			<div class="form-group">
				<label for="email" style="font-size:0.6875rem; font-weight:600; color:rgba(255,255,255,0.6); text-transform:uppercase; letter-spacing:0.05em;">Email</label>
				<input id="email" type="email" bind:value={email} placeholder="tu@email.com" required />
			</div>
			<div class="form-group">
				<label for="password" style="font-size:0.6875rem; font-weight:600; color:rgba(255,255,255,0.6); text-transform:uppercase; letter-spacing:0.05em;">Contraseña</label>
				<input id="password" type="password" bind:value={password} placeholder="••••••••" minlength="8" required />
			</div>

			{#if error}
				<p style="color:oklch(75% 0.2 25); font-size:0.8rem; margin:0.5rem 0;">{error}</p>
			{/if}

			<button type="submit" disabled={loading} style="width:100%; height:48px; border-radius:14px; border:none; cursor:pointer; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-weight:800; font-size:0.875rem; font-family:inherit; box-shadow:0 8px 24px -6px oklch(75% 0.22 165 / 0.55); margin-top:0.375rem; opacity:{loading ? 0.7 : 1};">
				{loading ? '...' : mode === 'login' ? 'Entrar' : 'Crear cuenta'}
			</button>
		</form>
	</div>
</div>
