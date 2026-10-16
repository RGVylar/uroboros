"""Página para apuntarse a la beta (/beta).

La app está en prueba cerrada en Google Play: solo la puede instalar quien esté
en la lista de emails de la prueba, que se mantiene a mano en Play Console. Esta
página es el enlace que se reparte: explica qué hace falta, recoge el email de
la cuenta de Google y, al apuntarse, deja a la vista los pasos que vienen.

Como /unete, la pinta el backend y se monta sin el prefijo /api. Es un
formulario HTML de toda la vida (sin JavaScript): POST a la misma URL y el
servidor responde con la página de "ya estás". Lo único con JavaScript es
turnar las capturas en escritorio; sin él se ven todas en fila.
"""
from html import escape

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Header, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.routers.downloads import ICON_PHONE, _APP_URL, _PLAY_URL, _pick_language, lucide
from app.services import beta_signup
from app.services.telegram_alerts import send_beta_signup_alert

router = APIRouter(tags=["beta"])

# Página de Play para aceptar la prueba cerrada. A quien aún no está en la
# lista le dice que no está disponible, de ahí el aviso que la acompaña.
_OPT_IN_URL = "https://play.google.com/apps/testing/com.uroboros.app"

_HTML = """<!doctype html>
<html lang="{L_LANG}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{L_TITLE}</title>
<meta name="robots" content="noindex">
<meta property="og:type" content="website">
<meta property="og:site_name" content="uroboros">
<meta property="og:title" content="{L_OG_TITLE}">
<meta property="og:description" content="{L_OG_DESC}">
<meta property="og:image" content="{APP}/social-banner.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:url" content="{APP}/beta">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{APP}/logo.png" type="image/png">
<style>
  html { scroll-behavior: smooth; overflow-x: clip; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #06070a; color: #eef1f5;
    font-family: 'Segoe UI', system-ui, sans-serif;
    min-height: 100dvh;
    background-image:
      radial-gradient(60% 45% at 15% 0%, oklch(45% 0.12 170 / 0.22), transparent 60%),
      radial-gradient(50% 40% at 90% 15%, oklch(45% 0.14 300 / 0.16), transparent 60%),
      radial-gradient(70% 50% at 50% 110%, oklch(40% 0.1 220 / 0.18), transparent 60%);
    background-attachment: fixed;
  }
  .wrap { max-width: 460px; margin: 0 auto; padding: 40px 16px 32px; }
  @media (min-width: 900px) { .wrap { padding-top: 72px; } }

  .hero { text-align: center; margin-bottom: 24px; }
  .hero img { width: 72px; height: 72px; filter: drop-shadow(0 12px 32px oklch(70% 0.18 165 / 0.35)); }
  .eyebrow {
    color: oklch(85% 0.17 160); font-weight: 700; font-size: 0.78rem;
    letter-spacing: 0.18em; text-transform: uppercase; margin-top: 14px;
  }
  h1 {
    font-family: Lora, Georgia, serif; font-weight: 500;
    font-size: 2.3rem; letter-spacing: -0.03em; line-height: 1.1; margin-top: 8px;
  }
  .pitch { color: rgba(255,255,255,0.65); font-size: 0.92rem; line-height: 1.55; margin: 14px auto 0; max-width: 380px; }
  .pitch b { color: #eef1f5; }

  .card {
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.09);
    border-radius: 20px; padding: 18px; margin-bottom: 12px;
    backdrop-filter: blur(22px) saturate(1.3); -webkit-backdrop-filter: blur(22px) saturate(1.3);
  }
  .card h2 { font-size: 0.9rem; margin-bottom: 10px; }
  .req { display: flex; gap: 12px; align-items: center; padding: 7px 0; font-size: 0.88rem; }
  .req .ico {
    width: 34px; height: 34px; flex-shrink: 0; border-radius: 11px; font-size: 1rem;
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08);
    display: flex; align-items: center; justify-content: center;
    color: oklch(85% 0.17 160);
  }
  .req .ico svg { width: 18px; height: 18px; }
  .req span { color: rgba(255,255,255,0.75); line-height: 1.4; }
  .req b { color: #eef1f5; }

  label { display: block; font-size: 0.82rem; font-weight: 600; margin: 4px 0 6px; }
  label small { font-weight: 400; color: rgba(255,255,255,0.5); }
  input[type=email], input[type=text] {
    width: 100%; padding: 13px 14px; border-radius: 13px; font: inherit; font-size: 1rem;
    background: rgba(0,0,0,0.35); color: #eef1f5;
    border: 1px solid rgba(255,255,255,0.14); margin-bottom: 12px;
  }
  input:focus { outline: 2px solid oklch(80% 0.17 162 / 0.7); outline-offset: 1px; border-color: transparent; }
  .hint { font-size: 0.75rem; color: rgba(255,255,255,0.5); line-height: 1.45; margin: -6px 0 12px; }
  /* Trampa para bots: un campo que una persona no ve ni rellena. */
  .hp { position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden; }

  button, a.btn {
    display: block; width: 100%; text-align: center; padding: 15px; border-radius: 16px;
    border: 0; cursor: pointer; text-decoration: none; font: inherit;
    background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
    color: #041010; font-weight: 800; font-size: 1.02rem; letter-spacing: -0.01em;
    box-shadow: 0 1px 0 rgba(255,255,255,0.3) inset, 0 14px 34px -8px oklch(75% 0.2 165 / 0.45);
  }
  a.btn.ghost {
    background: rgba(255,255,255,0.07); color: #eef1f5; box-shadow: none;
    border: 1px solid rgba(255,255,255,0.14); font-weight: 700;
  }
  .privacy { font-size: 0.72rem; color: rgba(255,255,255,0.45); line-height: 1.5; margin-top: 12px; }
  .privacy a, .steps a.link { color: oklch(85% 0.17 160); text-decoration: none; }
  .error {
    font-size: 0.82rem; color: #ffb4ab; background: rgba(255,80,60,0.1);
    border: 1px solid rgba(255,80,60,0.3); border-radius: 12px; padding: 10px 12px; margin-bottom: 12px;
  }

  .steps { list-style: none; counter-reset: step; }
  .steps li {
    counter-increment: step; position: relative; padding: 0 0 18px 40px;
    font-size: 0.86rem; color: rgba(255,255,255,0.7); line-height: 1.5;
  }
  .steps li:last-child { padding-bottom: 0; }
  .steps li::before {
    content: counter(step); position: absolute; left: 0; top: 0;
    width: 26px; height: 26px; border-radius: 50%; font-size: 0.78rem; font-weight: 800;
    background: oklch(75% 0.18 165 / 0.15); border: 1px solid oklch(75% 0.18 165 / 0.35);
    color: oklch(88% 0.16 160); display: flex; align-items: center; justify-content: center;
  }
  .steps b { color: #eef1f5; display: block; margin-bottom: 2px; }
  .steps a.btn { margin-top: 10px; padding: 12px; font-size: 0.92rem; }
  .steps .note { display: block; font-size: 0.75rem; color: rgba(255,255,255,0.45); margin-top: 6px; }

  .cta { margin: 20px auto 0; max-width: 300px; }
  .cta a.btn { display: flex; align-items: center; justify-content: center; gap: 8px; }
  .cta a.btn svg { width: 18px; height: 18px; }
  .cta small { display: block; text-align: center; font-size: 0.72rem; color: rgba(255,255,255,0.45); margin-top: 8px; }
  .shots { display: flex; gap: 10px; overflow-x: auto; scroll-snap-type: x mandatory; margin: 0 -16px 20px; padding: 4px 16px 10px; scrollbar-width: none; }
  .shots::-webkit-scrollbar { display: none; }
  .shots { -webkit-mask-image: linear-gradient(90deg, transparent, #000 16px, #000 calc(100% - 16px), transparent); mask-image: linear-gradient(90deg, transparent, #000 16px, #000 calc(100% - 16px), transparent); }
  .shots figure { flex: 0 0 42%; scroll-snap-align: center; }
  .shots img { width: 100%; height: auto; display: block; border-radius: 18px; border: 1px solid rgba(255,255,255,0.12); box-shadow: 0 18px 40px -16px rgba(0,0,0,0.8); }
  .shots figcaption { font-size: 0.7rem; color: rgba(255,255,255,0.5); text-align: center; margin-top: 6px; }
  @media (min-width: 700px) {
    .shots { margin-left: calc(50% - 50vw); margin-right: calc(50% - 50vw); padding: 4px 24px 10px; justify-content: safe center; gap: 14px; }
    .shots > figure { flex: 0 0 170px; }
  }
  .feat { display: flex; gap: 12px; padding: 9px 0; }
  .feat + .feat { border-top: 1px solid rgba(255,255,255,0.06); }
  .feat .ico { width: 34px; height: 34px; flex-shrink: 0; border-radius: 11px; background: oklch(75% 0.18 165 / 0.12); border: 1px solid oklch(75% 0.18 165 / 0.25); display: flex; align-items: center; justify-content: center; color: oklch(85% 0.17 160); }
  .feat .ico svg { width: 18px; height: 18px; }
  .feat b { display: block; font-size: 0.9rem; margin-bottom: 2px; }
  .feat span { font-size: 0.82rem; color: rgba(255,255,255,0.65); line-height: 1.45; }
  .section-label { font-size: 0.7rem; letter-spacing: 0.14em; text-transform: uppercase; color: rgba(255,255,255,0.45); font-weight: 700; margin: 4px 4px 10px; }


  /* Escritorio: tres columnas, con el formulario en el centro. */
  .shot-dots { display: none; }
  @media (min-width: 1000px) {
    .wrap.layout {
      max-width: 1180px; padding-top: 56px;
      display: grid; grid-template-columns: 1fr 420px 1fr; column-gap: 40px;
      grid-template-areas: "feat hero shots" "feat form shots" "feat req shots" "foot foot foot";
      grid-template-rows: auto auto 1fr auto; align-items: start;
    }
    .a-hero { grid-area: hero; } .a-form { grid-area: form; } .a-req { grid-area: req; }
    .a-feat { grid-area: feat; padding-top: 150px; } .a-shots { grid-area: shots; padding-top: 110px; }
    footer { grid-area: foot; }
    .cta { display: none; }
    .a-hero .hero { margin-bottom: 20px; }
    /* Un solo móvil que va pasando las capturas. */
    .shots, .shots { margin: 0 auto; padding: 0; overflow: visible; display: grid; justify-content: center; -webkit-mask-image: none; mask-image: none; }
    .shots > figure { grid-area: 1 / 1; width: 270px; opacity: 0; transform: translateY(8px) scale(0.98); transition: opacity 0.6s, transform 0.6s; }
    .shots > figure.on { opacity: 1; transform: none; }
    .shots img { border-radius: 26px; box-shadow: 0 30px 70px -20px rgba(0,0,0,0.9), 0 0 0 1px rgba(255,255,255,0.06); }
    .shots figcaption { font-size: 0.82rem; margin-top: 12px; }
    .shot-dots { display: flex; justify-content: center; gap: 6px; margin-top: 10px; }
    .shot-dots button { all: unset; width: 7px; height: 7px; border-radius: 50%; background: rgba(255,255,255,0.2); cursor: pointer; transition: background 0.3s, width 0.3s; }
    .shot-dots button.on { background: oklch(85% 0.17 160); width: 18px; border-radius: 4px; }
  }

  footer { text-align: center; margin-top: 26px; font-size: 0.7rem; color: rgba(255,255,255,0.3); }
  footer a { color: rgba(255,255,255,0.45); text-decoration: none; margin: 0 6px; }
</style>
</head>
<body>
<div class="wrap{WRAP_CLS}">
  <section class="a-hero">
  <div class="hero">
    <img src="{APP}/logo.png" alt="uroboros" width="72" height="72">
    <div class="eyebrow">{L_EYEBROW}</div>
    <h1>{HEADLINE}</h1>
    <p class="pitch">{PITCH}</p>
    {CTA}
  </div>
  </section>
  {BODY}
  <footer>
    uroboros · <a href="{APP}/privacy">{L_PRIVACY}</a>·<a href="{APP}/terms">{L_TERMS}</a>
  </footer>
</div>
{SCRIPT}
</body>
</html>"""

