<script lang="ts">
	import { goto } from '$app/navigation';
	import Aurora from '$lib/components/uro/Aurora.svelte';

	const lastUpdated = '23 de septiembre de 2026';
	const contactEmail = 'mugrelore@gmail.com';
	// Tal como aparecen en la ficha de Play Store: Google exige que esta página
	// referencie el nombre de la app o del desarrollador para poder identificarla.
	const appName = 'Uroboros: calorías y macros';
	const devName = 'Ramón González Vignau';

	// Google Play exige dos caminos para borrar la cuenta: uno dentro de la app y
	// esta página, pensada para quien ya la desinstaló y no puede llegar a Ajustes.
	// Por eso es pública: si exigiera iniciar sesión no serviría para su propósito.
	function goBack() {
		if (typeof history !== 'undefined' && history.length > 1) {
			history.back();
		} else {
			goto('/settings');
		}
	}
</script>

<svelte:head>
	<title>Eliminar tu cuenta — uroboros</title>
	<meta name="description" content="Cómo eliminar tu cuenta de uroboros y todos tus datos." />
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
		<h1 style="font-size:2rem; font-weight:400; font-family:var(--uro-font-serif); letter-spacing:-0.04em; margin:0 0 0.5rem;">Eliminar tu cuenta</h1>
		<div style="font-size:0.8125rem; color:rgba(255,255,255,0.45);">Última actualización: {lastUpdated}</div>
	</div>

	<div style="background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.09); border-radius:16px; padding:1.25rem; margin-bottom:1.5rem; font-size:0.875rem; color:rgba(255,255,255,0.7);">
		Puedes eliminar tu cuenta de <strong style="color:#fff;">{appName}</strong>, la aplicación de <strong style="color:#fff;">{devName}</strong>, y todos tus datos cuando quieras. Es irreversible: no hay forma de recuperarlos después.
	</div>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">1. Desde la app — inmediato</h2>
		<p style="margin:0 0 0.75rem; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Es la vía más rápida y no necesitas escribirnos:
		</p>
		<ol style="margin:0; padding-left:1.25rem; font-size:0.875rem; color:rgba(255,255,255,0.65); display:flex; flex-direction:column; gap:0.375rem;">
			<li>Abre <strong style="color:#fff;">Ajustes</strong>.</li>
			<li>Baja hasta <strong style="color:#fff;">Eliminar cuenta</strong>.</li>
			<li>Confirma escribiendo la palabra que te pide.</li>
		</ol>
		<p style="margin:0.75rem 0 0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			El borrado ocurre en ese momento, no queda ninguna solicitud pendiente.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">2. Si ya has desinstalado la app</h2>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Escríbenos a <a href="mailto:{contactEmail}?subject=Eliminar%20mi%20cuenta" style="color:oklch(85% 0.15 160);">{contactEmail}</a>
			<strong style="color:#fff;"> desde la misma dirección de email con la que te registraste</strong>, con el asunto
			«Eliminar mi cuenta». Es la forma de comprobar que la cuenta es tuya, así que una petición
			desde otra dirección no se puede atender.
		</p>
		<p style="margin:0.75rem 0 0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			No hace falta que expliques nada. Tramitamos la petición en un máximo de <strong style="color:#fff;">30 días</strong> y te confirmamos por email cuando esté hecho.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">3. Qué se borra</h2>
		<p style="margin:0 0 0.75rem; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Todo lo tuyo, sin conservar copia ni versión anonimizada:
		</p>
		<ul style="margin:0; padding-left:1.25rem; font-size:0.875rem; color:rgba(255,255,255,0.65); display:flex; flex-direction:column; gap:0.375rem;">
			<li>Tu cuenta: nombre, email y contraseña.</li>
			<li>Tu diario de comidas completo y tus objetivos.</li>
			<li>Peso, medidas corporales, agua, creatina, suplementos y sesiones de ejercicio.</li>
			<li>Tus recetas, tu despensa y tu lista de la compra.</li>
			<li>Tu foto de perfil, que se borra también del disco del servidor.</li>
			<li>Tus relaciones con otras personas: pareja, amigos y solicitudes pendientes.</li>
		</ul>
		<p style="margin:0.75rem 0 0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Lo único que no desaparece son las comidas que hayas apuntado <strong style="color:#fff;">en el diario de otra persona</strong>: esos registros son suyos y se quedan en su diario, igual que si los hubiera escrito ella. Tus recetas compartidas sí dejan de estar disponibles para quien las veía.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">4. Cuánto tarda en desaparecer del todo</h2>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			En la base de datos el borrado es <strong style="color:#fff;">inmediato</strong>, y tu foto de perfil se elimina del disco en ese mismo momento.
		</p>
		<p style="margin:0.75rem 0 0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Hacemos una <strong style="color:#fff;">copia de seguridad cada noche</strong> y la conservamos 30 días, para poder recuperar el servicio si algo se rompe. Eso significa que durante un máximo de <strong style="color:#fff;">30 días</strong> tus datos pueden seguir existiendo dentro de esas copias, a las que no se accede salvo para restaurar el sistema tras una incidencia. Pasado ese plazo, la copia que te contenía se destruye y no queda ningún rastro tuyo.
		</p>
		<p style="margin:0.75rem 0 0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			No conservamos ninguna otra copia, ni versiones anonimizadas o agregadas de tus datos, ni te enviamos nada después de eliminar la cuenta.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">5. Borrar solo una parte, sin eliminar la cuenta</h2>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			No hace falta eliminar la cuenta para deshacerte de tus datos. Desde la propia app puedes borrar, uno a uno o de golpe, tus comidas del diario, tus pesos y medidas, tus recetas, la despensa y la lista de la compra, tus alergias, las sesiones de ejercicio, los suplementos, tu foto de perfil y tus relaciones con otras personas. El borrado es inmediato en todos los casos.
		</p>
		<p style="margin:0.75rem 0 0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Si lo que te molesta son los avisos, puedes apagarlos todos en <strong style="color:#fff;">Ajustes → Notificaciones</strong> sin perder tu historial. Y si solo quieres dejar de compartir con alguien, en <strong style="color:#fff;">Amigos</strong> puedes revocar el acceso o bloquear a esa persona, y tu cuenta sigue intacta.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">6. Más información</h2>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Qué datos tratamos y por qué está en la <a href="/privacy" style="color:oklch(85% 0.15 160);">Política de Privacidad</a>. Las condiciones de uso, en los <a href="/terms" style="color:oklch(85% 0.15 160);">Términos del Servicio</a>.
		</p>
	</section>

</div>
