"""Invite landing (/unete) and the old APK download link.

La app se distribuye por Google Play. Antes se repartía un APK de debug desde
Nextcloud y `/api/download/latest-apk` resolvía el más reciente; ese endpoint
sigue existiendo porque lo llevan dentro los APK sideload antiguos (su botón
"Actualizar") y los enlaces ya compartidos, pero ahora manda a la ficha de Play.
"""
from fastapi import APIRouter, Header, Request
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter(prefix="/download", tags=["download"])

# Invite landing lives outside the /download prefix so the shared URL is short.
# Se monta sin el prefijo /api: es una página, no una API.
landing_router = APIRouter(tags=["download"])

# Ruta antigua (/api/unete), viva solo para redirigir los enlaces ya compartidos.
legacy_landing_router = APIRouter(tags=["download"])

# El `id` es el applicationId, igual que `UPDATE_URL` en frontend/src/lib/changelog.ts.
_PLAY_URL = "https://play.google.com/store/apps/details?id=com.uroboros.app"


@router.get("/latest-apk")
def latest_apk() -> RedirectResponse:
    """Antes bajaba el último APK de Nextcloud; ahora lleva a Google Play.

    Quien llega aquí suele tener un APK sideload antiguo (firmado con la clave
    de debug): Play no puede actualizarlo encima, tendrá que desinstalarlo e
    instalar la de la tienda. La landing /unete lo explica.
    """
    return RedirectResponse(_PLAY_URL, status_code=302)


_APP_URL = "https://comida.mugrelore.com"