_FORM = """
  <section class="a-shots">
  <div class="shots">
    <figure><img src="{APP}/screens/{L_LANG}/home.webp" alt="{L_SHOT1}" width="540" height="960" loading="lazy"><figcaption>{L_SHOT1}</figcaption></figure>
    <figure><img src="{APP}/screens/{L_LANG}/add.webp" alt="{L_SHOT2}" width="540" height="960" loading="lazy"><figcaption>{L_SHOT2}</figcaption></figure>
    <figure><img src="{APP}/screens/{L_LANG}/recipes.webp" alt="{L_SHOT3}" width="540" height="960" loading="lazy"><figcaption>{L_SHOT3}</figcaption></figure>
    <figure><img src="{APP}/screens/{L_LANG}/inventory.webp" alt="{L_SHOT4}" width="540" height="960" loading="lazy"><figcaption>{L_SHOT4}</figcaption></figure>
    <figure><img src="{APP}/screens/{L_LANG}/weight.webp" alt="{L_SHOT5}" width="540" height="960" loading="lazy"><figcaption>{L_SHOT5}</figcaption></figure>
  </div>
  </section>

  <section class="a-feat">
  <div class="section-label">{L_FEAT_T}</div>
  <div class="card">
    <div class="feat"><div class="ico">{ICON_F1}</div><div><b>{L_F1_T}</b><span>{L_F1_D}</span></div></div>
    <div class="feat"><div class="ico">{ICON_F2}</div><div><b>{L_F2_T}</b><span>{L_F2_D}</span></div></div>
    <div class="feat"><div class="ico">{ICON_F3}</div><div><b>{L_F3_T}</b><span>{L_F3_D}</span></div></div>
    <div class="feat"><div class="ico">{ICON_F4}</div><div><b>{L_F4_T}</b><span>{L_F4_D}</span></div></div>
  </div>
  </section>

  <section class="a-req">
  <div class="section-label">{L_TRY_T}</div>
  <div class="card">
    <h2>{L_REQ_T}</h2>
    <div class="req"><div class="ico">{ICON_PHONE}</div><span>{L_REQ1}</span></div>
    <div class="req"><div class="ico">{ICON_CALENDAR}</div><span>{L_REQ2}</span></div>
    <div class="req"><div class="ico">{ICON_CHECK}</div><span>{L_REQ3}</span></div>
  </div>
  </section>

  <section class="a-form">
  <form id="apuntarse" class="card" method="post" action="/beta?lang={L_LANG}">
    {ERROR}
    <label for="email">{L_EMAIL}</label>
    <input id="email" name="email" type="email" required maxlength="255"
           autocomplete="email" inputmode="email" value="{EMAIL}">
    <p class="hint">{L_EMAIL_HINT}</p>
    <label for="name">{L_NAME} <small>{L_OPTIONAL}</small></label>
    <input id="name" name="name" type="text" maxlength="80" autocomplete="given-name" value="{NAME}">
    <div class="hp" aria-hidden="true">
      <label for="website">Website</label>
      <input id="website" name="website" type="text" tabindex="-1" autocomplete="off">
    </div>
    <button type="submit">{L_SUBMIT}</button>
    <p class="privacy">{L_CONSENT}</p>
  </form>
  </section>
"""

