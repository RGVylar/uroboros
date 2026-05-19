# Plan de Publicación en Play Store - Uroboros

**Última actualización:** 2026-05-18  
**Estado:** 5 bloqueantes identificados, en progreso

---

## 🔴 Bloqueantes (Critical Path)

### 1. JWT_SECRET en Producción
**Ubicación:** `backend/app/config.py`  
**Estado:** ❌ BLOQUEANTE  
**Acción:**
- [ ] Cambiar `JWT_SECRET = "change-me-in-production"` a un valor aleatorio seguro (32+ chars)
- [ ] Usar variable de entorno en producción: `JWT_SECRET = os.environ.get('JWT_SECRET', ...)`
- [ ] Verificar que `crypto.py` use bcrypt 12 rounds (está correcto)
- [ ] Test: login/register funciona con la nueva secret

**Estimado:** 30 min

---

### 2. Terms of Service Faltante
**Ubicación:** Frontend (nueva ruta `/terms`)  
**Estado:** ✅ HECHO (2026-05-19)  
**Acción:**
- [x] Crear página `frontend/src/routes/terms/+page.svelte`
- [x] Incluir: derechos, uso aceptable, aviso médico, limitación de responsabilidad, jurisdicción ES
- [x] Enlazar desde Settings (pie de página)
- [x] Enlazar desde login (legal small print al crear cuenta + footer)
- [ ] Legal review humana (recomendado, no bloqueante para internal testing)

**Estimado:** 2-3 horas → **completado**

---

### 3. Backups de PostgreSQL
**Ubicación:** Infraestructura (comida.mugrelore.com)  
**Estado:** ❌ BLOQUEANTE  
**Acción:**
- [ ] Configurar backup automático diario:
  - `pg_dump` + almacenar en S3 o Google Cloud Storage
  - O usar Heroku Postgres Backups (si está en Heroku)
  - O cron job en el servidor: `0 2 * * * pg_dump ... | gzip > /backups/uroboros-$(date +\%Y\%m\%d).sql.gz`
- [ ] Retener 30 días de backups
- [ ] Test: restaurar un backup en ambiente de test
- [ ] Documentar procedimiento de recuperación

**Estimado:** 1-2 horas

---

### 4. Rate Limiting en Auth
**Ubicación:** `backend/app/routers/auth.py`  
**Estado:** ❌ BLOQUEANTE  
**Acción:**
- [ ] Instalar `slowapi` o `python-ratelimit`
- [ ] Aplicar límite a:
  - `POST /auth/login`: 5 intentos / 15 min por IP
  - `POST /auth/register`: 3 registros / hora por IP
  - `POST /auth/forgot-password`: 2 intentos / 10 min por IP
- [ ] Retornar `429 Too Many Requests` cuando se exceda
- [ ] Log de intentos fallidos para auditoría
- [ ] Test: verificar que bloquea tras X intentos, permite tras reset

**Estimado:** 2 horas

---

### 5. Error Tracking (Sentry o Similar)
**Ubicación:** Frontend + Backend  
**Estado:** ❌ BLOQUEANTE  
**Acción:**
- [ ] Elegir proveedor: Sentry (recomendado, plan free tiene 5k eventos/mes)
- [ ] Backend:
  - Instalar `sentry-sdk[flask]`
  - Inicializar en `main.py`: `sentry_sdk.init(dsn="...")`
  - Capturar excepciones en middleware
- [ ] Frontend:
  - Instalar `@sentry/svelte`
  - Inicializar en `src/app.html` o `+layout.svelte`
- [ ] Configurar alertas (Slack/email si hay errores 5xx)
- [ ] Test: trigger error intencional y verificar que aparece en dashboard

**Estimado:** 1.5 horas

---

## ⚠️ Avisos Importantes (No Bloqueantes pero Recomendados)

### Dependencias Vulnerables
**Acción:**
```bash
cd frontend && npm audit fix
cd ../backend && pip audit
```
- [ ] Resolver 15 vulnerabilidades npm (9 high)
- [ ] Remover/actualizar: `@xmldom`, `devalue`, `minimatch`, `tar`
- [ ] Ejecutar audit nuevamente para verificar

**Estimado:** 1 hora

---

### ProGuard / Obfuscación
**Ubicación:** `android/app/build.gradle`  
**Acción:**
- [ ] Habilitar `minifyEnabled true` en release build
- [ ] Configurar `proguardFiles` para excluir Capacitor plugins
- [ ] Test: APK release construye sin errores

**Estimado:** 1 hora

---

