# Plan — Ver el día de la pareja en tu propio diario

> Origen: idea de sesión 2026-07-22. En el diario, un **chip compacto** de la pareja que
> resume su día (kcal + proteína) y, al activarlo, **intercala sus comidas** entre las tuyas
> por hora, en solo-lectura y con su color/avatar. Complementa —no sustituye— a
> `PLAN_pareja_en_editar.md` (aquello era acción por-producto en el modal; esto es la vista
> panorámica del día).
>
> **Se shipea todo junto en una sola update, subiendo versión (1.7 → 1.8).** Sin fases.

---

## 1. Qué se quiere

Con pareja (permiso household, mismo `_can_log_for_user` que ya usamos):

1. **Chip** arriba del diario, junto a "↩ Igual que ayer": avatar real de la pareja + su
   nombre + **resumen del día** (`1.240 kc · 61 P`). Visible aunque no despliegues nada;
   así sabes cómo va sin ver qué comió. Oculto si no tienes pareja.
2. **Toca el chip** → sus comidas se **intercalan por hora** dentro de cada comida
   (Desayuno/Almuerzo/Cena/Snack), con fondo/borde de su color, su avatar y etiqueta con su
   nombre. **Solo lectura** (sin la × de borrar). Vuelve a tocarlo → se ocultan.
3. Sus kcal **NO se suman a tus totales**. Tu "694 kcal · P66" sigue siendo tuyo. Debajo,
   una línea `Pilar: 320 kcal` por comida, **solo cuando el chip está activo**.
4. En cada plato suyo, un botón **＋ "ponérmelo a mí también"** → crea esa entrada en TU
   diario (mismo producto, gramos y comida). Reutiliza `POST /diary`.
5. **Color de identidad por usuario** (elegible en el perfil, paleta curada): es el aro del
   avatar + el tinte de sus platos. Reutiliza la prop `ring` del componente `Avatar`.

El estado on/off del chip se **recuerda** (localStorage).

---

## 2. Cómo funciona hoy (contexto)

