"""Códigos de invitación de amistad.

Un código por usuario que se comparte en lugar del email. Añadir por email
significaba que cualquiera que conociese tu dirección podía dejarte una solicitud
pendiente delante; el código es algo que decides entregar y que puedes rotar si
se te escapa.

El alfabeto es Crockford Base32: sin I, L, O ni U, que son justo las que se leen
mal al copiar un código a mano. 32 símbolos y 8 caracteres son 32⁸ ≈ 1,1·10¹²
combinaciones — con rate limit en el endpoint que los resuelve, no es enumerable.
"""
import secrets

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CODE_LEN = 8

# Las que la gente teclea creyendo que son otra cosa. Crockford las define así.
_CONFUSABLES = str.maketrans({"O": "0", "I": "1", "L": "1", "U": "V"})


def generate_code() -> str:
    """Un código nuevo. secrets, no random: esto es un secreto compartido."""
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LEN))


def normalize(raw: str) -> str:
    """Lo que teclea el usuario → lo que hay en la BD.

    Acepta minúsculas, espacios y el guion del formato bonito, y corrige las
    confusiones típicas (una O por un cero). Devuelve "" si no queda un código
    válido, para que quien llama trate el caso sin distinguir vacío de basura.
    """
    cleaned = "".join(c for c in raw.upper() if c.isalnum()).translate(_CONFUSABLES)
    if len(cleaned) != CODE_LEN or any(c not in ALPHABET for c in cleaned):
        return ""
    return cleaned


def format_code(code: str) -> str:
    """Para enseñarlo: XXXX-XXXX se copia a mano mucho mejor que XXXXXXXX."""
    return f"{code[:4]}-{code[4:]}"
