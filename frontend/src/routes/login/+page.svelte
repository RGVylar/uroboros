<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { TokenResponse } from '$lib/types';
	import Aurora from '$lib/components/uro/Aurora.svelte';
	import GlassCard from '$lib/components/uro/GlassCard.svelte';

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

<Aurora />

<div class="login-shell">
	<!-- Logo + name -->
	<div class="brand">
		<img src="/logo.png" alt="uroboros" class="logo" />
		<h1 class="title"><em>uroboros</em></h1>
		<div class="tagline">Come mejor. Juntos.</div>
	</div>

	<!-- Tabs -->
	<div class="tabs">
		{#each [{ k: 'login' as const, l: 'Entrar' }, { k: 'register' as const, l: 'Crear cuenta' }] as t}
			<button
				class="tab"
				class:active={mode === t.k}
				onclick={() => mode = t.k}
			>{t.l}</button>
		{/each}
	</div>

	<!-- Form -->
	<GlassCard padding={18}>
		<form onsubmit={(e) => { e.preventDefault(); submit(); }}>
			{#if mode === 'register'}
				<label class="field">
					<span>Nombre</span>
					<input bind:value={name} placeholder="Rubén" required autocomplete="name" />
				</label>
			{/if}

			<label class="field">
				<span>Email</span>
				<input type="email" bind:value={email} placeholder="tu@email.com" required autocomplete="email" />
			</label>

			<label class="field">
				<span>Contraseña</span>
				<input type="password" bind:value={password} placeholder="••••••••" minlength="8" required autocomplete={mode === 'login' ? 'current-password' : 'new-password'} />
			</label>

			{#if mode === 'login'}
				<div class="forgot">
					<a href="/forgot-password">¿Olvidaste la contraseña?</a>
				</div>
			{/if}

			{#if error}<p class="error-msg">{error}</p>{/if}

			<button type="submit" class="submit-btn" disabled={loading}>
				{loading ? '...' : mode === 'login' ? 'Entrar' : 'Crear cuenta'}
			</button>

			{#if mode === 'register'}
				<p class="legal-fine">
					Al crear una cuenta aceptas nuestros
					<a href="/terms">términos</a>
					y la
					<a href="/privacy">política de privacidad</a>.
				</p>
			{/if}
		</form>
	</GlassCard>

	<!-- Footer legal links -->
	<div class="login-footer">
		<a href="/privacy">Privacidad</a>
		<span>·</span>
		<a href="/terms">Términos</a>
	</div>
</div>

<style>
	.login-shell {
		position: relative;
		z-index: 1;
		max-width: 420px;
		margin: 0 auto;
		padding: 32px 20px 40px;
		min-height: 100dvh;
		display: flex;
		flex-direction: column;
		justify-content: center;
		color: #fff;
	}

	/* Brand */
	.brand { text-align: center; margin-bottom: 32px; }
	.logo {
		width: 96px; height: 96px;
		margin: 0 auto 14px;
		display: block;
		filter: drop-shadow(0 8px 24px oklch(75% 0.2 190 / 0.5));
	}
	.title {
		font-family: 'Instrument Serif', 'Lora', Georgia, serif;
		font-weight: 400;
		font-size: 42px;
		letter-spacing: -1.2px;
		line-height: 1;
		margin: 0;
	}
	.title em { color: oklch(85% 0.17 160); font-style: italic; }
	.tagline {
		font-size: 12px;
		color: rgba(255, 255, 255, 0.5);
		margin-top: 6px;
	}

	/* Tabs */
	.tabs {
		display: flex;
		gap: 0;
		padding: 3px;
		margin-bottom: 16px;
		background: rgba(255, 255, 255, 0.04);
		border: 1px solid rgba(255, 255, 255, 0.08);
		border-radius: 99px;
	}
	.tab {
		flex: 1;
		padding: 10px;
		border-radius: 99px;
		background: transparent;
		border: none;
		cursor: pointer;
		color: rgba(255, 255, 255, 0.5);
		font: inherit;
		font-weight: 700;
		font-size: 12px;
		transition: all 0.15s;
	}
	.tab.active {
		background: rgba(255, 255, 255, 0.09);
		color: #fff;
	}

	/* Form */
	form { display: flex; flex-direction: column; gap: 0; }
	.field {
		display: block;
		margin-bottom: 12px;
	}
	.field span {
		display: block;
		font-size: 10px;
		color: rgba(255, 255, 255, 0.55);
		margin-bottom: 6px;
		letter-spacing: 0.4px;
		font-weight: 600;
		text-transform: uppercase;
	}
	.field input {
		width: 100%;
		padding: 12px 14px;
		border-radius: 12px;
		background: rgba(0, 0, 0, 0.2);
		border: 1px solid rgba(255, 255, 255, 0.08);
		color: #fff;
		font-size: 13px;
		font-family: inherit;
		outline: none;
		box-sizing: border-box;
		transition: border-color 0.15s;
	}
	.field input:focus {
		border-color: oklch(75% 0.18 165 / 0.4);
	}
	.forgot { text-align: right; margin: -4px 2px 10px; }
	.forgot a {
		color: oklch(85% 0.15 160);
		font-size: 11px;
		font-weight: 600;
		text-decoration: none;
	}
	.error-msg {
		color: oklch(70% 0.2 25);
		font-size: 12px;
		margin: 4px 2px 8px;
	}
	.submit-btn {
		width: 100%;
		height: 48px;
		border-radius: 14px;
		border: none;
		background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		color: #041010;
		font-family: inherit;
		font-weight: 800;
		font-size: 14px;
		cursor: pointer;
		box-shadow: 0 8px 24px -6px oklch(75% 0.22 165 / 0.55);
		margin-top: 6px;
	}
	.submit-btn:disabled { opacity: 0.5; cursor: default; }

	.legal-fine {
		font-size: 10.5px;
		color: rgba(255, 255, 255, 0.45);
		line-height: 1.5;
		margin: 12px 4px 0;
		text-align: center;
	}
	.legal-fine a {
		color: oklch(85% 0.15 160);
		text-decoration: none;
	}
	.legal-fine a:hover {
		text-decoration: underline;
	}

	.login-footer {
		display: flex;
		justify-content: center;
		gap: 14px;
		margin-top: 20px;
		font-size: 11px;
		color: rgba(255, 255, 255, 0.35);
	}
	.login-footer a {
		color: rgba(255, 255, 255, 0.6);
		text-decoration: none;
	}
	.login-footer a:hover {
		color: oklch(85% 0.15 160);
	}
</style>
