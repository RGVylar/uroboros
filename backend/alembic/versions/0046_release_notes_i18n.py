"""Translate release notes to English and Portuguese

Revision ID: 0046
Revises: 0045
Create Date: 2026-07-25

Hasta ahora `release_notes.title` y cada `items[].title`/`desc` eran texto
plano en español, a propósito: traducirlas a mano en cada release salía caro
(escribir cada nota tres veces). Ver la decisión original en 0044 y en
`documentation/02 - Arquitectura/Changelog y versiones.md`.

Se revisa esa decisión: ahora que la traducción la hace el asistente en vez de
un humano, el coste recurrente que la motivaba ya no aplica. Esta migración:

1. Convierte `release_notes.title` de VARCHAR a JSON (mismo tipo que `items`,
   que ya era JSON y no necesita cambio de columna).
2. Traduce el contenido de las 6 notas ya publicadas (1.5-1.10) a
   `{"es": ..., "en": ..., "pt": ...}`. El router (`_resolve_text` en
   `app/routers/release_notes.py`) sabe leer tanto el string plano viejo como
   este dict nuevo, así que esta migración no rompe nada aunque quedara algo
   sin traducir — pero aquí se traduce todo lo existente.

A partir de aquí, las migraciones de seed nuevas deben escribir `title`/`desc`
ya como dict de 3 idiomas directamente (no hace falta otra migración de
traducción después).
"""
import json

from alembic import op
import sqlalchemy as sa

revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None


