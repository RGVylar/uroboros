<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { api } from '$lib/api';

	let token = $derived($page.url.searchParams.get('token') ?? '');
	let password = $state('');
	let password2 = $state('');
	let loading = $state(false);
	let done = $state(false);
	let error = $state('');

	async function submit() {
		error = '';
		if (password.length < 8) { error = 'La contraseña debe tener al menos 8 caracteres'; return; }
		if (password !== password2) { error = 'Las contraseñas no coinciden'; return; }
		if (!token) { error = 'Enlace inválido'; return; }
		loading = true;
		try {
			await api.post('/auth/reset-password', { token, new_password: password });
			done = true;
			setTimeout(() => goto('/login'), 3000);
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Error';
		} finally {
			loading = false;
		}
	}
</script>

<div style="display:flex; flex-direction:column; justify-content:center; min-height:85dvh; padding:1.25rem;">
	<div style="text-align:center; margin-bottom:2rem;">
		<div style="width:64px; height:64px; border-radius:20px; margin:0 auto 0.875rem; background:linear-gradient(135deg, oklch(82% 0.18 160), oklch(62% 0.2 210)); display:flex; align-items:center; justify-content:center; font-size:2rem; font-weight:800; color:#041010; letter-spacing:-0.125em; box-shadow:0 14px 40px oklch(75% 0.2 190 / 0.45);">U</div>
		<h1 style="font-size:1.75rem; color:#fff; letter-spacing:-0.05em; font-family:'Lora','Georgia',serif; font-weight:400; margin:0;">Nueva contraseña</h1>
	</div>

	{#if !token}
		<div style="background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.09); border-radius:22px; padding:1.5rem; text-align:center;">
			<div style="font-size:2rem; margin-bottom:0.5rem;">⚠️</div>
			<div style="color:oklch(75% 0.2 25); font-size:0.875rem;">Enlace inválido. Solicita uno nuevo desde la pantalla de inicio de sesión.</div>
			<a href="/forgot-password" style="display:inline-block; margin-top:1rem; color:oklch(85% 0.15 160); font-weight:600; text-decoration:none;">Solicitar enlace</a>
		</div>
	{:else if done}
		<div style="background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.09); border-radius:22px; padding:1.5rem; text-align:center;">
			<div style="font-size:2.5rem; margin-bottom:0.75rem;">✅</div>
			<div style="font-size:1rem; font-weight:700; color:#fff; margin-bottom:0.5rem;">Contraseña cambiada</div>
			<div style="font-size:0.8125rem; color:rgba(255,255,255,0.55);">Redirigiendo al inicio de sesión...</div>
		</div>
	{:else}
		<div style="background:rgba(255,255,255,0.05); backdrop-filter:blur(24px) saturate(160%); border:1px solid rgba(255,255,255,0.09); border-radius:22px; padding:1.25rem;">
			<form onsubmit={(e) => { e.preventDefault(); submit(); }}>
				<div style="margin-bottom:0.875rem;">
					<label for="pw" style="display:block; font-size:0.6875rem; font-weight:600; color:rgba(255,255,255,0.6); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.375rem;">Nueva contraseña</label>
					<input id="pw" type="password" bind:value={password} placeholder="Mínimo 8 caracteres" minlength="8" required style="width:100%; box-sizing:border-box;" />
				</div>
				<div style="margin-bottom:1rem;">
					<label for="pw2" style="display:block; font-size:0.6875rem; font-weight:600; color:rgba(255,255,255,0.6); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.375rem;">Repetir contraseña</label>
					<input id="pw2" type="password" bind:value={password2} placeholder="Repite la contraseña" required style="width:100%; box-sizing:border-box;" />
				</div>

				{#if error}
					<p style="color:oklch(75% 0.2 25); font-size:0.8rem; margin:0 0 0.75rem;">{error}</p>
				{/if}

				<button type="submit" disabled={loading} style="width:100%; height:48px; border-radius:14px; border:none; cursor:pointer; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-weight:800; font-size:0.875rem; font-family:inherit; opacity:{loading ? 0.7 : 1};">
					{loading ? 'Guardando...' : 'Guardar nueva contraseña'}
				</button>
			</form>
		</div>
	{/if}
</div>
