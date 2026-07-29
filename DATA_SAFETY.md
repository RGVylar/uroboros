# Data Safety — Uroboros (Google Play Console)

> Respuestas exactas para el formulario **Data safety** de Play Console, mapeadas
> al código real (modelos SQLAlchemy + servicios). Transcríbelas tal cual en
> `Play Console → App content → Data safety`.
>
> Última revisión: 2026-07-17 (repaso tras separar pareja de amigo; el formulario
> no cambia — ver la nota sobre compartir entre usuarios).

---

## Resumen de decisiones (lo que marca Google al principio)

| Pregunta del formulario | Respuesta |
|---|---|
| ¿Tu app recoge o comparte datos de usuario? | **Sí** |
| ¿Todos los datos están cifrados en tránsito? | **Sí** (HTTPS/TLS vía Caddy + Cloudflare) |
| ¿Ofreces forma de solicitar borrado de datos? | **Sí** — desde la app (`Ajustes → Eliminar cuenta`, `DELETE /users/me`) |

---

## Datos que SE RECOGEN

Para cada tipo: *Collected = Sí*. Ninguno se marca como "processed ephemerally"
(se persisten en PostgreSQL). Marca **Sí** en "Is this data required?" salvo donde
se indique opcional.

### Personal info
| Tipo de dato | ¿Recogido? | ¿Compartido? | Propósito | Origen en el código |
|---|---|---|---|---|
| **Name** | Sí (requerido) | No* | App functionality, Account management | `User.name` |
| **Email address** | Sí (requerido) | No* | App functionality, Account management | `User.email` |
| **User IDs** | Sí | No | App functionality | `User.id` (JWT `sub`) |

### Photos and videos  ← **cambió el 2026-07-29, hay que reenviar el formulario**
| Tipo de dato | ¿Recogido? | ¿Compartido? | Propósito | Origen en el código |
|---|---|---|---|---|
| **Photos** | Sí (**opcional**) | No | App functionality (foto de perfil) | `User.avatar_photo` |

> Marca **"Is this data required?" → No**: la foto es opcional y hay 18 avatares
> predefinidos como alternativa.
>
> **No** se marca como *shared*: solo la ven las personas cuya solicitud has
> aceptado, y eso es una transferencia nacida de una acción explícita del usuario
> (misma lógica que el resto de lo compartido, ver la nota más abajo).
>
> Lo que se guarda **no es el fichero que sube el usuario**: se reencodea a WebP
> 256×256 y se descarta el original con todo su EXIF, incluido el GPS
> ([avatar_photo_service.py](backend/app/services/avatar_photo_service.py)). Esto
> es lo que permite seguir marcando **Location → NO recogida** aunque ahora se
> acepten fotos de móvil.

\* Ver nota sobre Telegram/Resend más abajo — técnicamente el email/nombre salen a
proveedores como encargados del tratamiento; Google lo considera "processing", no
"sharing", si es solo para operar el servicio. Ver sección "Terceros".

### Health and fitness  ← **categoría sensible, revísala con cuidado**
| Tipo de dato | ¿Recogido? | Propósito | Origen |
|---|---|---|---|
| **Health info** | Sí | App functionality | Peso (`WeightLog`), medidas corporales (`BodyMeasurementLog`), alergias (`UserAllergy`), suplementos (`UserSupplement`/`SupplementLog`), creatina (`CreatineLog`), estado de ánimo/energía/digestión (`MoodEntry`) |
| **Fitness info** | Sí | App functionality | Calorías/macros y comidas (`DiaryEntry`), agua (`WaterLog`), sesiones de ejercicio (`ExerciseSession`), cheat days (`CheatDayLog`) |

### App activity
| Tipo de dato | ¿Recogido? | Propósito | Origen |
|---|---|---|---|
| **Other user-generated content** | Sí | App functionality | Recetas (`Recipe`), inventario/despensa (`InventoryItem`), lista de la compra (`ShoppingListItem`), notas de ánimo |
| **Other actions** (social) | Sí | App functionality | Relación con otra persona (`Friendship.kind`: pareja o amigo) y los permisos que cada lado activa dentro de ella |

> **Sobre compartir entre usuarios** (recetas por círculo, despensa con la pareja,
> alergias con quien puede apuntarte comida, % de adherencia en el duelo): no se
> declara como *shared*. En este formulario "shared" es ceder datos a un tercero
> para sus fines; Google exceptúa expresamente las transferencias que nacen de una
> acción explícita del usuario, y aquí nada se comparte sin que ambas partes lo
> activen. Se queda en *collected*, como está arriba.

### App info and performance
| Tipo de dato | ¿Recogido? | Propósito | Origen |
|---|---|---|---|
| **Crash logs / Diagnostics** | Sí | App functionality (monitoring) | Alertas a Telegram con método/ruta/stack trace en errores 500 (`telegram_alerts.send_error_alert`). **No** incluye contenido del usuario, sí la ruta. |

### Device or other IDs
| Tipo de dato | ¿Recogido? | Propósito | Origen |
|---|---|---|---|
| **Device or other IDs** | Sí | App functionality (notificaciones) | Endpoint de Web Push + `user_agent` del dispositivo (`PushSubscription`). La IP del cliente se procesa para rate limiting (`CF-Connecting-IP`) pero no se almacena de forma persistente. |