# ── Contenido traducido de las 6 notas ya publicadas ────────────────────────
# Cada entrada: (version, title_dict, items_dict_list)
_NOTES = {
    "1.5": {
        "title": {
            "es": "Duelo semanal",
            "en": "Weekly duel",
            "pt": "Duelo semanal",
        },
        "items": [
            {
                "type": "nuevo",
                "title": {
                    "es": "Duelo semanal de adherencia",
                    "en": "Weekly adherence duel",
                    "pt": "Duelo semanal de aderência",
                },
                "desc": {
                    "es": "Compite con tu pareja: quién cumple más sus propios objetivos cada semana. Actívalo en Amigos — solo se comparte el porcentaje, nunca el diario.",
                    "en": "Compete with your partner: who sticks to their own goals best each week. Turn it on in Friends — only the percentage is shared, never your diary.",
                    "pt": "Compete com o teu par: quem cumpre melhor os seus próprios objetivos cada semana. Ativa-o em Amigos — só se partilha a percentagem, nunca o diário.",
                },
            },
            {
                "type": "nuevo",
                "title": {
                    "es": "Avisos de nueva versión",
                    "en": "New version alerts",
                    "pt": "Avisos de nova versão",
                },
                "desc": {
                    "es": "La app te avisa cuando hay una actualización disponible, con lo más destacado que trae.",
                    "en": "The app lets you know when an update's available, with the highlights it brings.",
                    "pt": "A app avisa-te quando há uma atualização disponível, com os destaques que traz.",
                },
            },
            {
                "type": "mejora",
                "title": {
                    "es": "Novedades configurables",
                    "en": "Configurable changelog",
                    "pt": "Novidades configuráveis",
                },
                "desc": {
                    "es": "Puedes silenciar estos avisos en Ajustes; los lanzamientos importantes se muestran igualmente.",
                    "en": "You can mute these alerts in Settings; major launches still show either way.",
                    "pt": "Podes silenciar estes avisos em Definições; os lançamentos importantes aparecem sempre.",
                },
            },
        ],
    },
    "1.6": {
        "title": {
            "es": "Pareja y amigos, por fin separados",
            "en": "Partner and friends, finally split apart",
            "pt": "Par e amigos, finalmente separados",
        },
        "items": [
            {
                "type": "nuevo",
                "title": {
                    "es": "Ahora eliges: pareja o amigo",
                    "en": "Now you choose: partner or friend",
                    "pt": "Agora escolhes: par ou amigo",
                },
                "desc": {
                    "es": "Al añadir a alguien dices qué sois. La pareja comparte despensa y lista de la compra; los amigos, recetas y duelo. Si ya compartíais despensa, sois pareja y no tienes que hacer nada.",
                    "en": "When you add someone, you say what you are. Partners share the pantry and shopping list; friends share recipes and the duel. If you already shared a pantry, you're partners — no action needed.",
                    "pt": "Ao adicionares alguém, dizes o que são. O par partilha despensa e lista de compras; os amigos, receitas e duelo. Se já partilhavam despensa, são par e não precisas de fazer nada.",
                },
            },
            {
                "type": "nuevo",
                "title": {
                    "es": "Recetas para quien tú quieras",
                    "en": "Recipes for whoever you want",
                    "pt": "Receitas para quem quiseres",
                },
                "desc": {
                    "es": "Cada receta elige su círculo: privada 🔒, solo tu pareja 💚 o tus amigos 🔗. Las que ya compartías siguen visibles para tus amigos, como hasta ahora.",
                    "en": "Each recipe picks its circle: private 🔒, partner only 💚, or friends 🔗. The ones you already shared stay visible to your friends, same as before.",
                    "pt": "Cada receita escolhe o seu círculo: privada 🔒, só para o par 💚, ou amigos 🔗. As que já partilhavas continuam visíveis para os teus amigos, como até agora.",
                },
            },
            {
                "type": "mejora",
                "title": {
                    "es": "Nadie entra en tu diario sin permiso",
                    "en": "No one logs food in your diary without permission",
                    "pt": "Ninguém regista no teu diário sem permissão",
                },
                "desc": {
                    "es": "Las solicitudes nuevas ya no dan permiso para apuntar comida en tu diario: ahora se concede a mano. Los permisos que ya diste siguen tal cual — revísalos en Amigos si quieres.",
                    "en": "New requests no longer grant permission to log food in your diary — it's now granted by hand. Permissions you already gave stay as they were — review them in Friends if you want.",
                    "pt": "Os pedidos novos já não dão permissão para registar comida no teu diário: agora concede-se à mão. As permissões que já deste mantêm-se — revê-as em Amigos se quiseres.",
                },
            },
            {
                "type": "fix",
                "title": {
                    "es": "La despensa ya no se descuadra",
                    "en": "The pantry no longer gets out of sync",
                    "pt": "A despensa já não desacerta",
                },
                "desc": {
                    "es": "Al dejar de compartir despensa, las cantidades podían duplicarse. Ya no.",
                    "en": "Quantities could end up duplicated when you stopped sharing a pantry. Not anymore.",
                    "pt": "Ao deixar de partilhar despensa, as quantidades podiam duplicar-se. Já não.",
                },
            },
        ],
    },
    "1.7": {
        "title": {
            "es": "Comida compartida, más fina",
            "en": "Shared meals, refined",
            "pt": "Comida partilhada, mais afinada",
        },
        "items": [
            {
                "type": "mejora",
                "title": {
                    "es": "Cada uno con sus gramos",
                    "en": "Everyone with their own grams",
                    "pt": "Cada um com as suas gramas",
                },
                "desc": {
                    "es": "Al editar una comida que tu pareja también tiene, ajustáis la cantidad de cada uno por separado. Y si se le olvidó ponérsela, se la añades ahí mismo.",
                    "en": "Editing a meal your partner also has now lets you each adjust your own amount separately. And if they forgot to log theirs, you can add it right there.",
                    "pt": "Ao editar uma refeição que o teu par também tem, ajustam a quantidade de cada um separadamente. E se ele/ela se esqueceu de a registar, adicionas-lha ali mesmo.",
                },
            },
            {
                "type": "mejora",
                "title": {
                    "es": "Al borrar, eliges de quién",
                    "en": "When you delete, you choose whose",
                    "pt": "Ao apagar, escolhes de quem",
                },
                "desc": {
                    "es": "Si un alimento lo tenéis los dos, al borrarlo decides: para los dos, solo el tuyo o solo el de tu pareja.",
                    "en": "If a food item belongs to both of you, deleting it lets you decide: both, just yours, or just your partner's.",
                    "pt": "Se um alimento é dos dois, ao apagá-lo decides: dos dois, só o teu, ou só o do teu par.",
                },
            },
            {
                "type": "fix",
                "title": {
                    "es": "El diario se actualiza al instante",
                    "en": "The diary updates instantly",
                    "pt": "O diário atualiza-se na hora",
                },
                "desc": {
                    "es": "Al cambiar una comida de momento del día, la tarjeta se mueve sola, sin recargar.",
                    "en": "Change a meal's time of day and the card moves on its own, no reload needed.",
                    "pt": "Ao mudar uma refeição de momento do dia, o cartão move-se sozinho, sem recarregar.",
                },
            },
        ],
    },
    "1.8": {
        "title": {
            "es": "El día de tu pareja, en tu diario",
            "en": "Your partner's day, in your diary",
            "pt": "O dia do teu par, no teu diário",
        },
        "items": [
            {
                "type": "nuevo",
                "title": {
                    "es": "Ver lo que lleva tu pareja hoy",
                    "en": "See what your partner's had today",
                    "pt": "Vê o que o teu par já comeu hoje",
                },
                "desc": {
                    "es": "Un chip arriba de tu diario resume su día (kcal y proteína). Tócalo y sus comidas aparecen intercaladas entre las tuyas, en su color, para que os coordinéis.",
                    "en": "A chip above your diary summarizes their day (kcal and protein). Tap it and their meals show up interleaved with yours, in their color, to help you two coordinate.",
                    "pt": "Um chip por cima do teu diário resume o dia dele/dela (kcal e proteína). Toca-lhe e as refeições dele/dela aparecem intercaladas com as tuas, na cor dele/dela, para se coordenarem.",
                },
            },
            {
                "type": "nuevo",
                "title": {
                    "es": "Ponértelo a ti también",
                    "en": "Log it for yourself too",
                    "pt": "Regista também para ti",
                },
                "desc": {
                    "es": "¿Ha comido algo que tú también quieres registrar? Con el botón + de cada plato suyo te lo copias a tu diario al instante.",
                    "en": "Did they eat something you want to log as well? The + button on each of their dishes copies it straight into your diary.",
                    "pt": "Ele/ela comeu algo que também queres registar? O botão + de cada prato dele/dela copia-o de imediato para o teu diário.",
                },
            },
            {
                "type": "nuevo",
                "title": {
                    "es": "Tu color de identidad",
                    "en": "Your identity color",
                    "pt": "A tua cor de identidade",
                },
                "desc": {
                    "es": "Elige tu color en el perfil: es el aro de tu avatar y el tono con el que te ve tu pareja. Sus calorías nunca se suman a tus totales.",
                    "en": "Pick your color in your profile: it's the ring around your avatar and the shade your partner sees you in. Their calories are never added to your totals.",
                    "pt": "Escolhe a tua cor no perfil: é o anel do teu avatar e o tom com que o teu par te vê. As calorias dele/dela nunca se somam aos teus totais.",
                },
            },
        ],
    },
    "1.9": {
        "title": {
            "es": "uroboros habla inglés y portugués",
            "en": "uroboros speaks English and Portuguese",
            "pt": "O uroboros fala inglês e português",
        },
        "items": [
            {
                "type": "nuevo",
                "title": {
                    "es": "Elige tu idioma",
                    "en": "Choose your language",
                    "pt": "Escolhe o teu idioma",
                },
                "desc": {
                    "es": "Español, inglés y portugués. Lo encuentras en Ajustes → Idioma. La primera vez la app coge el idioma de tu móvil sola; si eliges uno a mano, se queda fijo.",
                    "en": "Spanish, English and Portuguese. Find it in Settings → Language. The first time, the app picks up your phone's language on its own; choose one by hand and it stays fixed.",
                    "pt": "Espanhol, inglês e português. Encontras em Definições → Idioma. Na primeira vez, a app segue o idioma do telemóvel sozinha; se escolheres um à mão, fica fixo.",
                },
            },
            {
                "type": "nuevo",
                "title": {
                    "es": "Fechas y números en tu idioma",
                    "en": "Dates and numbers in your language",
                    "pt": "Datas e números no teu idioma",
                },
                "desc": {
                    "es": "El calendario, los días de la semana y los meses ya no están en español a la fuerza: se adaptan al idioma que tengas puesto.",
                    "en": "The calendar, weekdays and months are no longer forced into Spanish — they adapt to whichever language you've set.",
                    "pt": "O calendário, os dias da semana e os meses já não estão à força em espanhol: adaptam-se ao idioma que tiveres definido.",
                },
            },
            {
                "type": "mejora",
                "title": {
                    "es": "La página de invitación, traducida",
                    "en": "The invite page, translated",
                    "pt": "A página de convite, traduzida",
                },
                "desc": {
                    "es": "El enlace que compartes con quien quieras invitar detecta el idioma de su navegador y se muestra en inglés o portugués si toca.",
                    "en": "The link you share to invite someone detects their browser's language and shows up in English or Portuguese when it fits.",
                    "pt": "O link que partilhas para convidar alguém deteta o idioma do navegador dele/dela e mostra-se em inglês ou português quando for o caso.",
                },
            },
            {
                "type": "mejora",
                "title": {
                    "es": "Widgets de Android traducidos",
                    "en": "Android widgets, translated",
                    "pt": "Widgets do Android traduzidos",
                },
                "desc": {
                    "es": "Los accesos rápidos de la pantalla de inicio siguen el idioma del sistema.",
                    "en": "The home screen shortcuts follow your system language.",
                    "pt": "Os atalhos do ecrã principal seguem o idioma do sistema.",
                },
            },
        ],
    },
    "1.10": {
        "title": {
            "es": "Copia una comida de otro día",
            "en": "Copy a meal from another day",
            "pt": "Copia uma refeição de outro dia",
        },
        "items": [
            {
                "type": "nuevo",
                "title": {
                    "es": "Repite una comida de un día anterior",
                    "en": "Repeat a meal from a previous day",
                    "pt": "Repete uma refeição de um dia anterior",
                },
                "desc": {
                    "es": "Al mirar un día pasado, cada comida tiene un botón para copiarla a hoy tal cual. Útil cuando vuelves a comer algo que ya registraste hace unos días.",
                    "en": "Looking at a past day, every meal has a button to copy it into today as-is. Handy when you eat something again that you already logged a few days back.",
                    "pt": "Ao ver um dia passado, cada refeição tem um botão para a copiar para hoje tal como está. Útil quando voltas a comer algo que já registaste há uns dias.",
                },
            },
            {
                "type": "mejora",
                "title": {
                    "es": "Iconos más claros en el diario",
                    "en": "Clearer icons in the diary",
                    "pt": "Ícones mais claros no diário",
                },
                "desc": {
                    "es": "Los botones de copiar, guardar como receta y vaciar comida pasan a iconos, así no se corta el texto en pantallas estrechas.",
                    "en": "The copy, save-as-recipe and clear-meal buttons switch to icons, so the text no longer wraps on narrow screens.",
                    "pt": "Os botões de copiar, guardar como receita e esvaziar refeição passam a ícones, para o texto não cortar em ecrãs estreitos.",
                },
            },
            {
                "type": "mejora",
                "title": {
                    "es": "El icono de Recetas, coherente",
                    "en": "The Recipes icon, made consistent",
                    "pt": "O ícone de Receitas, coerente",
                },
                "desc": {
                    "es": "El mismo libro se usa ahora en la barra de navegación y en el menú lateral.",
                    "en": "The same book icon is now used in both the bottom navigation and the sidebar menu.",
                    "pt": "O mesmo ícone de livro é agora usado na barra de navegação e no menu lateral.",
                },
            },
            {
                "type": "nuevo",
                "title": {
                    "es": "Widgets en la pantalla de inicio (Android)",
                    "en": "Home screen widgets (Android)",
                    "pt": "Widgets no ecrã principal (Android)",
                },
                "desc": {
                    "es": "Acceso rápido para apuntar comida y un widget con código QR para invitar, directo desde el escritorio del móvil.",
                    "en": "Quick access to log food and a QR-code widget for invites, straight from your phone's home screen.",
                    "pt": "Acesso rápido para registar comida e um widget com código QR para convidar, diretamente do ecrã principal do telemóvel.",
                },
            },
        ],
    },
}

