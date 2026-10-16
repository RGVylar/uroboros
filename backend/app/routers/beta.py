"""Página para apuntarse a la beta (/beta).

La app está en prueba cerrada en Google Play: solo la puede instalar quien esté
en la lista de emails de la prueba, que se mantiene a mano en Play Console. Esta
página es el enlace que se reparte: explica qué hace falta, recoge el email de
la cuenta de Google y, al apuntarse, deja a la vista los pasos que vienen.

Como /unete, la pinta el backend y se monta sin el prefijo /api. Es un
formulario HTML de toda la vida (sin JavaScript): POST a la misma URL y el
servidor responde con la página de "ya estás".
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

  footer { text-align: center; margin-top: 26px; font-size: 0.7rem; color: rgba(255,255,255,0.3); }
  footer a { color: rgba(255,255,255,0.45); text-decoration: none; margin: 0 6px; }
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <img src="{APP}/logo.png" alt="uroboros" width="72" height="72">
    <div class="eyebrow">{L_EYEBROW}</div>
    <h1>{HEADLINE}</h1>
    <p class="pitch">{PITCH}</p>
  </div>
  {BODY}
  <footer>
    uroboros · <a href="{APP}/privacy">{L_PRIVACY}</a>·<a href="{APP}/terms">{L_TERMS}</a>
  </footer>
</div>
</body>
</html>"""

_FORM = """
  <div class="card">
    <h2>{L_REQ_T}</h2>
    <div class="req"><div class="ico">{ICON_PHONE}</div><span>{L_REQ1}</span></div>
    <div class="req"><div class="ico">{ICON_CALENDAR}</div><span>{L_REQ2}</span></div>
    <div class="req"><div class="ico">{ICON_CHECK}</div><span>{L_REQ3}</span></div>
  </div>

  <form class="card" method="post" action="/beta?lang={L_LANG}">
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
"""

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
        "L_PITCH": "uroboros es mi app para llevar las calorías y los macros <b>en pareja</b>: apuntas una comida una vez y cuenta para los dos. Para que salga en Google Play, Google pide que antes la prueben <b>12 personas durante 14 días</b>.",
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
        "L_PITCH": "uroboros is my app for tracking calories and macros <b>as a couple</b>: log a meal once and it counts for both of you. Before it can come out on Google Play, Google asks for <b>12 people to test it for 14 days</b>.",
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
        "L_PITCH": "O uroboros é a minha app para gerir calorias e macros <b>a dois</b>: registas uma refeição uma vez e conta para ambos. Para sair no Google Play, a Google pede que antes a testem <b>12 pessoas durante 14 dias</b>.",
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
    else:
        body = (
            _FORM.replace("{ERROR}", f'<p class="error">{error}</p>' if error else "")
            .replace("{EMAIL}", escape(email))
            .replace("{NAME}", escape(name))
        )
        headline, eyebrow, pitch = copy["L_HEADLINE"], copy["L_EYEBROW"], copy["L_PITCH"]
    html = (
        _HTML.replace("{BODY}", body)
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