_CTA = """<div class="cta"><a class="btn" href="#apuntarse">{L_SUBMIT} {ICON_DOWN}</a><small>{L_CTA_NOTE}</small></div>"""

# Mejora progresiva: sin JavaScript las capturas se ven todas en fila.
_SCRIPT = """<script>
  // Solo en escritorio: las capturas se van turnando en un único móvil.
  (() => {
    const mq = matchMedia('(min-width: 1000px)');
    const figs = [...document.querySelectorAll('.shots > figure')];
    const dots = document.createElement('div'); dots.className = 'shot-dots';
    figs.forEach((_, i) => { const b = document.createElement('button'); b.setAttribute('aria-label', String(i + 1)); b.onclick = () => { show(i); restart(); }; dots.append(b); });
    document.querySelector('.a-shots').append(dots);
    let cur = 0, timer;
    function show(i) { cur = i; figs.forEach((f, j) => f.classList.toggle('on', j === i)); [...dots.children].forEach((d, j) => d.classList.toggle('on', j === i)); }
    function restart() { clearInterval(timer); if (mq.matches) timer = setInterval(() => show((cur + 1) % figs.length), 3200); }
    show(0); restart(); mq.addEventListener('change', restart);
  })();
</script>"""

_DONE = """
  <div class="card">
    <ol class="steps">
      <li><b>{L_S1_T}</b>{L_S1_D}</li>
      <li><b>{L_S2_T}</b>{L_S2_D}
        <a class="btn" href="{OPT_IN}">{L_S2_BTN}</a>
        <span class="note">{L_S2_NOTE}</span></li>
      <li><b>{L_S3_T}</b>{L_S3_D}
        <a class="btn ghost" href="{PLAY}&amp;hl={L_HL}">{L_S3_BTN}</a></li>
    </ol>
  </div>
"""