# The invite message links here instead of straight at Google Play: messaging
# apps' crawlers need an HTML page with Open Graph tags to render a preview card,
# and the page can explain what the app is and how to start before sending
# Android users to the store (and iPhone users to the web app). It's also where
# a future invite deep-link would plug in (open the add-friend modal in the app).
_LANDING_HTML = """<!doctype html>
<html lang="{L_LANG}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{L_TITLE}</title>
<meta property="og:type" content="website">
<meta property="og:site_name" content="uroboros">
<meta property="og:title" content="{L_OG_TITLE}">
<meta property="og:description" content="{L_OG_DESC}">
<meta property="og:image" content="{APP}/social-banner.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:url" content="{L_CANONICAL}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{APP}/logo.png" type="image/png">
<style>
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
  .wrap { max-width: 460px; margin: 0 auto; padding: 40px 20px 32px; }

  /* En escritorio la columna de 460px deja demasiado aire a los lados: pasamos
     a un split a pantalla completa — izquierda el gancho (marca + ventajas),
     derecha un panel con todo lo de descargar. */
  @media (min-width: 900px) {
    .wrap { max-width: none; padding: 0; }
    .cols {
      display: grid; grid-template-columns: 1.05fr 1fr;
      min-height: 100dvh; align-items: stretch;
    }
    .col {
      padding: 60px 48px;
      display: flex; flex-direction: column; justify-content: center; align-items: center;
    }
    /* El panel de descarga se separa del fondo con un velo y un filo. */
    .col + .col {
      background: rgba(255,255,255,0.035);
      border-left: 1px solid rgba(255,255,255,0.09);
    }
    .col > * { width: 100%; max-width: 460px; }
    .col + .col > * { max-width: 400px; margin-left: auto; margin-right: auto; }
  }

  /* Hero */
  .hero { text-align: center; margin-bottom: 26px; }
  .hero img { width: 96px; height: 96px; filter: drop-shadow(0 12px 32px oklch(70% 0.18 165 / 0.35)); }
  h1 {
    font-family: Lora, Georgia, serif; font-weight: 500;
    font-size: 2.6rem; letter-spacing: -0.04em; margin-top: 10px;
  }
  .tag { color: oklch(85% 0.17 160); font-weight: 600; font-size: 1.02rem; margin-top: 4px; }
  .pitch { color: rgba(255,255,255,0.6); font-size: 0.92rem; line-height: 1.55; margin: 14px auto 0; max-width: 340px; }
  @media (min-width: 900px) {
    .hero { text-align: left; margin-bottom: 0; }
    .hero img { width: 72px; height: 72px; }
    h1 { font-size: 3.2rem; margin-top: 8px; }
    .tag { font-size: 1.15rem; margin-top: 2px; }
    .pitch { margin-left: 0; margin-right: 0; max-width: 420px; font-size: 0.95rem; }
  }

  /* Cards */
  .card {
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.09);
    border-radius: 20px; padding: 18px; margin-bottom: 12px;
    backdrop-filter: blur(22px) saturate(1.3); -webkit-backdrop-filter: blur(22px) saturate(1.3);
  }
  .feat { display: flex; gap: 12px; align-items: flex-start; padding: 9px 4px; }
  .feat .ico {
    width: 38px; height: 38px; flex-shrink: 0; border-radius: 12px; font-size: 1.05rem;
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08);
    display: flex; align-items: center; justify-content: center;
  }
  .feat b { font-size: 0.88rem; display: block; }
  .feat span { font-size: 0.78rem; color: rgba(255,255,255,0.5); line-height: 1.45; }
  @media (min-width: 900px) {
    /* En el lado del gancho las ventajas van sueltas sobre el degradado:
       una tarjeta ahí competiría con el panel de descarga. */
    .col:first-child .card {
      background: none; border: 0; padding: 0; margin: 30px 0 0;
      backdrop-filter: none; -webkit-backdrop-filter: none;
    }
    .col:first-child .feat { padding: 8px 0; }
  }

  /* CTA */
  a.btn {
    display: block; text-align: center; padding: 16px; border-radius: 16px; text-decoration: none;
    background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
    color: #041010; font-weight: 800; font-size: 1.05rem; letter-spacing: -0.01em;
    box-shadow: 0 1px 0 rgba(255,255,255,0.3) inset, 0 14px 34px -8px oklch(75% 0.2 165 / 0.45);
  }
  /* Trust */
  .trust h2 { font-size: 0.85rem; display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
  .trust p { font-size: 0.78rem; color: rgba(255,255,255,0.55); line-height: 1.55; }
  .trust ol { margin: 10px 0 0 2px; list-style: none; counter-reset: step; }
  .trust li {
    counter-increment: step; font-size: 0.78rem; color: rgba(255,255,255,0.65);
    padding: 4px 0 4px 30px; position: relative; line-height: 1.45;
  }
  .trust li::before {
    content: counter(step); position: absolute; left: 0; top: 3px;
    width: 20px; height: 20px; border-radius: 50%; font-size: 0.68rem; font-weight: 800;
    background: oklch(75% 0.18 165 / 0.15); border: 1px solid oklch(75% 0.18 165 / 0.35);
    color: oklch(88% 0.16 160); display: flex; align-items: center; justify-content: center;
  }
  .trust a { color: oklch(85% 0.17 160); text-decoration: none; }

  /* QR: solo tiene sentido en pantallas grandes (móvil ya tiene el botón). */
  .qr { display: none; }
  @media (min-width: 560px) {
    .qr {
      display: flex; gap: 15px; align-items: center; margin-top: 12px; padding: 18px;
      background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.09);
      border-radius: 20px;
      backdrop-filter: blur(22px) saturate(1.3); -webkit-backdrop-filter: blur(22px) saturate(1.3);
    }
    /* La placa del QR es el degradado del botón: en vez de un parche blanco,
       una pastilla de la marca. El contraste lo pone el módulo casi negro. */
    .qr svg {
      width: 128px; height: 128px; flex-shrink: 0;
      border-radius: 18px; padding: 9px;
      background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(76% 0.2 168));
      box-shadow: 0 1px 0 rgba(255,255,255,0.35) inset,
                  0 14px 34px -10px oklch(75% 0.2 165 / 0.5);
    }
    .qr b { font-size: 0.85rem; display: block; margin-bottom: 4px; }
    .qr span { font-size: 0.78rem; color: rgba(255,255,255,0.55); line-height: 1.5; }
  }
  /* Dentro del panel de descarga el QR no necesita tarjeta: el propio panel
     ya lo separa del fondo. */
  @media (min-width: 900px) {
    .qr {
      background: none; border: 0; border-radius: 0; padding: 4px 0 0;
      margin-top: 18px; gap: 18px; backdrop-filter: none; -webkit-backdrop-filter: none;
    }
    /* Aquí hay sitio de sobra: el QR manda tanto como el botón. */
    .qr svg { width: 172px; height: 172px; border-radius: 22px; padding: 12px; }
  }

  a.web {
    display: block; text-align: center; margin: 18px 0 0; color: rgba(255,255,255,0.55);
    font-size: 0.85rem; text-decoration: none;
  }
  a.web:hover { color: #eef1f5; }
  footer {
    text-align: center; margin-top: 26px; font-size: 0.7rem; color: rgba(255,255,255,0.3);
  }
  footer a { color: rgba(255,255,255,0.45); text-decoration: none; margin: 0 6px; }
</style>
</head>
<body>
<div class="wrap">
 <div class="cols">
  <div class="col">
  <div class="hero">
    <img src="{APP}/logo.png" alt="uroboros" width="96" height="96">
    <h1>uroboros</h1>
    <div class="tag">{L_TAG}</div>
    <p class="pitch">{L_PITCH}</p>
  </div>

  <div class="card">
    <div class="feat"><div class="ico">🍽️</div><div><b>{L_F1_T}</b><span>{L_F1_D}</span></div></div>
    <div class="feat"><div class="ico">📊</div><div><b>{L_F2_T}</b><span>{L_F2_D}</span></div></div>
    <div class="feat"><div class="ico">🍳</div><div><b>{L_F3_T}</b><span>{L_F3_D}</span></div></div>
    <div class="feat"><div class="ico">⚔️</div><div><b>{L_F4_T}</b><span>{L_F4_D}</span></div></div>
  </div>
  </div>

  <div class="col">
  <div class="dl">
  <a class="btn" href="{PLAY}&amp;hl={L_HL}">{L_BTN}</a>

  <div class="qr">
    <svg viewBox="0 0 37 37" role="img" aria-label="{L_QR_ARIA}"><rect width="37" height="37" fill="none"/><path stroke="#04150f" d="M2 2.5h7m1 0h1m3 0h1m4 0h5m1 0h1m2 0h7m-33 1h1m5 0h1m1 0h4m2 0h1m1 0h1m1 0h1m3 0h2m2 0h1m5 0h1m-33 1h1m1 0h3m1 0h1m3 0h1m1 0h2m4 0h1m3 0h3m1 0h1m1 0h3m1 0h1m-33 1h1m1 0h3m1 0h1m1 0h3m1 0h6m5 0h2m1 0h1m1 0h3m1 0h1m-33 1h1m1 0h3m1 0h1m4 0h1m1 0h1m1 0h2m2 0h1m2 0h1m1 0h1m1 0h1m1 0h3m1 0h1m-33 1h1m5 0h1m2 0h1m1 0h1m2 0h1m2 0h3m1 0h1m2 0h1m1 0h1m5 0h1m-33 1h7m1 0h1m1 0h1m1 0h1m1 0h1m1 0h1m1 0h1m1 0h1m1 0h1m1 0h1m1 0h7m-25 1h1m1 0h3m4 0h4m1 0h2m-24 1h1m1 0h2m1 0h3m2 0h2m2 0h1m1 0h4m1 0h1m1 0h1m2 0h1m2 0h1m1 0h2m-33 1h2m2 0h1m4 0h1m6 0h1m1 0h3m2 0h2m1 0h2m1 0h4m-32 1h7m6 0h1m5 0h1m1 0h3m1 0h4m1 0h2m-33 1h3m2 0h1m1 0h1m1 0h1m2 0h2m1 0h2m3 0h1m6 0h1m1 0h1m1 0h1m-32 1h2m2 0h1m1 0h4m5 0h1m1 0h1m1 0h2m1 0h4m1 0h3m-29 1h1m2 0h2m2 0h5m1 0h3m2 0h1m1 0h1m2 0h1m2 0h1m1 0h1m1 0h1m-32 1h2m1 0h1m1 0h3m3 0h1m4 0h1m1 0h4m2 0h1m1 0h1m1 0h3m-31 1h1m2 0h1m4 0h1m1 0h2m4 0h1m3 0h4m1 0h2m3 0h1m-30 1h9m1 0h1m2 0h3m3 0h3m1 0h3m1 0h3m-31 1h1m2 0h2m2 0h1m7 0h1m1 0h1m4 0h3m1 0h1m1 0h2m2 0h1m-33 1h4m1 0h2m2 0h1m4 0h4m2 0h1m5 0h3m1 0h2m-32 1h1m2 0h2m2 0h1m2 0h3m2 0h4m3 0h2m1 0h2m1 0h1m3 0h1m-29 1h3m1 0h3m1 0h1m2 0h7m2 0h1m2 0h1m1 0h3m-32 1h1m1 0h3m3 0h1m3 0h1m4 0h1m1 0h2m2 0h2m1 0h1m2 0h1m2 0h1m-30 1h1m1 0h2m1 0h3m1 0h1m1 0h1m1 0h1m1 0h1m1 0h5m1 0h2m2 0h3m-32 1h1m7 0h3m1 0h4m1 0h1m1 0h1m2 0h1m1 0h1m1 0h3m1 0h2m-33 1h1m1 0h1m1 0h1m1 0h3m2 0h3m1 0h1m1 0h1m1 0h1m2 0h1m1 0h5m2 0h2m-25 1h1m6 0h5m1 0h1m1 0h2m3 0h2m1 0h1m-32 1h7m1 0h1m1 0h2m1 0h2m1 0h2m1 0h1m1 0h1m1 0h2m1 0h1m1 0h1m-29 1h1m5 0h1m1 0h4m3 0h2m1 0h1m1 0h5m3 0h4m-32 1h1m1 0h3m1 0h1m4 0h4m1 0h1m1 0h11m1 0h1m1 0h1m-33 1h1m1 0h3m1 0h1m1 0h4m1 0h3m6 0h1m4 0h1m1 0h1m2 0h1m-33 1h1m1 0h3m1 0h1m1 0h1m1 0h3m1 0h5m1 0h1m1 0h2m2 0h2m2 0h1m-31 1h1m5 0h1m2 0h1m1 0h2m1 0h5m3 0h1m1 0h2m1 0h2m3 0h1m-33 1h7m1 0h3m4 0h1m1 0h2m2 0h1m1 0h1m1 0h1m2 0h1m1 0h1"/></svg>
    <div>
      <b>{L_QR_T}</b>
      <span>{L_QR_D}</span>
    </div>
  </div>
  </div>

  <div class="card trust" style="margin-top:14px;">
    <h2>{L_TRUST_T}</h2>
    <p>{L_TRUST_INTRO}</p>
    <ol>
      <li>{L_STEP1}</li>
      <li>{L_STEP2}</li>
      <li>{L_STEP3}</li>
    </ol>
    <p style="margin-top:10px;">{L_TRUST_OUTRO}</p>
  </div>

  <a class="web" href="{APP}/">{L_WEB}</a>

  <footer>
    uroboros · <a href="{APP}/privacy">{L_PRIVACY}</a>·<a href="{APP}/terms">{L_TERMS}</a>
  </footer>
  </div>
 </div>
</div>
</body>
</html>""".replace("{APP}", _APP_URL).replace("{PLAY}", _PLAY_URL)


