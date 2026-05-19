<script lang="ts">
	import { goto } from '$app/navigation';
	import Aurora from '$lib/components/uro/Aurora.svelte';

	const lastUpdated = '1 de mayo de 2026';
	const contactEmail = 'mugrelore@gmail.com';
	const appName = 'uroboros';
	const devName = 'Ramón González Vignau';

	function goBack() {
		if (typeof history !== 'undefined' && history.length > 1) {
			history.back();
		} else {
			goto('/settings');
		}
	}
</script>

<svelte:head>
	<title>Política de Privacidad — uroboros</title>
</svelte:head>

<Aurora />

<div style="max-width:680px; margin:0 auto; padding:1rem 1.25rem 6rem; color:#fff; font-family:inherit; line-height:1.7; position:relative; z-index:1;">

	<!-- Back button -->
	<button
		onclick={goBack}
		style="display:inline-flex; align-items:center; gap:0.5rem; padding:0.5rem 0.875rem; border-radius:99px; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); color:rgba(255,255,255,0.85); font-family:inherit; font-size:0.8125rem; cursor:pointer; margin-bottom:1.25rem;"
	>
		← Atrás
	</button>

	<div style="margin-bottom:2rem;">
		<div style="font-size:0.75rem; color:rgba(255,255,255,0.4); text-transform:uppercase; letter-spacing:0.1em; margin-bottom:0.5rem;">Legal</div>
		<h1 style="font-size:2rem; font-weight:400; font-family:'Lora','Georgia',serif; letter-spacing:-0.04em; margin:0 0 0.5rem;">Política de Privacidad</h1>
		<div style="font-size:0.8125rem; color:rgba(255,255,255,0.45);">Última actualización: {lastUpdated}</div>
	</div>

	<div style="background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.09); border-radius:16px; padding:1.25rem; margin-bottom:1.5rem; font-size:0.875rem; color:rgba(255,255,255,0.7);">
		Esta política describe cómo <strong style="color:#fff;">{appName}</strong> recoge, usa y protege tu información personal. Al usar la app, aceptas estas condiciones.
	</div>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">1. Responsable del tratamiento</h2>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			<strong style="color:#fff;">{devName}</strong><br>
			Contacto: <a href="mailto:{contactEmail}" style="color:oklch(85% 0.15 160);">{contactEmail}</a>
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">2. Datos que recogemos</h2>
		<p style="margin:0 0 0.75rem; font-size:0.875rem; color:rgba(255,255,255,0.65);">Recogemos únicamente los datos que tú introduces voluntariamente:</p>
		<ul style="margin:0; padding-left:1.25rem; font-size:0.875rem; color:rgba(255,255,255,0.65); display:flex; flex-direction:column; gap:0.375rem;">
			<li><strong style="color:#fff;">Cuenta:</strong> nombre y dirección de email</li>
			<li><strong style="color:#fff;">Diario alimenticio:</strong> alimentos consumidos, cantidades y calorías</li>
			<li><strong style="color:#fff;">Métricas corporales:</strong> peso, medidas corporales (opcionales)</li>
			<li><strong style="color:#fff;">Actividad física:</strong> sesiones de ejercicio registradas (opcional)</li>
			<li><strong style="color:#fff;">Inventario:</strong> productos y cantidades en tu despensa (opcional)</li>
			<li><strong style="color:#fff;">Recetas:</strong> recetas personales que crees en la app (opcional)</li>
		</ul>
		<p style="margin:0.75rem 0 0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			No recogemos datos de localización, contactos, ni ningún otro dato del dispositivo.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">3. Para qué usamos tus datos</h2>
		<ul style="margin:0; padding-left:1.25rem; font-size:0.875rem; color:rgba(255,255,255,0.65); display:flex; flex-direction:column; gap:0.375rem;">
			<li>Proporcionarte el servicio de seguimiento nutricional</li>
			<li>Permitirte compartir datos con tu pareja o amigos (solo si tú lo activas)</li>
			<li>Enviarte emails transaccionales (recuperación de contraseña)</li>
			<li>Mejorar la experiencia de la app</li>
		</ul>
		<p style="margin:0.75rem 0 0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			No usamos tus datos para publicidad, ni los vendemos ni compartimos con terceros.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">4. Compartir datos con otros usuarios</h2>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			{appName} permite compartir tu diario e inventario con otros usuarios (pareja, amigos). Esta funcionalidad es <strong style="color:#fff;">completamente opcional</strong> y requiere que tú la actives explícitamente. Puedes revocar el acceso en cualquier momento desde la sección "Amigos" de la app.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">5. Dónde se almacenan tus datos</h2>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Tus datos se almacenan en servidores ubicados en la Unión Europea. No se transfieren a terceros países. El servicio de email transaccional utilizado es <strong style="color:#fff;">Resend</strong> (resend.com), que actúa como encargado del tratamiento únicamente para el envío de emails del sistema.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">6. Durante cuánto tiempo guardamos tus datos</h2>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Tus datos se conservan mientras tengas una cuenta activa. Si eliminas tu cuenta, todos tus datos se borran permanentemente en un plazo máximo de 30 días.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">7. Tus derechos (RGPD)</h2>
		<p style="margin:0 0 0.75rem; font-size:0.875rem; color:rgba(255,255,255,0.65);">Como usuario tienes derecho a:</p>
		<ul style="margin:0; padding-left:1.25rem; font-size:0.875rem; color:rgba(255,255,255,0.65); display:flex; flex-direction:column; gap:0.375rem;">
			<li><strong style="color:#fff;">Acceso:</strong> solicitar una copia de todos tus datos</li>
			<li><strong style="color:#fff;">Rectificación:</strong> corregir datos incorrectos</li>
			<li><strong style="color:#fff;">Supresión:</strong> eliminar tu cuenta y todos tus datos</li>
			<li><strong style="color:#fff;">Portabilidad:</strong> exportar tus datos en formato CSV desde la app</li>
			<li><strong style="color:#fff;">Oposición:</strong> oponerte a cualquier tratamiento</li>
		</ul>
		<p style="margin:0.75rem 0 0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Para ejercer cualquiera de estos derechos, escríbenos a <a href="mailto:{contactEmail}" style="color:oklch(85% 0.15 160);">{contactEmail}</a>.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">8. Seguridad</h2>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Las contraseñas se almacenan cifradas con bcrypt. Toda la comunicación entre la app y el servidor se realiza mediante HTTPS. No almacenamos contraseñas en texto plano.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">9. Menores de edad</h2>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			{appName} no está dirigida a menores de 16 años. Si eres menor de 16 años, no uses la app sin el consentimiento de tus padres o tutores.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">10. Cambios en esta política</h2>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Podemos actualizar esta política ocasionalmente. Te notificaremos de cambios significativos por email. La fecha de última actualización siempre aparece al inicio de esta página.
		</p>
	</section>

	<section>
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">11. Contacto</h2>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Cualquier pregunta sobre privacidad: <a href="mailto:{contactEmail}" style="color:oklch(85% 0.15 160);">{contactEmail}</a>
		</p>
	</section>

	<div style="margin-top:3rem; padding-top:1.5rem; border-top:1px solid rgba(255,255,255,0.08); text-align:center; font-size:0.75rem; color:rgba(255,255,255,0.3);">
		{appName} · {lastUpdated}
	</div>
</div>
