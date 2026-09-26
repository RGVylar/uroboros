"""Filtro de nombres de usuario.

El nombre se ve fuera de tu cuenta (solicitudes de amistad, perfil de amigo,
diario de la pareja), así que un insulto como nombre llega a otra persona.
No pretende ser exhaustivo: corta lo evidente, y lo que se cuele se resuelve
con la denuncia y bloqueo de /friends/{id}/report.
"""
from __future__ import annotations

import re
import unicodedata

_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})

# Solo palabras sueltas: como subcadena darían falsos positivos
# ("computadora" contiene "puta", "Nazir" contiene "nazi", "Scunthorpe"...).
_WORDS = {
    # es
    "puta", "puto", "putas", "zorra", "maricon", "maricones", "marica", "bollera",
    "tortillera", "sidoso", "subnormal", "retrasado", "mongolo", "gilipollas",
    "cabron", "cabrona", "mierda", "polla", "cono", "follar", "sudaca", "sudacas",
    "negrata", "panchito", "moromierda", "nazi", "nazis", "hitler", "heil",
    # en
    "nigger", "niggers", "nigga", "niggas", "faggot", "fag", "fags", "retard",
    "chink", "spic", "kike", "wetback", "tranny", "cunt", "whore", "slut", "fuck",
    "fucker", "shit", "bitch", "rape", "rapist", "kkk",
    # pt
    "caralho", "buceta", "viado", "macaco", "merda", "foda", "cuzao", "arrombado",
}

# Estas sí como subcadena del nombre sin espacios: son lo bastante largas y
# específicas como para no aparecer dentro de un nombre real, y así se cazan
# variantes pegadas ("xXniggerXx", "negratadelbarrio").
_SUBSTRINGS = (
    "nigger", "nigga", "faggot", "negrata", "sudaca", "maricon", "hijoputa",
    "hijodeputa", "hijaputa", "gilipollas", "hitler", "caralho", "buceta",
    "siegheil", "whitepower", "negrodemierda", "morodemierda",
)


def _normalize(text: str) -> str:
    s = unicodedata.normalize("NFKD", text.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.translate(_LEET)


def is_offensive_name(name: str) -> bool:
    s = _normalize(name)
    words = re.findall(r"[a-z]+", s)
    if any(w in _WORDS for w in words):
        return True
    # Colapsa repeticiones ("niiigger") antes de buscar subcadenas.
    joined = re.sub(r"(.)\1+", r"\1", "".join(words))
    return any(re.sub(r"(.)\1+", r"\1", sub) in joined for sub in _SUBSTRINGS)