# Copy de la landing en los tres idiomas. Es HTML servido por el servidor, así
# que no hay localStorage donde mirar: el idioma sale de Accept-Language.
# El portugués es europeo (pt-PT), igual que el diccionario del frontend.
_LANDING_COPY: dict[str, dict[str, str]] = {
    "es": {
        "L_LANG": "es",
        "L_HL": "es",
        "L_TITLE": "Únete a uroboros 🐍",
        "L_OG_TITLE": "uroboros — come mejor, en pareja",
        "L_OG_DESC": "La app para llevar la comida con tu pareja: registra una comida para los dos a la vez, compite en constancia y comparte la lista de la compra.",
        "L_TAG": "Come mejor. Juntos.",
        "L_PITCH": "Te han invitado a la app para llevar la comida <b>en pareja</b>: una sola vez, para los dos.",
        "L_F1_T": "Registro a dos",
        "L_F1_D": "Apunta una comida y aparece en el diario de ambos, con sus macros calculados.",
        "L_F2_T": "Objetivos y progreso",
        "L_F2_D": "Calorías, proteína, agua, peso y medidas — con historial y tendencias.",
        "L_F3_T": "Recetas e inventario compartido",
        "L_F3_D": "La despensa y la lista de la compra, comunes de verdad.",
        "L_F4_T": "Duelo semanal",
        "L_F4_D": "Un pique sano: quién cumple más sus propios objetivos cada semana.",
        "L_BTN": "Disponible en Google Play",
        "L_QR_ARIA": "Código QR para abrir la app en Google Play desde el móvil",
        "L_QR_T": "¿Estás en el ordenador?",
        "L_QR_D": "Escanea este código con la cámara del móvil Android y se abrirá la app en Google Play.",
        "L_TRUST_T": "📲 Cómo empezar",
        "L_TRUST_INTRO": "En tres pasos estáis registrando juntos:",
        "L_STEP1": "Instala uroboros desde <b>Google Play</b>.",
        "L_STEP2": "Crea tu cuenta, o entra con la que ya tengas.",
        "L_STEP3": "En <b>Amigos</b>, añade a quien te ha invitado.",
        "L_TRUST_OUTRO": "¿Tenías la versión antigua instalada con un archivo APK? Desinstálala e instala la de Google Play: tus datos están en tu cuenta, no pierdes nada.",
        "L_WEB": "¿Sin Android? Úsala desde el navegador →",
        "L_PRIVACY": "privacidad",
        "L_TERMS": "términos",
    },
    "en": {
        "L_LANG": "en",
        "L_HL": "en",
        "L_TITLE": "Join uroboros 🐍",
        "L_OG_TITLE": "uroboros — eat better, together",
        "L_OG_DESC": "The app for tracking food with your partner: log one meal for both of you at once, compete on consistency and share the shopping list.",
        "L_TAG": "Eat better. Together.",
        "L_PITCH": "You've been invited to the app for tracking food <b>as a couple</b>: log it once, for both of you.",
        "L_F1_T": "Log once, for two",
        "L_F1_D": "Log a meal and it shows up in both diaries, with the macros worked out.",
        "L_F2_T": "Goals and progress",
        "L_F2_D": "Calories, protein, water, weight and measurements — with history and trends.",
        "L_F3_T": "Shared recipes and pantry",
        "L_F3_D": "The pantry and the shopping list, genuinely shared.",
        "L_F4_T": "Weekly duel",
        "L_F4_D": "A friendly rivalry: who sticks to their own goals best each week.",
        "L_BTN": "Get it on Google Play",
        "L_QR_ARIA": "QR code to open the app on Google Play from your phone",
        "L_QR_T": "On your computer?",
        "L_QR_D": "Scan this code with your Android phone's camera to open the app on Google Play.",
        "L_TRUST_T": "📲 Getting started",
        "L_TRUST_INTRO": "Three steps and you're logging together:",
        "L_STEP1": "Install uroboros from <b>Google Play</b>.",
        "L_STEP2": "Create your account, or sign in with the one you already have.",
        "L_STEP3": "In <b>Friends</b>, add whoever invited you.",
        "L_TRUST_OUTRO": "Had the old version installed from an APK file? Uninstall it and install the one from Google Play: your data lives in your account, you won't lose anything.",
        "L_WEB": "No Android? Use it in your browser →",
        "L_PRIVACY": "privacy",
        "L_TERMS": "terms",
    },
    "pt": {
        "L_LANG": "pt",
        "L_HL": "pt-PT",
        "L_TITLE": "Junta-te ao uroboros 🐍",
        "L_OG_TITLE": "uroboros — comer melhor, a dois",
        "L_OG_DESC": "A app para gerir a comida com o teu par: regista uma refeição para os dois de uma vez, compete na constância e partilha a lista de compras.",
        "L_TAG": "Comer melhor. Juntos.",
        "L_PITCH": "Convidaram-te para a app de gerir a comida <b>a dois</b>: registas uma vez, conta para ambos.",
        "L_F1_T": "Registo a dois",
        "L_F1_D": "Regista uma refeição e aparece no diário de ambos, com os macros já calculados.",
        "L_F2_T": "Objetivos e progresso",
        "L_F2_D": "Calorias, proteína, água, peso e medidas — com histórico e tendências.",
        "L_F3_T": "Receitas e despensa partilhadas",
        "L_F3_D": "A despensa e a lista de compras, partilhadas a sério.",
        "L_F4_T": "Duelo semanal",
        "L_F4_D": "Uma piadinha saudável: quem cumpre melhor os seus próprios objetivos cada semana.",
        "L_BTN": "Disponível no Google Play",
        "L_QR_ARIA": "Código QR para abrir a app no Google Play a partir do telemóvel",
        "L_QR_T": "Estás no computador?",
        "L_QR_D": "Lê este código com a câmara do telemóvel Android e a app abre-se no Google Play.",
        "L_TRUST_T": "📲 Como começar",
        "L_TRUST_INTRO": "Em três passos estão a registar juntos:",
        "L_STEP1": "Instala o uroboros a partir do <b>Google Play</b>.",
        "L_STEP2": "Cria a tua conta, ou entra com a que já tens.",
        "L_STEP3": "Em <b>Amigos</b>, adiciona quem te convidou.",
        "L_TRUST_OUTRO": "Tinhas a versão antiga instalada a partir de um ficheiro APK? Desinstala-a e instala a do Google Play: os teus dados estão na tua conta, não perdes nada.",
        "L_WEB": "Sem Android? Usa-a no navegador →",
        "L_PRIVACY": "privacidade",
        "L_TERMS": "termos",
    },
}