- `GET /diary/day` agrupa por comida y devuelve `entries` + `meals` + `totals`. **Solo lee
  `user.id`**, no acepta `user_id`. [backend/app/routers/diary.py:354](backend/app/routers/diary.py#L354).
- Permiso household ya existe: `_can_log_for_user` (kind==partner + opt-in).
  [backend/app/routers/diary.py:102](backend/app/routers/diary.py#L102).
- `User` tiene `avatar_id` (slug de preset, null→disco con inicial).
  [backend/app/models/user.py:21](backend/app/models/user.py#L21).
- `Avatar.svelte` ya deriva un hue del nombre cuando no hay preset, y **ya tiene prop `ring`**.
  [frontend/src/lib/components/Avatar.svelte:17](frontend/src/lib/components/Avatar.svelte#L17).
- La lista de amigos ya devuelve `avatar_id` por amigo.
  [backend/app/schemas/friendship.py:13](backend/app/schemas/friendship.py#L13).
- Versión actual **1.7**. [frontend/src/lib/changelog.ts:5](frontend/src/lib/changelog.ts#L5).

---

## 3. Modelo de color: `identity_hue` (int, nullable)

- Nueva columna `User.identity_hue: int | None`. **Null ⇒ se usa el hue que el `Avatar` ya
  deriva del nombre** (comportamiento actual, cero ruptura, cero backfill).
- Paleta curada de 6 hues, **sin verde ni ámbar** (chocan con `--primary`/objetivos y
  `--cal`/kcal) ni rojo (choca con borrar/grasa): `320, 350, 290, 265, 235, 195`.
- El color que ves en tu diario es el **del otro** (pintas sus platos), no el tuyo. Igual
  que los avatares.

---

## 4. Cambios técnicos

### Backend
1. **Modelo + migración 0042**: `User.identity_hue` (Integer, nullable). Sin backfill.
2. **`GET /diary/day`**: añadir `user_id: int | None = Query(None)`. Si viene y != user.id →
   `_can_log_for_user` o 403; leer el día de ese usuario. Mantener el gate premium sobre el
   ACTOR (el que consulta), no sobre la pareja. Hoy es siempre "hoy", no toca historial.
3. **Schemas**: exponer `identity_hue` en el usuario propio ([auth.py:19](backend/app/schemas/auth.py#L19),
   junto a `avatar_id`) y en la ficha de amigo ([friendship.py:13](backend/app/schemas/friendship.py#L13)).
4. **Endpoint de guardado**: aceptar `identity_hue` donde ya se guarda `avatar_id` (perfil/
   ajustes). Validar contra la paleta permitida; fuera de ella → 422.

### Frontend
5. **Perfil/Ajustes**: selector de color (6 swatches) junto al de avatar. Guarda `identity_hue`.
6. **Componente chip** (`+page.svelte` o extraído): avatar de la pareja con `ring` de su
   color + nombre + `kc · P` del día. Estado on/off en localStorage (`uro_show_partner`).
   Oculto si no hay pareja. Al montar, si está on, pide el día de la pareja.
7. **Datos de la pareja**: obtener su `id`, `name`, `avatar_id`, `identity_hue` (de la lista
   de amigos, `kind==='partner'`) y su día vía `GET /diary/day?user_id=<id>`.
8. **Intercalado**: fusionar sus entries en los grupos de comida del diario, ordenando por
   `consumed_at`. Render `pentry` read-only (avatar + ring + tinte + tag nombre, sin ×).
9. **Totales**: NO sumar sus kcal a los tuyos. Línea `Pilar: X kcal` por comida solo con el
   chip activo. (Si una comida solo la tiene la pareja, la cabecera sale con tu total a 0.)
10. **＋ copiar a mí**: en cada plato suyo, `POST /diary` con su `product_id`, `grams` y
    `meal_type`. Refrescar el día. Mantener soporte offline/`syncQueue` como el resto.

### Versión
11. `APP_VERSION` 1.7 → **1.8** + nota de versión (major). Actualizar `changelog.ts` y la
    migración de seed de nota si aplica (patrón `00XX_seed_release_note_1_8.py`).

---

## 5. Tests
- `GET /diary/day?user_id=<pareja>` con permiso → 200 con su día; sin permiso → 403.
- `identity_hue` fuera de la paleta → 422; dentro → se guarda y se expone.
- Copiar a mí (`POST /diary` desde un plato de la pareja) crea SOLO mi entrada, no toca la suya.

## 6. Orden de trabajo
1. Backend: `identity_hue` (modelo + migración + schemas + guardado + validación).
2. Backend: `user_id` en `/diary/day` + guard.
3. Frontend: selector de color en perfil/ajustes.
4. Frontend: chip (avatar+resumen) + estado en localStorage + fetch pareja.
5. Frontend: intercalado read-only + línea por comida (sin sumar).
6. Frontend: botón ＋ copiar a mí.
7. Verificar en preview (demo + pareja). 8. Subir a 1.8 + nota. 9. Tests.

## 7. Estado
- Diseño acordado y validado con mockups (2026-07-22): `mockup-pilar-compacto.html` es el
  bueno (chip con resumen + intercalado + color/avatar). Descartados: tira al final
  (`mockup-pilar-en-diario.html`) y fila-toggle grande (`mockup-pilar-intercalada.html`).
- **IMPLEMENTADO (2026-07-22), sin commitear ni desplegar.** Todo en 1.8.
  - Backend: `User.identity_hue` (migración **0042**, idempotente Postgres + patch SQLite dev
    en `database.py`); `GET /diary/day` acepta `user_id` con guard `_can_log_for_user`;
    `PATCH /users/me/identity-color` (valida paleta `IDENTITY_HUES` en `app/avatars.py`);
    `identity_hue` expuesto en `UserOut`, `UserMinimal` y `/users/{id}/profile`.
  - Frontend: chip de pareja + resumen (kc·P) + intercalado read-only por hora + línea
    "Pilar: X kcal" por comida (solo con chip on) + botón ＋ copiar a mí, todo en
    `routes/+page.svelte`. Estado en `localStorage('uro_show_partner')`. Selector de color
    en `routes/profile/+page.svelte`. Helpers `nameHue`/`identityColor`/`IDENTITY_HUES` en
    `lib/avatars.ts`; `Avatar.svelte` acepta prop `identityHue`. `APP_VERSION`→1.8.
  - Nota de versión: migración **0043** (major).
  - Tests: `tests/test_partner_diary.py` (9, en verde). Suite completa 48/48. `svelte-check`
    sin errores nuevos en los archivos tocados.
- **VERIFICADO en preview local (2026-07-22)** con demo + Pilar como pareja (hubo que poner
  `kind='partner'` a mano en la BD demo: la siembra la crea como `friend`). Comprobado:
  chip con su resumen, intercalado por hora, sus kcal fuera de tus totales, tarjeta única
  "Los dos" al compartir producto, botón ＋ (copia con su hora y la tarjeta pasa a compartida)
  y toggle que oculta todo lo suyo dejando el resumen. Sin errores de consola.
- **Ajustes post-verificación** (commit `e1dc640`): chip + "Igual que ayer" en la misma fila;
  deduplicado de lo compartido; ＋ hereda la hora; gramos redondeados.
- **PENDIENTE DESPLEGAR:** `alembic upgrade head` aplica **0042-0043** (backup antes; 0042
  toca `users`). Rebuild frontend + restart backend. Subir `APP_VERSION` ya hecho en el
  código; recordar el paso de la PWA/changelog como en despliegues anteriores.