---

## Datos que NO se recogen (déjalos SIN marcar)

- **Location** (precisa o aproximada) — la app no pide permiso de ubicación. La zona
  horaria (`NotificationPrefs.timezone`, IANA) NO es ubicación.
- **Financial info** — no hay pagos implementados aún. Cuando se active Google Play
  Billing, Google gestiona el pago y **no** debes declararlo aquí como recogido por ti.
- ~~**Photos and videos**~~ — **ya no aplica**: desde 2026-07-29 hay foto de perfil
  opcional, declarada arriba. La cámara sigue usándose además para escanear códigos
  de barras en tiempo real, y de eso no se almacena ninguna imagen.
- **Contacts, Calendar, SMS, Call logs, Audio, Files** — no se accede.
- **Web browsing history, Search history** — no.

---

## Prácticas de seguridad (sección "Security practices")

| Pregunta | Respuesta | Justificación |
|---|---|---|
| Data encrypted in transit | **Sí** | Todo el tráfico va por HTTPS (Caddy + Cloudflare Tunnel). |
| Users can request data deletion | **Sí** | `Ajustes → Eliminar cuenta` borra en cascada todos los datos (`DELETE /users/me`, [users.py](backend/app/routers/users.py)). |
| Committed to Play Families Policy | No aplica (no dirigida a menores) | |
| Independent security review | No | (opcional; no lo tienes) |

> Contraseñas: bcrypt (12 rounds), nunca en texto plano. No es una pregunta directa
> del formulario pero refuerza la sección de seguridad si te la piden.

---

## Terceros que reciben datos (para tu control interno y coherencia con la Privacy Policy)

El formulario distingue "collected" (lo procesas tú/tus encargados) de "shared"
(se cede a un tercero para sus propios fines). En Uroboros **nadie recibe datos para
fines propios**, pero estos encargados procesan datos en tu nombre:

| Tercero | Qué recibe | Para qué | Nota |
|---|---|---|---|
| **Open Food Facts** | Código de barras escaneado | Buscar el producto | No se envían datos personales, solo el código. |
| **Resend** | Email del usuario | Enviar el correo de "recuperar contraseña" | Encargado del tratamiento (ya en tu Privacy Policy). |
| **Cloudflare** | IP + tráfico | Proxy/TLS/túnel | Encargado de infraestructura. |
| **Telegram** | **Nombre + email en cada registro**; IP en brute-force; rutas en errores 500 | Alertas de operación al admin | ⚠️ Ver aviso abajo. |

### ⚠️ Aviso sobre Telegram (recomendación, no bloquea el formulario)

`send_new_user_alert` envía **nombre + email del usuario** a los servidores de
Telegram (fuera de la UE) en cada alta ([auth.py:48](backend/app/routers/auth.py),
[telegram_alerts.py:55](backend/app/services/telegram_alerts.py)). Es una
transferencia de dato personal a un tercero no mencionado en tu Privacy Policy, que
sí dice *"no se transfieren a terceros países"*. Dos opciones para quedar coherente:

1. **Recomendado:** no enviar el email en la alerta (basta con "nuevo usuario, total N")
   o enviar el email ofuscado (`u***@dominio`). Elimina el problema de raíz.
2. Añadir Telegram como encargado + transferencia internacional en la Privacy Policy.

---

## Checklist antes de enviar el formulario

- [ ] Marcar Health info y Fitness info (lo más fácil de olvidar y lo más sensible).
- [ ] **Marcar Photos** (nuevo, opcional) y confirmar que sigue SIN marcarse Location:
      el reencodeo borra el GPS, por eso una cosa no arrastra la otra.
- [ ] Confirmar "encrypted in transit = Sí" y "deletion available = Sí".
- [ ] NO marcar Location ni Financial.
- [ ] URL de Privacy Policy publicada (`https://comida.mugrelore.com/privacy`).
- [ ] Resolver el aviso de Telegram (opción 1 recomendada) antes de publicar en abierto.

---

## Contenido generado por usuarios (política aparte del formulario)

Desde que hay foto de perfil, una persona puede enseñarle una imagen a otra, y eso
activa de lleno la **User Generated Content policy** de Play. Lo que exige y dónde
está resuelto:

| Requisito de Play | Estado |
|---|---|
| Mecanismo de denuncia dentro de la app | ✅ `POST /friends/{id}/report` + botón en la pantalla de Amigos |
| Poder bloquear a otro usuario | ✅ la denuncia bloquea; `Friendship.blocked_by` impide volver a solicitar |
| Moderación del contenido | ⚠️ **manual**: cada foto subida llega al chat de admin con miniatura (`send_avatar_photo_alert`). Escala hasta unas pocas subidas al día, no más. |

> La foto **no se muestra en solicitudes pendientes**, solo entre relaciones
> aceptadas. La regla vive en un `model_validator` de `FriendshipOut`, no repartida
> por los endpoints, para que no se pueda olvidar al añadir uno nuevo.