def _pick_language(accept_language: str | None, lang: str | None = None) -> str:
    """Idioma de la landing: ?lang= manda sobre Accept-Language, y es de reserva.

    El parámetro de query existe por dos motivos prácticos:
      - Cloudflare solo honra `Vary` para Accept-Encoding salvo que configures
        una Cache Rule; la query string, en cambio, va en la clave de caché
        siempre. Sin esto el edge puede repartir un único idioma a todos.
      - Los crawlers de WhatsApp y compañía no mandan Accept-Language, así que
        la tarjeta del enlace saldría siempre en español. Con ?lang=, quien
        comparte propaga su idioma y cada variante se cachea por separado.

    Lo demás es deliberadamente simple: recorre las preferencias en orden y se
    queda con la primera que sepamos servir. No pesa los factores q= porque los
    navegadores ya las mandan ordenadas de mayor a menor.
    """
    if lang and lang.split("-")[0].lower() in _LANDING_COPY:
        return lang.split("-")[0].lower()
    if not accept_language:
        return "es"
    for part in accept_language.split(","):
        tag = part.split(";")[0].strip().lower()
        primary = tag.split("-")[0]
        if primary in _LANDING_COPY:
            return primary
    return "es"


def _render_landing(lang: str, canonical: str) -> str:
    html = _LANDING_HTML.replace("{L_CANONICAL}", canonical)
    for key, value in _LANDING_COPY[lang].items():
        html = html.replace("{" + key + "}", value)
    return html