# Primera persona, como la historia de Instagram con la que se buscaban
# testers: quien pide el favor es una persona, no una empresa.
_COPY: dict[str, dict[str, str]] = {
    "es": {
        "L_LANG": "es",
        "L_HL": "es",
        "L_TITLE": "Prueba uroboros antes que nadie",
        "L_OG_TITLE": "¿Me ayudas a probar uroboros?",
        "L_OG_DESC": "Busco personas con Android para probar mi app de calorías en pareja antes de que salga en Google Play.",
        "L_EYEBROW": "Busco testers",
        "L_HEADLINE": "Pruébala antes que nadie",
        "L_PITCH": "Es mi app para llevar las calorías y los macros <b>en pareja</b>: apuntas una comida una vez y cuenta para los dos. Antes de que salga en Google Play necesito <b>12 personas</b> que la prueben <b>14 días</b>. ¿Te animas?",
        "L_CTA_NOTE": "Te apuntas en un minuto",
        "L_FEAT_T": "Qué puedes hacer",
        "L_TRY_T": "Para probarla",
        "L_SHOT1": "Tu día de un vistazo",
        "L_SHOT2": "Apunta en segundos",
        "L_SHOT3": "Recetas y ollas",
        "L_SHOT4": "Despensa compartida",
        "L_SHOT5": "Tu peso y su tendencia",
        "L_F1_T": "Pensada para dos",
        "L_F1_D": "Apuntas la comida una vez y cuenta para los dos, cada uno con sus gramos y sus objetivos. Y ves el día de tu pareja junto al tuyo.",
        "L_F2_T": "Apuntar es rápido",
        "L_F2_D": "Escanea el código de barras o búscalo, con la carta de las cadenas de comida rápida incluida. Con una foto del ticket se llena la despensa.",
        "L_F3_T": "Cocina una vez, come varios días",
        "L_F3_D": "Guarda tus recetas y haz ollas para toda la semana: la app reparte las raciones.",
        "L_F4_T": "Con un poco de pique",
        "L_F4_D": "Duelos semanales con tu pareja, medallas y ranking con tus amigos para no dejarlo.",
        "L_REQ_T": "Qué hace falta",
        "L_REQ1": "Tener un móvil <b>Android</b>",
        "L_REQ2": "Dejarla instalada <b>14 días</b> seguidos",
        "L_REQ3": "Ya está: no hace falta usarla a diario (aunque si me cuentas qué tal, mejor)",
        "L_EMAIL": "Email de tu cuenta de Google",
        "L_EMAIL_HINT": "El de la cuenta con la que entras en Google Play en el móvil. Si pones otro, Play no te dejará instalarla.",
        "L_NAME": "Tu nombre",
        "L_OPTIONAL": "(opcional)",
        "L_SUBMIT": "Quiero probarla",
        "L_CONSENT": "Uso tu email solo para añadirte a la prueba en Google Play y avisarte de que ya puedes instalarla. Lo borro cuando acabe la beta. Más en <a href=\"{APP}/privacy\">privacidad</a>.",
        "L_ERR_EMAIL": "Ese email no parece válido. Revísalo y vuelve a probar.",
        "L_DONE_EYEBROW": "Estás dentro",
        "L_DONE_HEADLINE": "¡Gracias por apuntarte!",
        "L_DONE_PITCH": "Te he guardado como <b>{EMAIL}</b>. Esto es lo que viene:",
        "L_S1_T": "Te añado a la lista",
        "L_S1_D": "Lo hago a mano, normalmente en el mismo día, y te aviso por email.",
        "L_S2_T": "Acepta la prueba",
        "L_S2_D": "Abre este enlace desde el móvil y pulsa «Convertirse en tester».",
        "L_S2_BTN": "Aceptar la prueba en Google Play",
        "L_S2_NOTE": "Si te dice que no está disponible, es que aún no te he añadido: vuelve a probar más tarde.",
        "L_S3_T": "Instálala",
        "L_S3_D": "Descárgala desde Google Play y déjala instalada 14 días.",
        "L_S3_BTN": "Abrir en Google Play",
        "L_PRIVACY": "privacidad",
        "L_TERMS": "términos",
    },
    "en": {
        "L_LANG": "en",
        "L_HL": "en",
        "L_TITLE": "Try uroboros before anyone else",
        "L_OG_TITLE": "Will you help me test uroboros?",
        "L_OG_DESC": "I'm looking for Android users to test my couples' calorie app before it comes out on Google Play.",
        "L_EYEBROW": "Looking for testers",
        "L_HEADLINE": "Try it before anyone else",
        "L_PITCH": "It's my app for tracking calories and macros <b>as a couple</b>: log a meal once and it counts for both of you. Before it comes out on Google Play I need <b>12 people</b> to try it for <b>14 days</b>. Are you in?",
        "L_CTA_NOTE": "Signing up takes a minute",
        "L_FEAT_T": "What you can do",
        "L_TRY_T": "To try it",
        "L_SHOT1": "Your day at a glance",
        "L_SHOT2": "Log food in seconds",
        "L_SHOT3": "Recipes and batch cooking",
        "L_SHOT4": "Shared pantry",
        "L_SHOT5": "Your weight and its trend",
        "L_F1_T": "Made for two",
        "L_F1_D": "Log a meal once and it counts for both of you, each with your own grams and goals. And see your partner's day next to yours.",
        "L_F2_T": "Logging is quick",
        "L_F2_D": "Scan the barcode or search for it, fast food chain menus included. A photo of your receipt fills up the pantry.",
        "L_F3_T": "Cook once, eat for days",
        "L_F3_D": "Save your recipes and batch cook for the whole week: the app splits the servings.",
        "L_F4_T": "A bit of friendly rivalry",
        "L_F4_D": "Weekly duels with your partner, plus medals and a ranking with your friends to keep you going.",
        "L_REQ_T": "What it takes",
        "L_REQ1": "An <b>Android</b> phone",
        "L_REQ2": "Keep it installed for <b>14 days</b> in a row",
        "L_REQ3": "That's it: no need to use it every day (though I'd love to hear what you think)",
        "L_EMAIL": "Your Google account email",
        "L_EMAIL_HINT": "The account you use for Google Play on your phone. With a different one, Play won't let you install it.",
        "L_NAME": "Your name",
        "L_OPTIONAL": "(optional)",
        "L_SUBMIT": "I want to try it",
        "L_CONSENT": "I only use your email to add you to the test on Google Play and let you know when you can install it. I'll delete it when the beta ends. More in the <a href=\"{APP}/privacy\">privacy policy</a>.",
        "L_ERR_EMAIL": "That email doesn't look right. Check it and try again.",
        "L_DONE_EYEBROW": "You're in",
        "L_DONE_HEADLINE": "Thanks for signing up!",
        "L_DONE_PITCH": "I've saved you as <b>{EMAIL}</b>. Here's what happens next:",
        "L_S1_T": "I add you to the list",
        "L_S1_D": "I do it by hand, usually the same day, and I'll let you know by email.",
        "L_S2_T": "Accept the test",
        "L_S2_D": "Open this link on your phone and tap “Become a tester”.",
        "L_S2_BTN": "Accept the test on Google Play",
        "L_S2_NOTE": "If it says it's not available, I haven't added you yet: try again later.",
        "L_S3_T": "Install it",
        "L_S3_D": "Download it from Google Play and keep it installed for 14 days.",
        "L_S3_BTN": "Open in Google Play",
        "L_PRIVACY": "privacy",
        "L_TERMS": "terms",
    },
    "pt": {
        "L_LANG": "pt",
        "L_HL": "pt-PT",
        "L_TITLE": "Experimenta o uroboros antes de toda a gente",
        "L_OG_TITLE": "Ajudas-me a testar o uroboros?",
        "L_OG_DESC": "Procuro pessoas com Android para testar a minha app de calorias a dois antes de sair no Google Play.",
        "L_EYEBROW": "Procuro testers",
        "L_HEADLINE": "Experimenta-a antes de toda a gente",
        "L_PITCH": "É a minha app para gerir calorias e macros <b>a dois</b>: registas uma refeição uma vez e conta para ambos. Antes de sair no Google Play preciso de <b>12 pessoas</b> que a testem durante <b>14 dias</b>. Alinhas?",
        "L_CTA_NOTE": "Inscreves-te num minuto",
        "L_FEAT_T": "O que podes fazer",
        "L_TRY_T": "Para a testar",
        "L_SHOT1": "O teu dia num relance",
        "L_SHOT2": "Regista em segundos",
        "L_SHOT3": "Receitas e panelas",
        "L_SHOT4": "Despensa partilhada",
        "L_SHOT5": "O teu peso e a tendência",
        "L_F1_T": "Pensada para dois",
        "L_F1_D": "Registas a refeição uma vez e conta para ambos, cada um com as suas gramas e objetivos. E vês o dia do teu par ao lado do teu.",
        "L_F2_T": "Registar é rápido",
        "L_F2_D": "Lê o código de barras ou pesquisa, com os menus das cadeias de fast food incluídos. Com uma foto do talão enche-se a despensa.",
        "L_F3_T": "Cozinha uma vez, come vários dias",
        "L_F3_D": "Guarda as tuas receitas e faz panelas para a semana inteira: a app divide as doses.",
        "L_F4_T": "Com um pouco de picardia",
        "L_F4_D": "Duelos semanais com o teu par, medalhas e ranking com os teus amigos para não desistires.",
        "L_REQ_T": "O que é preciso",
        "L_REQ1": "Ter um telemóvel <b>Android</b>",
        "L_REQ2": "Mantê-la instalada <b>14 dias</b> seguidos",
        "L_REQ3": "Mais nada: não é preciso usá-la todos os dias (mas se me disseres o que achas, melhor)",
        "L_EMAIL": "Email da tua conta Google",
        "L_EMAIL_HINT": "O da conta com que entras no Google Play no telemóvel. Se puseres outro, o Play não te deixa instalá-la.",
        "L_NAME": "O teu nome",
        "L_OPTIONAL": "(opcional)",
        "L_SUBMIT": "Quero experimentar",
        "L_CONSENT": "Uso o teu email só para te adicionar ao teste no Google Play e avisar-te de que já a podes instalar. Apago-o quando a beta acabar. Mais na <a href=\"{APP}/privacy\">privacidade</a>.",
        "L_ERR_EMAIL": "Esse email não parece válido. Revê-o e tenta outra vez.",
        "L_DONE_EYEBROW": "Estás dentro",
        "L_DONE_HEADLINE": "Obrigado por te inscreveres!",
        "L_DONE_PITCH": "Guardei-te como <b>{EMAIL}</b>. É isto que vem a seguir:",
        "L_S1_T": "Adiciono-te à lista",
        "L_S1_D": "Faço-o à mão, normalmente no mesmo dia, e aviso-te por email.",
        "L_S2_T": "Aceita o teste",
        "L_S2_D": "Abre este link no telemóvel e toca em «Tornar-se tester».",
        "L_S2_BTN": "Aceitar o teste no Google Play",
        "L_S2_NOTE": "Se disser que não está disponível, ainda não te adicionei: tenta mais tarde.",
        "L_S3_T": "Instala-a",
        "L_S3_D": "Descarrega-a do Google Play e mantém-na instalada 14 dias.",
        "L_S3_BTN": "Abrir no Google Play",
        "L_PRIVACY": "privacidade",
        "L_TERMS": "termos",
    },
}


