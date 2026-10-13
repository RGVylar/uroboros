"""Receta compartida fuera de la app: el código del enlace y la página /r/<código>.

La página la pinta el backend (igual que /unete) porque los crawlers de
WhatsApp y compañía no ejecutan la SPA: necesitan el HTML con las etiquetas
Open Graph ya puestas para sacar la tarjeta con el nombre y las kcal.
"""
import json
import re
import secrets
from html import escape

from app.models import Recipe

APP_URL = "https://comida.mugrelore.com"

# Sin 0/O/1/l/I: el código a veces se lee en voz alta o se copia a mano.
_ALPHABET = "23456789abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ"


def new_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(8))


def clean_name(name: str) -> str:
    """"Aceite De Oliva Virgen Extra" → "Aceite de oliva virgen extra".

    Los nombres de Open Food Facts llegan a menudo en Title Case. Se pasa a
    minúscula cada palabra capitalizada salvo la primera; las siglas en
    mayúsculas (SOS, AOVE) se quedan como están.
    """
    words = name.split(" ")
    out = words[:1]
    for w in words[1:]:
        out.append(w.lower() if len(w) > 1 and w[0].isupper() and w[1:].islower() else w)
    return " ".join(out)


def _unit(product) -> str:
    return product.unit or "g"


def fmt_qty(grams: float, unit: str) -> str:
    if unit == "unit":
        q = round(grams / 100, 2)
        return f"{q:g} ud"
    return f"{round(grams):g} {unit}"


def macros(recipe: Recipe, factor: float = 1.0) -> dict[str, int]:
    cal = p = c = f = 0.0
    for ing in recipe.ingredients:
        k = ing.grams / 100 * factor
        pr = ing.product
        cal += pr.calories_per_100g * k
        p += pr.protein_per_100g * k
        c += pr.carbs_per_100g * k
        f += pr.fat_per_100g * k
    return {"kcal": round(cal), "p": round(p), "c": round(c), "f": round(f)}


# Mismo formato que frontend/src/lib/recipeSteps.ts: @[Nombre](id) o @[Nombre](id:gramos).
_TAG = re.compile(r"@\[([^\]]+)\]\((\d+)(?::(\d+(?:\.\d+)?))?\)")


def step_parts(step: str, recipe: Recipe) -> list[dict]:
    by_product = {ing.product_id: ing for ing in recipe.ingredients}
    parts: list[dict] = []
    last = 0
    for m in _TAG.finditer(step):
        if m.start() > last:
            parts.append({"text": step[last:m.start()]})
        ing = by_product.get(int(m.group(2)))
        if ing:
            grams = float(m.group(3)) if m.group(3) else ing.grams
            parts.append({"name": clean_name(ing.product.display_name), "grams": grams, "unit": _unit(ing.product)})
        else:
            parts.append({"text": m.group(1)})
        last = m.end()
    if last < len(step):
        parts.append({"text": step[last:]})
    return parts


COPY = {
    "es": {
        "by": "de {name}", "servings": "Raciones", "per_serving": "por ración", "whole": "receta entera",
        "ingredients": "Ingredientes", "howto": "Cómo se hace", "prep": "Preparación", "cook": "Cocción",
        "min": "min", "kcal": "kcal", "p": "prot.", "c": "carbos", "f": "grasa",
        "save": "Guardar en mi Uroboros", "no_app": "¿Aún no usas Uroboros? Conócelo",
        "og_desc_serv": "{kcal} kcal · P{p} por ración · {n} raciones", "og_desc": "{kcal} kcal · P{p} · {ings}", "ing_one": "1 ingrediente", "ing_many": "{n} ingredientes",
        "not_found_t": "Esta receta ya no está compartida", "not_found": "Quien la compartió ha retirado el enlace.",
    },
    "en": {
        "by": "by {name}", "servings": "Servings", "per_serving": "per serving", "whole": "whole recipe",
        "ingredients": "Ingredients", "howto": "How to make it", "prep": "Prep", "cook": "Cook",
        "min": "min", "kcal": "kcal", "p": "protein", "c": "carbs", "f": "fat",
        "save": "Save to my Uroboros", "no_app": "Not using Uroboros yet? Take a look",
        "og_desc_serv": "{kcal} kcal · P{p} per serving · {n} servings", "og_desc": "{kcal} kcal · P{p} · {ings}", "ing_one": "1 ingredient", "ing_many": "{n} ingredients",
        "not_found_t": "This recipe is no longer shared", "not_found": "Whoever shared it has removed the link.",
    },
    "pt": {
        "by": "de {name}", "servings": "Doses", "per_serving": "por dose", "whole": "receita inteira",
        "ingredients": "Ingredientes", "howto": "Como se faz", "prep": "Preparação", "cook": "Cozedura",
        "min": "min", "kcal": "kcal", "p": "prot.", "c": "hidratos", "f": "gordura",
        "save": "Guardar no meu Uroboros", "no_app": "Ainda não usas o Uroboros? Conhece-o",
        "og_desc_serv": "{kcal} kcal · P{p} por dose · {n} doses", "og_desc": "{kcal} kcal · P{p} · {ings}", "ing_one": "1 ingrediente", "ing_many": "{n} ingredientes",
        "not_found_t": "Esta receita já não está partilhada", "not_found": "Quem a partilhou retirou a ligação.",
    },
}