# ── Contenido original en español, para el downgrade ────────────────────────
_ORIGINAL_ES_TITLE = {v: data["title"]["es"] for v, data in _NOTES.items()}


def _strip_to_es(items: list[dict]) -> list[dict]:
    return [
        {**it, "title": it["title"]["es"], "desc": it["desc"]["es"]}
        for it in items
    ]


def upgrade() -> None:
    conn = op.get_bind()

    # 1. title: VARCHAR -> JSON. to_json() of the existing plain string turns
    # it into a JSON string scalar first; the UPDATE below then replaces it
    # with the {es, en, pt} object.
    op.execute("ALTER TABLE release_notes ALTER COLUMN title TYPE JSON USING to_json(title)")

    # 2. Translate content for the 6 notes already published.
    for version, data in _NOTES.items():
        conn.execute(
            sa.text(
                "UPDATE release_notes SET title = CAST(:title AS JSON), "
                "items = CAST(:items AS JSON) WHERE version = :version"
            ),
            {
                "title": json.dumps(data["title"]),
                "items": json.dumps(data["items"]),
                "version": version,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()

    # Revert content to the original plain-Spanish shape first...
    for version, data in _NOTES.items():
        conn.execute(
            sa.text(
                "UPDATE release_notes SET title = CAST(:title AS JSON), "
                "items = CAST(:items AS JSON) WHERE version = :version"
            ),
            {
                "title": json.dumps(_ORIGINAL_ES_TITLE[version]),
                "items": json.dumps(_strip_to_es(data["items"])),
                "version": version,
            },
        )

    # ...then shrink the column back to VARCHAR(120).
    op.execute("ALTER TABLE release_notes ALTER COLUMN title TYPE VARCHAR(120) USING title #>> '{}'")