_ICONS = {
    "ICON_PHONE": ICON_PHONE,
    "ICON_CALENDAR": lucide(
        '<path d="M8 2v3"/><path d="M16 2v3"/><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/>'
    ),
    "ICON_CHECK": lucide('<path d="M20 6 9 17l-5-5"/>'),
    "ICON_DOWN": lucide('<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/>'),
    "ICON_F1": lucide(
        '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
        '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
    ),
    "ICON_F2": lucide(
        '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/>'
        '<path d="M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M8 7v10"/><path d="M12 7v10"/><path d="M17 7v10"/>'
    ),
    "ICON_F3": lucide(
        '<path d="M2 12h20"/><path d="M20 12v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8"/><path d="m4 8 16-4"/>'
        '<path d="m8.86 6.78-.45-1.81a2 2 0 0 1 1.45-2.43l1.94-.48a2 2 0 0 1 2.43 1.46l.45 1.8"/>'
    ),
    "ICON_F4": lucide(
        '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/>'
        '<path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/>'
        '<path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>'
    ),
}


def _fill(template: str, copy: dict[str, str]) -> str:
    for key, value in copy.items():
        template = template.replace("{" + key + "}", value)
    return template


def _render(lang: str, *, done_email: str | None = None, error: str = "", email: str = "", name: str = "") -> str:
    copy = _COPY[lang]
    if done_email is not None:
        body = _DONE.replace("{OPT_IN}", _OPT_IN_URL)
        headline, eyebrow = copy["L_DONE_HEADLINE"], copy["L_DONE_EYEBROW"]
        pitch = copy["L_DONE_PITCH"].replace("{EMAIL}", escape(done_email))
        wrap_cls, cta, script = "", "", ""
    else:
        body = (
            _FORM.replace("{ERROR}", f'<p class="error">{error}</p>' if error else "")
            .replace("{EMAIL}", escape(email))
            .replace("{NAME}", escape(name))
        )
        headline, eyebrow, pitch = copy["L_HEADLINE"], copy["L_EYEBROW"], copy["L_PITCH"]
        wrap_cls, cta, script = " layout", _CTA, _SCRIPT
    html = (
        _HTML.replace("{BODY}", body)
        .replace("{WRAP_CLS}", wrap_cls)
        .replace("{CTA}", cta)
        .replace("{SCRIPT}", script)
        .replace("{HEADLINE}", headline)
        .replace("{PITCH}", pitch)
        .replace("{L_EYEBROW}", eyebrow)
    )
    return _fill(_fill(html, copy), _ICONS).replace("{APP}", _APP_URL).replace("{PLAY}", _PLAY_URL)