@landing_router.get("/unete", response_class=HTMLResponse)
def invite_landing(
    accept_language: str | None = Header(default=None),
    lang: str | None = None,
) -> HTMLResponse:
    """Public invite landing: OG preview card + Google Play link + how to start.

    Se sirve en es/en/pt. Aquí no hay sesión ni localStorage — quien abre este
    enlace todavía no tiene la app —, así que el idioma sale de ?lang= o, en su
    defecto, de Accept-Language.
    """
    resolved = _pick_language(accept_language, lang)
    # La canónica refleja lo que se pidió: si el enlace traía ?lang=, se queda,
    # que es lo que hace que cada idioma tenga su propia tarjeta cacheada.
    canonical = f"{_APP_URL}/unete?lang={resolved}" if lang else f"{_APP_URL}/unete"
    # 1h cache: the page rarely changes and this keeps Cloudflare serving it
    # from the edge. Caveat: copy edits take up to an hour to show for anyone
    # who already viewed it — bust with a ?v= query while reviewing changes.
    # `Vary` es correcto en HTTP y lo respetan navegadores y cachés intermedias,
    # pero Cloudflare solo lo honra para Accept-Encoding salvo Cache Rule: el
    # reparto de idiomas de verdad lo asegura ?lang=, que sí va en la clave.
    return HTMLResponse(
        _render_landing(resolved, canonical),
        headers={
            "Cache-Control": "public, max-age=3600",
            "Vary": "Accept-Language",
        },
    )


@legacy_landing_router.get("/unete", include_in_schema=False)
def invite_landing_legacy(request: Request) -> RedirectResponse:
    """La landing vivía en /api/unete, y sigue habiendo enlaces por ahí.

    Cada WhatsApp ya enviado apunta aquí para siempre, así que esta ruta no se
    borra: redirige permanente y conserva la query (el ?lang=).
    """
    qs = request.url.query
    return RedirectResponse(f"/unete?{qs}" if qs else "/unete", status_code=301)