_PAGE = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Uroboros</title>
<meta property="og:type" content="article">
<meta property="og:site_name" content="Uroboros">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{og_desc}">
<meta property="og:image" content="{app}/social-banner.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:url" content="{canonical}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{app}/logo.png" type="image/png">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #06070a; color: #eef1f5; font-family: 'Segoe UI', system-ui, sans-serif;
    min-height: 100dvh; line-height: 1.5;
    background-image:
      radial-gradient(60% 45% at 15% 0%, oklch(45% 0.12 170 / 0.22), transparent 60%),
      radial-gradient(50% 40% at 90% 15%, oklch(45% 0.14 300 / 0.16), transparent 60%);
    background-attachment: fixed;
  }}
  .wrap {{ max-width: 520px; margin: 0 auto; padding: 28px 18px 40px; }}
  .head {{ display: flex; gap: 12px; align-items: center; margin-bottom: 16px; }}
  .head img {{ width: 48px; height: 48px; }}
  h1 {{ font-family: Lora, Georgia, serif; font-weight: 500; font-size: 1.7rem; letter-spacing: -0.02em; line-height: 1.15; }}
  .sub {{ color: rgba(255,255,255,0.5); font-size: 0.85rem; margin-top: 2px; }}
  .card {{ background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.09); border-radius: 18px; padding: 14px; margin-bottom: 12px; }}
  .serv {{ display: flex; justify-content: space-between; align-items: center; }}
  .serv span {{ color: rgba(255,255,255,0.6); font-size: 0.9rem; }}
  .stepper {{ display: flex; align-items: center; gap: 12px; }}
  .stepper button {{ width: 32px; height: 32px; border-radius: 50%; border: 1px solid rgba(255,255,255,0.15); background: rgba(255,255,255,0.06); color: #fff; font-size: 1.1rem; cursor: pointer; }}
  .stepper b {{ font-size: 1.15rem; min-width: 1.5rem; text-align: center; }}
  .mac {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; text-align: center; }}
  .mac div {{ background: rgba(255,255,255,0.04); border-radius: 12px; padding: 8px 0; }}
  .mac b {{ display: block; font-size: 1.1rem; }}
  .mac span {{ font-size: 0.72rem; color: rgba(255,255,255,0.5); }}
  .note {{ font-size: 0.75rem; color: rgba(255,255,255,0.45); text-align: center; margin-top: 8px; }}
  h2 {{ font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase; color: rgba(255,255,255,0.55); margin: 20px 4px 8px; }}
  ul {{ list-style: none; }}
  li.ing {{ display: flex; justify-content: space-between; gap: 12px; padding: 8px 4px; border-bottom: 1px dashed rgba(255,255,255,0.08); font-size: 0.95rem; }}
  li.ing .q {{ color: rgba(255,255,255,0.55); white-space: nowrap; font-variant-numeric: tabular-nums; }}
  ol {{ list-style: none; display: grid; gap: 12px; }}
  ol li {{ display: flex; gap: 10px; font-size: 0.95rem; line-height: 1.7; }}
  .n {{ flex-shrink: 0; width: 26px; height: 26px; border-radius: 50%; display: grid; place-items: center; font-size: 0.8rem; font-weight: 800; background: oklch(75% 0.18 160 / 0.18); color: oklch(85% 0.15 160); margin-top: 2px; }}
  .chip {{ display: inline-flex; align-items: baseline; gap: 5px; padding: 0 8px; border-radius: 999px; background: oklch(75% 0.18 160 / 0.14); color: oklch(88% 0.12 160); font-weight: 600; white-space: nowrap; }}
  .chip .q {{ font-weight: 500; color: oklch(80% 0.1 160 / 0.8); font-size: 0.9em; }}
  .cta {{ display: block; text-align: center; text-decoration: none; padding: 14px; border-radius: 14px; font-weight: 700; margin-top: 22px; color: #04130c; background: linear-gradient(135deg, oklch(85% 0.17 160), oklch(70% 0.19 170)); }}
  .alt {{ display: block; text-align: center; color: rgba(255,255,255,0.55); font-size: 0.85rem; margin-top: 12px; text-decoration: none; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <img src="{app}/logo.png" alt="">
    <div><h1>{title}</h1><div class="sub">{subtitle}</div></div>
  </div>
  {servings_block}
  <div class="card">
    <div class="mac">
      <div><b style="color:oklch(82% 0.15 60)">{kcal}</b><span>{l_kcal}</span></div>
      <div><b style="color:oklch(78% 0.14 240)">{p} g</b><span>{l_p}</span></div>
      <div><b style="color:oklch(78% 0.14 295)">{c} g</b><span>{l_c}</span></div>
      <div><b style="color:oklch(75% 0.17 25)">{f} g</b><span>{l_f}</span></div>
    </div>
    <div class="note">{macro_note}</div>
  </div>
  <h2>{l_ingredients}</h2>
  <ul>{ingredients}</ul>
  {steps_block}
  <a class="cta" href="{save_href}">{l_save}</a>
  <a class="alt" href="/unete?lang={lang}">{l_no_app} →</a>
</div>
<script>
  // Cambiar las raciones reescala las cantidades (ingredientes y pastillas de
  // los pasos); los macros por ración no cambian.
  (function () {{
    var base = {base_servings}, n = base, out = document.getElementById('n');
    if (!out) return;
    function fmt(g, u) {{
      if (u === 'unit') return (Math.round(g / 100 * 100) / 100) + ' ud';
      return Math.round(g) + ' ' + u;
    }}
    function render() {{
      out.textContent = n;
      document.querySelectorAll('[data-g]').forEach(function (el) {{
        el.textContent = fmt(parseFloat(el.dataset.g) * n / base, el.dataset.u);
      }});
    }}
    document.getElementById('less').onclick = function () {{ if (n > 1) {{ n--; render(); }} }};
    document.getElementById('more').onclick = function () {{ if (n < 50) {{ n++; render(); }} }};
  }})();
</script>
</body>
</html>
"""

_NOT_FOUND = """<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Uroboros</title><link rel="icon" href="{app}/logo.png" type="image/png">
<style>body{{background:#06070a;color:#eef1f5;font-family:'Segoe UI',system-ui,sans-serif;display:grid;place-items:center;min-height:100dvh;margin:0;text-align:center;padding:24px}}
img{{width:64px}}h1{{font-family:Lora,Georgia,serif;font-weight:500;margin:14px 0 6px}}p{{color:rgba(255,255,255,.55)}}a{{color:oklch(85% 0.17 160)}}</style></head>
<body><div><img src="{app}/logo.png" alt=""><h1>{title}</h1><p>{body}</p><p style="margin-top:18px"><a href="/unete?lang={lang}">{no_app} →</a></p></div></body></html>
"""


def _qty_span(grams: float, unit: str) -> str:
    return f'<span class="q" data-g="{grams:g}" data-u="{unit}">{escape(fmt_qty(grams, unit))}</span>'


def render_page(recipe: Recipe, owner_name: str, lang: str, canonical: str) -> str:
    t = COPY[lang]
    servings = recipe.servings or 0
    per = macros(recipe, 1 / servings) if servings > 1 else macros(recipe)
    title = escape(recipe.name)

    meta = [t["by"].format(name=escape(owner_name))]
    if recipe.prep_minutes:
        meta.append(f'{t["prep"]} {recipe.prep_minutes} {t["min"]}')
    if recipe.cook_minutes:
        meta.append(f'{t["cook"]} {recipe.cook_minutes} {t["min"]}')

    ingredients = "".join(
        f'<li class="ing"><span>{escape(clean_name(ing.product.display_name))}</span>{_qty_span(ing.grams, _unit(ing.product))}</li>'
        for ing in recipe.ingredients
    )

    steps_html = ""
    for i, step in enumerate(recipe.steps, 1):
        body = "".join(
            escape(p["text"]) if "text" in p
            else f'<span class="chip">{escape(p["name"])}{_qty_span(p["grams"], p["unit"])}</span>'
            for p in step_parts(step, recipe)
        )
        steps_html += f'<li><span class="n">{i}</span><p>{body}</p></li>'
    steps_block = f'<h2>{t["howto"]}</h2><ol>{steps_html}</ol>' if steps_html else ""

    if servings > 1:
        servings_block = (
            f'<div class="card serv"><span>{t["servings"]}</span><div class="stepper">'
            f'<button id="less" aria-label="−">−</button><b id="n">{servings}</b>'
            f'<button id="more" aria-label="+">+</button></div></div>'
        )
        og_desc = t["og_desc_serv"].format(kcal=per["kcal"], p=per["p"], n=servings)
    else:
        servings_block = ""
        n = len(recipe.ingredients)
        ings = t["ing_one"] if n == 1 else t["ing_many"].format(n=n)
        og_desc = t["og_desc"].format(kcal=per["kcal"], p=per["p"], ings=ings)

    values = {
        "lang": lang, "app": APP_URL, "canonical": escape(canonical), "title": title,
        "og_desc": escape(og_desc), "subtitle": " · ".join(meta),
        "servings_block": servings_block, "base_servings": json.dumps(max(servings, 1)),
        "kcal": per["kcal"], "p": per["p"], "c": per["c"], "f": per["f"],
        "l_kcal": t["kcal"], "l_p": t["p"], "l_c": t["c"], "l_f": t["f"],
        "macro_note": t["per_serving"] if servings > 1 else t["whole"],
        "l_ingredients": t["ingredients"], "ingredients": ingredients, "steps_block": steps_block,
        "save_href": f"/recipes?importar={recipe.public_code}",
        "l_save": t["save"], "l_no_app": t["no_app"],
    }
    return _PAGE.format(**values)


def render_not_found(lang: str) -> str:
    t = COPY[lang]
    return _NOT_FOUND.format(lang=lang, app=APP_URL, title=t["not_found_t"], body=t["not_found"], no_app=t["no_app"])
