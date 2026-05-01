<script lang="ts">
	import { api } from '$lib/api';

	let email = $state('');
	let loading = $state(false);
	let sent = $state(false);
	let error = $state('');

	async function submit() {
		if (!email.trim()) return;
		loading = true;
		error = '';
		try {
			await api.post('/auth/forgot-password', { email: email.trim() });
			sent = true;
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
		<h1 style="font-size:1.75rem; color:#fff; letter-spacing:-0.05em; font-family:'Lora','Georgia',serif; font-weight:400; margin:0;">Recuperar contraseña</h1>
	</div>

	{#if sent}
		<div style="background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.09); border-radius:22px; padding:1.5rem; text-align:center;">
			<div style="font-size:2.5rem; margin-bottom:0.75rem;">📬</div>
			<div style="font-size:1rem; font-weight:700; color:#fff; margin-bottom:0.5rem;">Email enviado</div>
			<div style="font-size:0.8125rem; color:rgba(255,255,255,0.55);">
				Si hay una cuenta con ese email, recibirás un enlace para restablecer tu contraseña.<br><br>
				Revisa también la carpeta de spam.
			</div>
			<a href="/login" style="display:inline-block; margin-top:1.25rem; color:oklch(85% 0.15 160); font-size:0.875rem; font-weight:600; text-decoration:none;">← Volver al inicio de sesión</a>
		</div>
	{:else}
		<div style="background:rgba(255,255,255,0.05); backdrop-filter:blur(24px) saturate(160%); border:1px solid rgba(255,255,255,0.09); border-radius:22px; padding:1.25rem;">
			<p style="font-size:0.8125rem; color:rgba(255,255,255,0.55); margin:0 0 1.25rem;">
				Escribe tu email y te enviaremos un enlace para crear una nueva contraseña.
			</p>
			<form onsubmit={(e) => { e.preventDefault(); submit(); }}>
				<div style="margin-bottom:1rem;">
					<label for="email" style="display:block; font-size:0.6875rem; font-weight:600; color:rgba(255,255,255,0.6); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.375rem;">Email</label>
					<input id="email" type="email" bind:value={email} placeholder="tu@email.com" required style="width:100%; box-sizing:border-box;" />
				</div>

				{#if error}
					<p style="color:oklch(75% 0.2 25); font-size:0.8rem; margin:0 0 0.75rem;">{error}</p>
				{/if}

				<button type="submit" disabled={loading} style="width:100%; height:48px; border-radius:14px; border:none; cursor:pointer; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-weight:800; font-size:0.875rem; font-family:inherit; opacity:{loading ? 0.7 : 1};">
					{loading ? 'Enviando...' : 'Enviar enlace'}
				</button>
			</form>
		</div>

		<a href="/login" style="display:block; text-align:center; margin-top:1rem; color:rgba(255,255,255,0.45); font-size:0.8125rem; text-decoration:none;">← Volver al inicio de sesión</a>
	{/if}
</div>
