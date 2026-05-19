<script lang="ts">
	import { goto } from '$app/navigation';
	import Aurora from '$lib/components/uro/Aurora.svelte';

	const lastUpdated = '19 de mayo de 2026';
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
	<title>Términos del Servicio — uroboros</title>
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
		<h1 style="font-size:2rem; font-weight:400; font-family:'Lora','Georgia',serif; letter-spacing:-0.04em; margin:0 0 0.5rem;">Términos del Servicio</h1>
		<div style="font-size:0.8125rem; color:rgba(255,255,255,0.45);">Última actualización: {lastUpdated}</div>
	</div>

	<div style="background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.09); border-radius:16px; padding:1.25rem; margin-bottom:1.5rem; font-size:0.875rem; color:rgba(255,255,255,0.7);">
		Estos términos regulan el uso de <strong style="color:#fff;">{appName}</strong>. Al crear una cuenta o usar la app, aceptas estas condiciones. Si no estás de acuerdo, no uses el servicio.
	</div>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">1. El servicio</h2>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			{appName} es una aplicación de seguimiento nutricional y bienestar personal. Permite registrar comidas, peso, medidas corporales, ejercicio, inventario doméstico y compartir datos con personas de confianza (pareja, familia). El servicio se ofrece tal cual, sin garantías de disponibilidad continua.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">2. Cuenta de usuario</h2>
		<ul style="margin:0; padding-left:1.25rem; font-size:0.875rem; color:rgba(255,255,255,0.65); display:flex; flex-direction:column; gap:0.375rem;">
			<li>Debes tener al menos <strong style="color:#fff;">16 años</strong> para crear una cuenta.</li>
			<li>Eres responsable de mantener la confidencialidad de tu contraseña.</li>
			<li>Toda la actividad realizada desde tu cuenta es responsabilidad tuya.</li>
			<li>Debes proporcionar información veraz al registrarte (email válido, nombre real opcional).</li>
			<li>Una persona puede tener una sola cuenta. Las cuentas no son transferibles.</li>
		</ul>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">3. Uso aceptable</h2>
		<p style="margin:0 0 0.75rem; font-size:0.875rem; color:rgba(255,255,255,0.65);">Te comprometes a NO:</p>
		<ul style="margin:0; padding-left:1.25rem; font-size:0.875rem; color:rgba(255,255,255,0.65); display:flex; flex-direction:column; gap:0.375rem;">
			<li>Usar la app para fines ilegales o que dañen a terceros.</li>
			<li>Intentar acceder sin autorización a cuentas, servidores o datos de otros usuarios.</li>
			<li>Realizar ingeniería inversa, descompilar o intentar extraer el código fuente.</li>
			<li>Sobrecargar el servicio con peticiones automatizadas (scraping, bots, ataques DDoS).</li>
			<li>Crear productos o recetas con contenido ofensivo, falso o que infrinja derechos de terceros.</li>
			<li>Suplantar a otra persona o registrar cuentas con datos falsos para engañar.</li>
		</ul>
		<p style="margin:0.75rem 0 0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			El incumplimiento puede resultar en la suspensión o eliminación de la cuenta sin previo aviso.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">4. Aviso médico importante</h2>
		<div style="background:oklch(75% 0.18 30 / 0.1); border:1px solid oklch(75% 0.18 30 / 0.25); border-radius:12px; padding:1rem; margin-bottom:0.75rem;">
			<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.85); font-weight:600;">
				⚠️ {appName} <strong>NO es un servicio médico</strong>.
			</p>
		</div>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			La información de macros, calorías, alérgenos y recomendaciones es <strong style="color:#fff;">orientativa</strong> y no sustituye a un profesional sanitario. Antes de iniciar cualquier dieta, programa de ejercicio o cambio nutricional consulta a un médico o nutricionista colegiado. {devName} no se responsabiliza de problemas de salud derivados del uso de la app.
		</p>
		<p style="margin:0.75rem 0 0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			La detección de alérgenos se basa en datos de Open Food Facts y puede ser incompleta o estar desactualizada. <strong style="color:#fff;">Verifica siempre el etiquetado del producto</strong>.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">5. Contenido del usuario</h2>
		<p style="margin:0 0 0.75rem; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Mantienes la propiedad intelectual de los contenidos que crees en {appName} (recetas, comidas registradas, medidas, notas). Al crearlos, nos concedes una licencia no exclusiva y limitada únicamente para:
		</p>
		<ul style="margin:0; padding-left:1.25rem; font-size:0.875rem; color:rgba(255,255,255,0.65); display:flex; flex-direction:column; gap:0.375rem;">
			<li>Almacenar y mostrarte tus datos.</li>
			<li>Compartirlos con los usuarios a los que tú expresamente les concedas acceso.</li>
		</ul>
		<p style="margin:0.75rem 0 0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Nunca usaremos tus datos para entrenar modelos de IA, hacer publicidad, ni los venderemos a terceros.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">6. Productos creados manualmente</h2>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Cuando creas un producto manualmente (botón "Manual" en /add o /inventario), ese producto puede ser visible para otros usuarios del servicio si lo buscan. <strong style="color:#fff;">No incluyas información personal ni contenido protegido por derechos de autor</strong> en los nombres o marcas. Nos reservamos el derecho a eliminar productos que infrinjan estos términos.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">7. Datos de Open Food Facts</h2>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Los datos de productos comerciales (códigos de barras) provienen de <a href="https://world.openfoodfacts.org" style="color:oklch(85% 0.15 160);">Open Food Facts</a>, una base de datos abierta bajo licencia Open Database License (ODbL). {appName} simplemente consulta esta base de datos en tu nombre; no garantizamos la exactitud, completitud ni actualización de la información obtenida.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">8. Disponibilidad del servicio</h2>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Nos esforzamos por mantener {appName} disponible 24/7, pero no garantizamos la ausencia de interrupciones por mantenimiento, fallos técnicos o causas de fuerza mayor. La app es de uso gratuito y se ofrece "tal cual", sin garantía de continuidad indefinida.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">9. Limitación de responsabilidad</h2>
		<p style="margin:0 0 0.75rem; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			En la medida que lo permita la ley aplicable, y salvo en casos de <strong style="color:#fff;">dolo o culpa grave</strong> imputable a {devName}, este no será responsable de:
		</p>
		<ul style="margin:0; padding-left:1.25rem; font-size:0.875rem; color:rgba(255,255,255,0.65); display:flex; flex-direction:column; gap:0.375rem;">
			<li>Daños indirectos, lucro cesante o pérdida de datos derivados del uso de la app.</li>
			<li>Problemas de salud relacionados con dietas seguidas a partir de la información de la app.</li>
			<li>Reacciones alérgicas debidas a información incompleta o errónea de Open Food Facts.</li>
			<li>Acciones de otros usuarios con los que decidas compartir tus datos.</li>
			<li>Interrupciones del servicio o pérdida de datos por fallos técnicos ajenos a nuestra voluntad.</li>
		</ul>
		<p style="margin:0.75rem 0 0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Esta limitación <strong style="color:#fff;">no restringe</strong> los derechos irrenunciables que la legislación de protección de consumidores otorga al usuario, especialmente los previstos en el Real Decreto Legislativo 1/2007 (TRLGDCU). Tampoco se aplica a daños causados por dolo, culpa grave, ni a la responsabilidad por daños personales o a la salud cuando la ley imperativa así lo determine.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">10. Cancelación y eliminación de cuenta</h2>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Puedes eliminar tu cuenta en cualquier momento desde <strong style="color:#fff;">Ajustes → Cuenta → Eliminar cuenta</strong>. La eliminación es <strong style="color:#fff;">permanente e irreversible</strong>: todos tus datos (diario, recetas, peso, medidas, inventario) se borrarán en un plazo máximo de 30 días, salvo aquellos que debamos conservar por obligación legal.
		</p>
		<p style="margin:0.75rem 0 0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Podemos suspender o eliminar tu cuenta si incumples estos términos, sin derecho a reembolso ni compensación.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">11. Propiedad intelectual</h2>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			El código, diseño, logos, marca {appName} y demás elementos del servicio son propiedad de {devName} y están protegidos por las leyes de propiedad intelectual. No se concede ninguna licencia para reproducirlos, modificarlos o distribuirlos sin permiso expreso por escrito.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">12. Modificaciones</h2>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Podemos modificar estos términos para reflejar cambios legales, técnicos o del servicio. Los cambios sustanciales se notificarán por email con al menos 15 días de antelación. Si continúas usando la app tras la notificación, se entiende que aceptas los nuevos términos. Si no estás de acuerdo, puedes eliminar tu cuenta antes de que entren en vigor.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">13. Ley aplicable y jurisdicción</h2>
		<p style="margin:0 0 0.75rem; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Estos términos se rigen por la <strong style="color:#fff;">legislación española</strong>, sin perjuicio de las normas imperativas de protección al consumidor del país de residencia del usuario dentro de la UE.
		</p>
		<p style="margin:0 0 0.75rem; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			<strong style="color:#fff;">Si eres consumidor:</strong> conforme al artículo 90.2 del TRLGDCU (RD Legislativo 1/2007) y al Reglamento (UE) 1215/2012, podrás presentar acciones contra nosotros ante los juzgados de tu domicilio, y nosotros solo podremos demandarte ante los juzgados del tuyo. Esta cláusula no limita ese derecho.
		</p>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			<strong style="color:#fff;">Si no eres consumidor</strong> (uso profesional o empresarial), las partes se someten expresamente a los juzgados y tribunales de Pontevedra (España), con renuncia a cualquier otro fuero que pudiera corresponderles.
		</p>
		<p style="margin:0.75rem 0 0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Como consumidor también dispones de la <strong style="color:#fff;">plataforma de resolución de litigios en línea</strong> de la Comisión Europea: <a href="https://ec.europa.eu/consumers/odr" target="_blank" rel="noopener noreferrer" style="color:oklch(85% 0.15 160);">ec.europa.eu/consumers/odr</a>.
		</p>
	</section>

	<section style="margin-bottom:2rem;">
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">14. Privacidad</h2>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			El tratamiento de tus datos personales se rige por nuestra <a href="/privacy" style="color:oklch(85% 0.15 160);">Política de Privacidad</a>, que forma parte integrante de estos términos.
		</p>
	</section>

	<section>
		<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.75rem;">15. Contacto</h2>
		<p style="margin:0; font-size:0.875rem; color:rgba(255,255,255,0.65);">
			Cualquier pregunta sobre estos términos: <a href="mailto:{contactEmail}" style="color:oklch(85% 0.15 160);">{contactEmail}</a>
		</p>
	</section>

	<div style="margin-top:3rem; padding-top:1.5rem; border-top:1px solid rgba(255,255,255,0.08); text-align:center; font-size:0.75rem; color:rgba(255,255,255,0.3);">
		{appName} · {lastUpdated}
	</div>
</div>