### VITE_API_URL en Producción
**Ubicación:** Variables de entorno en pipeline  
**Acción:**
- [ ] Verificar que `VITE_API_URL=https://comida.mugrelore.com/api` en CI/CD
- [ ] Test: APK construido desde GitHub Actions se conecta al servidor correcto

**Estimado:** 30 min

---

### Icono y Assets
**Ubicación:** `android/app/src/main/res/mipmap-*`  
**Acción:**
- [ ] Verificar icono es 512×512px PNG sin transparencia
- [ ] Generar todas las densidades (hdpi, xhdpi, xxhdpi, xxxhdpi)
- [ ] Splash screen actualizado con branding final
- [ ] Play Store store listing images (2 screenshots mínimo)

**Estimado:** 2 horas

---

### Testing en Dispositivo Físico
**Acción:**
- [ ] Instalar APK release en dispositivo Android real (no emulador)
- [ ] Test paths críticos:
  - Login / Register
  - Onboarding (goals, notification modal)
  - Add food (camera, barcode scanner)
  - Settings (cambiar notificaciones, idioma)
  - Profile (editar datos)
  - Diary (agregar comidas, racha)
- [ ] Verificar notificaciones locales funcionan
- [ ] Verificar conexión a API con HTTPS
- [ ] Instalar 2+ veces para verificar updates

**Estimado:** 2 horas

---

## ✅ Verificación Pre-Envío

- [ ] Todos los 5 bloqueantes resueltos
- [ ] Build pasa sin errores/warnings
- [ ] `versionCode` incrementado (actualmente 1 → subir a 2 antes de Play)
- [ ] `versionName` actualizado (actualmente "1.0" → "1.0.0" o "0.1.0")
- [ ] Privacy Policy enlazada en Settings
- [ ] Terms of Service enlazada en Settings y login
- [ ] Copyright/Legal footer visible
- [ ] APK testado en 2+ dispositivos físicos
- [ ] Screenshot de Play Store review (mínimo 2)
- [ ] Descripción corta (<80 chars) y larga (descripción app)
- [ ] Icono Play Store (512×512px)

---

## 📅 Timeline Estimado

| Tarea | Horas | Responsable | Fecha |
|-------|-------|-------------|-------|
| JWT_SECRET + Rate Limiting | 2.5 | Backend | - |
| Terms of Service | 3 | Legal/Frontend | - |
| Backups PostgreSQL | 1.5 | DevOps | - |
| Error Tracking (Sentry) | 1.5 | Backend/Frontend | - |
| npm audit fix | 1 | Frontend | - |
| ProGuard + Testing | 2.5 | Android | - |
| **TOTAL BLOQUEANTES** | **12** | - | - |
| **Avisos + Preparación** | **8** | - | - |
| **TOTAL** | **20** | - | **~1 semana** |

---

## 🚀 Proceso de Publicación (después de resolver bloqueantes)

1. **Internal Testing** (1-3 días)
   - Enviar a Google Play Console (track: Internal Testing)
   - Esperar a que Google revise de seguridad
   - Testear en 5+ dispositivos Android reales

2. **Closed Testing / Alfa** (2 semanas opcional)
   - 10-20 beta testers externos
   - Recopilar feedback

3. **Production Release**
   - Cambiar de Internal Testing → Production
   - Google revisa nuevamente (24-48h típicamente)
   - Live en Play Store 🎉

---

## 📝 Notas

- **Cumplimiento regional:** La app maneja datos de salud → cumple GDPR + LSSI-CE (España)
- **Privacidad:** Ya existe Privacy Policy completa, solo falta Terms of Service
- **Seguridad:** Autenticación bcrypt + JWT está bien. El JWT_SECRET es el único problema criptográfico.
- **Escalabilidad:** PostgreSQL + FastAPI están listos para usuarios iniciales (100-1000 usuarios)

---

## 📊 Checklist Final

```
[  ] Bloqueante 1: JWT_SECRET seguro
[  ] Bloqueante 2: Terms of Service
[  ] Bloqueante 3: Backups PostgreSQL
[  ] Bloqueante 4: Rate Limiting Auth
[  ] Bloqueante 5: Error Tracking
[  ] npm audit fix completado
[  ] ProGuard habilitado
[  ] VITE_API_URL correcto
[  ] APK testado en dispositivo físico
[  ] Play Store console ready
[  ] Envío a Internal Testing
[  ] Aprobación de Google
[  ] Publicado en Play Store ✨
```

---

**Contacto:** Si algo no está claro, consultar la documentación de Google Play Console: https://play.google.com/console/developers