def _lang(accept_language: str | None, lang: str | None) -> str:
    resolved = _pick_language(accept_language, lang)
    return resolved if resolved in _COPY else "es"


@router.get("/beta", response_class=HTMLResponse)
def beta_page(
    accept_language: str | None = Header(default=None),
    lang: str | None = None,
) -> HTMLResponse:
    """El enlace que se reparte. Cacheable como /unete (ver allí el porqué
    de ?lang=); la respuesta del POST, en cambio, es de cada cual."""
    return HTMLResponse(
        _render(_lang(accept_language, lang)),
        headers={"Cache-Control": "public, max-age=3600", "Vary": "Accept-Language"},
    )


@router.post("/beta", response_class=HTMLResponse)
@limiter.limit("10/hour")
def beta_signup_submit(
    request: Request,
    background: BackgroundTasks,
    email: str = Form("", max_length=320),
    name: str = Form("", max_length=200),
    website: str = Form("", max_length=200),
    accept_language: str | None = Header(default=None),
    lang: str | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    resolved = _lang(accept_language, lang)
    no_store = {"Cache-Control": "no-store"}

    # Un bot que rellena el campo trampa ve lo mismo que una persona, para que
    # no tenga motivo para cambiar de táctica; simplemente no se guarda nada.
    if website:
        return HTMLResponse(_render(resolved, done_email=email.strip()), headers=no_store)

    normalized = beta_signup.normalize_email(email)
    if normalized is None:
        return HTMLResponse(
            _render(resolved, error=_COPY[resolved]["L_ERR_EMAIL"], email=email.strip(), name=name.strip()),
            status_code=422,
            headers=no_store,
        )

    if beta_signup.register(db, normalized, name, resolved):
        background.add_task(send_beta_signup_alert, normalized, beta_signup.pending_count(db))

    return HTMLResponse(_render(resolved, done_email=normalized), headers=no_store)
