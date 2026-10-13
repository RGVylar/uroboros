"""Seed the release note for 1.32 (ollas y bebidas en mililitros)

Revision ID: 0088
Revises: 0087
Create Date: 2026-10-13

Data migration, misma forma que 0085. Va como `major`: las ollas son una
forma nueva de apuntar.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0088"
down_revision = "0087"
branch_labels = None
depends_on = None

_release_notes = sa.table(
    "release_notes",
    sa.column("version", sa.String),
    sa.column("title", sa.JSON),
    sa.column("items", sa.JSON),
    sa.column("importance", sa.String),
    sa.column("published", sa.Boolean),
    sa.column("published_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    op.bulk_insert(_release_notes, [
        {
            "version": "1.32",
            "title": {
                "es": "Ollas para varios días",
                "en": "Pots for several days",
                "pt": "Panelas para vários dias",
            },
            "importance": "major",
            "published": True,
            "published_at": datetime.now(timezone.utc),
            "items": [
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Cocina una vez, apuntad varios días",
                        "en": "Cook once, log for days",
                        "pt": "Cozinha uma vez, registem vários dias",
                    },
                    "desc": {
                        "es": "En Recetas, haz una olla con lo que echas en crudo y para cuántas raciones da. Cada uno apunta sus raciones desde Añadir y la olla se va vaciando, con lo que ha comido cada uno en su color.",
                        "en": "In Recipes, make a pot with what goes in raw and how many servings it makes. Each of you logs servings from Add and the pot empties, with what each one ate in their colour.",
                        "pt": "Em Receitas, faz uma panela com o que pões cru e para quantas doses dá. Cada um regista as suas doses em Adicionar e a panela vai esvaziando, com o que cada um comeu na sua cor.",
                    },
                },
                {
                    "type": "nuevo",
                    "title": {
                        "es": "Y si la pesas, en gramos",
                        "en": "And in grams, if you weigh it",
                        "pt": "E em gramas, se a pesares",
                    },
                    "desc": {
                        "es": "Pesar la olla ya cocinada es opcional. Si lo haces, puedes apuntar tu plato en gramos y las cuentas salen bien aunque la pasta o el arroz pesen el doble al cocerse.",
                        "en": "Weighing the cooked pot is optional. If you do, you can log your plate in grams and the numbers stay right even though pasta or rice double in weight.",
                        "pt": "Pesar a panela já cozinhada é opcional. Se o fizeres, podes registar o teu prato em gramas e as contas batem certo mesmo que a massa ou o arroz pesem o dobro.",
                    },
                },
                {
                    "type": "mejora",
                    "title": {
                        "es": "Bebidas en mililitros, y atajos de envase",
                        "en": "Drinks in millilitres, and pack shortcuts",
                        "pt": "Bebidas em mililitros, e atalhos de embalagem",
                    },
                    "desc": {
                        "es": "Los productos escaneados saben si se miden en ml o en g. Cuando el producto lo dice, un toque pone la lata entera o una ración.",
                        "en": "Scanned products know whether they're measured in ml or g. When the product says so, one tap logs the whole can or a serving.",
                        "pt": "Os produtos digitalizados sabem se se medem em ml ou em g. Quando o produto o indica, um toque regista a lata inteira ou uma dose.",
                    },
                },
            ],
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM release_notes WHERE version = '1.32'")
