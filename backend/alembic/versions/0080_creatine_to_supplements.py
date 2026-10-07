"""Creatina → suplemento normal

Revision ID: 0080
Revises: 0079
Create Date: 2026-10-07

El módulo de creatina era el antecesor de la lista de suplementos y hacía lo
mismo con un solo elemento. Quien lo tenía encendido o tiene días marcados
recibe un suplemento "Creatina" (o reutiliza el suyo si ya se llamaba así)
con esos días copiados a supplement_logs, y se le enciende el módulo de
suplementos para que lo vea. Después se apaga track_creatine.

La tabla creatine_logs y los endpoints /creatine se quedan: las APK viejas
aún pueden llamarlos.
"""

from alembic import op
import sqlalchemy as sa

revision = "0080"
down_revision = "0079"
branch_labels = None
depends_on = None

_users = sa.table("users", sa.column("id", sa.Integer), sa.column("modules", sa.JSON))


def upgrade() -> None:
    bind = op.get_bind()
    user_ids = {
        row[0]
        for row in bind.execute(sa.text(
            "SELECT user_id FROM user_goals WHERE track_creatine "
            "UNION SELECT DISTINCT user_id FROM creatine_logs"
        ))
    }

    for uid in sorted(user_ids):
        supp_id = bind.execute(sa.text(
            "SELECT id FROM user_supplements WHERE user_id = :u AND lower(name) LIKE 'creat%' "
            "ORDER BY id LIMIT 1"
        ), {"u": uid}).scalar()
        if supp_id is None:
            position = bind.execute(sa.text(
                "SELECT COALESCE(MAX(position), -1) + 1 FROM user_supplements WHERE user_id = :u"
            ), {"u": uid}).scalar()
            bind.execute(sa.text(
                "INSERT INTO user_supplements (user_id, name, position) VALUES (:u, 'Creatina', :p)"
            ), {"u": uid, "p": position})
            supp_id = bind.execute(sa.text(
                "SELECT MAX(id) FROM user_supplements WHERE user_id = :u AND name = 'Creatina'"
            ), {"u": uid}).scalar()

        bind.execute(sa.text(
            "INSERT INTO supplement_logs (user_id, supplement_id, logged_date) "
            "SELECT c.user_id, :s, c.logged_date FROM creatine_logs c "
            "WHERE c.user_id = :u AND NOT EXISTS ("
            "  SELECT 1 FROM supplement_logs l "
            "  WHERE l.user_id = c.user_id AND l.supplement_id = :s AND l.logged_date = c.logged_date)"
        ), {"u": uid, "s": supp_id})

        # Columna JSON: se lee, se cambia y se escribe entera.
        modules = bind.execute(sa.select(_users.c.modules).where(_users.c.id == uid)).scalar() or {}
        if modules.get("supplements") is False:
            bind.execute(_users.update().where(_users.c.id == uid).values(modules={**modules, "supplements": True}))

    bind.execute(sa.text("UPDATE user_goals SET track_creatine = false WHERE track_creatine"))


def downgrade() -> None:
    # Los suplementos creados ya son del usuario; no se deshacen.
    pass
