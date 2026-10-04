"""Idioma de la petición en curso, para lo poco que el backend traduce.

El cliente manda `X-Lang` (es/en/pt) en cada llamada; un middleware lo deja en
esta ContextVar. Hoy solo lo usan los nombres de los alimentos genéricos, que
son los únicos productos que tienen traducción.
"""
from contextvars import ContextVar

SUPPORTED = ("es", "en", "pt")

_lang: ContextVar[str] = ContextVar("request_lang", default="es")


def set_request_lang(raw: str | None) -> None:
    code = (raw or "").strip().lower()[:2]
    _lang.set(code if code in SUPPORTED else "es")


def request_lang() -> str:
    return _lang.get()


def localized_name(product) -> str:
    lang = _lang.get()
    if lang == "en" and product.name_en:
        return product.name_en
    if lang == "pt" and product.name_pt:
        return product.name_pt
    return product.name
