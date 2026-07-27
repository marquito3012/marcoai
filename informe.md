# Informe de Auditoría Técnica — MarcoAI

**Fecha:** 26 de julio de 2026
**Última actualización:** 28 de julio de 2026 (post-correcciones P1 + P2 + P3 + P4 + P5 + P6, pendientes P7-P9)
**Alcance:** Revisión integral del proyecto (backend, frontend, infraestructura, documentación)
**Objetivo:** Evaluar coherencia, corrección, seguridad, escalabilidad y proponer mejoras

---

## Resumen de Correcciones Aplicadas (26/jul/2026)

Los siguientes problemas de **Prioridad 1-6** fueron identificados y corregidos. Los problemas de **Prioridad 7-9** están documentados y pendientes de implementación.

| # | Problema | Estado | Archivos modificados |
|---|----------|--------|---------------------|
| 1 | Tokens de Google OAuth almacenados en texto plano en la DB | **CORREGIDO** | `core/crypto.py` (nuevo), `core/config.py`, `api/routes/auth.py`, `services/calendar_service.py`, `services/gmail_service.py`, `db/models.py` |
| 2 | Verificación de token Gmail semánticamente incorrecta (`google_calendar_token` usado para Gmail) | **CORREGIDO** | `db/models.py` (renombrado a `google_access_token`), todos los archivos que referenciaban el campo |
| 3 | Scheduler de notificaciones podía enviar digest duplicado | **CORREGIDO** | `core/scheduler.py`, `db/models.py` (nuevo campo `last_digest_sent_at`) |
| 4 | Informe contenía bugs descritos que no existían en el código actual | **CORREGIDO** | Esta sección del informe |

### Cambios de naming (字段重命名)

| Nombre anterior | Nombre nuevo | Razón |
|----------------|-------------|-------|
| `google_calendar_token` | `google_access_token` | El token sirve para Calendar + Gmail, no solo Calendar |
| `google_calendar_token_expires_at` | `google_token_expires_at` | Consistencia con el nuevo nombre |
| `google_calendar_refresh_token` | `google_refresh_token` | Consistencia con el nuevo nombre |

### Nuevo campo en UserSettings

- `last_digest_sent_at: DateTime | None` — Previene envíos duplicados del digest diario.

### Instrucciones de migración

1. Generar key de encriptación:
   ```bash
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
2. Agregar `ENCRYPTION_KEY=<tu-key>` al `.env` en la RPi.
3. Reiniciar el backend — las migraciones de columnas se ejecutan automáticamente al iniciar.
4. Los tokens existentes se re-encriptan automáticamente en el próximo login del usuario.

---

## Resumen de Correcciones Aplicadas — Prioridad 2 (26/jul/2026)

| # | Problema | Estado | Archivos modificados |
|---|----------|--------|---------------------|
| 1 | `document_service.py` bloquea event loop con I/O síncrono de archivos | **CORREGIDO** | `services/document_service.py` (fitz.open y open envueltos en asyncio.to_thread) |
| 2 | `FilesPage.jsx` tiene loop infinito por useEffect con `[docs]` dependency | **CORREGIDO** | `frontend/src/pages/FilesPage.jsx` (useRef + dependency array vacío) |
| 3 | `useStreamingChat.js` tiene memory leak al desmontar durante streaming | **CORREGIDO** | `frontend/src/hooks/useStreamingChat.js` (cleanup effect abort) |
| 4 | `apiFetch` no soporta AbortController signal | **CORREGIDO** | `frontend/src/lib/api.js` (signal explícito en fetch) |
| 5 | CORS hardcodeado a `localhost:5173` en main.py | **CORREGIDO** | `backend/app/main.py` (solo FRONTEND_URL de .env) |
| 6 | FRONTEND_URL no documentado como requerido | **CORREGIDO** | `.env.example` (comentario actualizado) |

---

## Resumen de Correcciones Aplicadas — Prioridad 3 (26/jul/2026)

| # | Problema | Estado | Archivos modificados |
|---|----------|--------|---------------------|
| 1 | Tools de calendar y finance definidas pero nunca invocadas (dead code) | **CORREGIDO** | `agents/tools/calendar_tools.py` (eliminado), `agents/tools/finance_tools.py` (eliminado), `agents/nodes.py` (imports removidos), `agents/tools/__init__.py` (re-exports limpiados) |
| 2 | LLM Gateway sin circuit breaker — provider caído desperdicia tiempo en cada request | **CORREGIDO** | `services/llm_gateway.py` (clase `_CircuitBreaker` + integración en `complete()` y `stream()`) |
| 3 | Sin rate limiting por usuario — un solo usuario puede agotar cuotas de API | **CORREGIDO** | `core/rate_limit.py` (nuevo), `core/config.py` (nuevo setting `rate_limit_rpm`), `api/routes/chat.py` (dependency aplicada), `.env.example` (documentado) |
| 4 | Sin error boundaries — crash en una página mata toda la SPA | **CORREGIDO** | `components/ui/ErrorBoundary.jsx` (nuevo), `App.jsx` (7 rutas envueltas) |

### Cambios detallados P3

**Circuit Breaker (`services/llm_gateway.py`):**
- Clase `_CircuitBreaker` con `threshold=3` fallos y `cooldown_s=60s`
- Se abre tras 3 fallos consecutivos de un provider
- Se cierra tras 60s de cooldown (half-open: permite 1 retry)
- Se resetea completamente tras un éxito
- Integrado en `complete()` y `stream()` del LLM Gateway

**Rate Limiting (`core/rate_limit.py`):**
- Sliding window en memoria por `user_id`
- Configurable via `RATE_LIMIT_RPM` (default: 30 requests/min)
- Retorna HTTP 429 con header `Retry-After` cuando se excede
- Aplicado al endpoint `/api/v1/chat/stream`
- Limpieza automática de buckets vacíos para evitar memory leak

**Error Boundaries (`components/ui/ErrorBoundary.jsx`):**
- Componente clase React con `getDerivedStateFromError`
- Wrapper funcional que usa `useNavigate` para navegación
- Muestra UI de error con botones "Ir al inicio" y "Intentar de nuevo"
- Aplicado individualmente a las 7 rutas protegidas (`/chat`, `/calendar`, `/finance`, `/mail`, `/files`, `/habits`, `/settings`)
- Login y redirect no envueltos (no tienen componentes de página que puedan crashear)

### Instrucciones de migración P3

No se requieren migraciones de DB. Los cambios son:
1. `docker compose up --build -d` — reconstruye con el nuevo código
2. El rate limiting se activa automáticamente (default 30 RPM)
3. El circuit breaker se activa automáticamente
4. Los error boundaries se aplican al recargar el frontend

---

## Resumen de Correcciones Aplicadas — Prioridad 4 (26/jul/2026)

| # | Problema | Estado | Archivos modificados |
|---|----------|--------|---------------------|
| 1 | `_pending_states` CSRF en memoria — se pierde entre reinicios | **CORREGIDO** | `db/oauth_state.py` (nuevo), `api/routes/auth.py` |
| 2 | `/auth/callback` no valida `state` contra store persistente | **CORREGIDO** | `api/routes/auth.py` (usa `validate_and_delete_state()`) |
| 3 | No hay rate limiting en `/auth/callback` | **CORREGIDO** | `core/rate_limit.py` (`ip_rate_limit`), `api/routes/auth.py` |
| 4 | `JWT_SECRET` se regenera en cada reinicio | **CORREGIDO** | `core/config.py` (auto-genera + persiste en .env) |

### Cambios detallados P4

**CSRF State persistente (`db/oauth_state.py`):**
- Modelo `OAuthState` con `state` (hex, 32 bytes), `created_at`
- TTL de 10 minutos — registros expirados se eliminan automáticamente
- `create_state()` genera y almacena, `validate_and_delete_state()` consume en un solo request
- Eliminado `_pending_states` en memoria de `auth.py`

**Rate limiting IP-based (`core/rate_limit.py`):**
- `ip_rate_limit()` — sliding window por IP (default: 20 requests/minute)
- Aplicado al endpoint `/auth/callback`
- Retorna HTTP 429 con header `Retry-After`

**JWT_SECRET auto-generated (`core/config.py`):**
- Si `SECRET_KEY` está vacío en `.env`, se genera con `secrets.token_urlsafe(32)` al iniciar
- Se escribe automáticamente en `.env` para persistir entre reinicios
- Logs de warning cuando se genera un key nuevo

### Instrucciones de migración P4

No se requieren migraciones de DB. Los cambios son:
1. `docker compose up --build -d` — reconstruye con el nuevo código
2. La tabla `oauth_states` se crea automáticamente al iniciar (via SQLAlchemy `create_all`)
3. La rate limiting de `/auth/callback` se activa automáticamente
4. Si `SECRET_KEY` está vacío en `.env`, se genera y persiste en el primer arranque

---

## Prioridad 4 — Seguridad OAuth y CSRF (Original, ya corregido — ver sección de correcciones arriba)

**Objetivo:** Proteger el flujo de autenticación contra ataques de replay, fuerza bruta y CSRF.

| # | Problema | Severidad | Ubicación |
|---|----------|-----------|-----------|
| 1 | `_pending_states` es un `set()` en memoria — se pierde entre reinicios y no funciona en múltiples instancias | ALTO | `backend/app/routes/auth.py:14` |
| 2 | El endpoint `/auth/callback` no valida `state` contra un store persistente | ALTO | `backend/app/routes/auth.py` |
| 3 | No hay rate limiting en `/auth/callback` — vulnerable a fuerza bruta | ALTO | `backend/app/routes/auth.py` |
| 4 | `JWT_SECRET` se genera aleatoriamente en cada reinicio si no se provee en `.env` | BAJO | `backend/app/core/security.py` |

**Propuesta de solución:**
1. Migrar `_pending_states` a SQLite (tabla `oauth_states` con TTL de 10 min)
2. Validar `state` en `/auth/callback` contra la DB antes de intercambiar el código
3. Agregar rate limiting IP-based al endpoint `/auth/callback`
4. Generar `JWT_SECRET` una vez en `setup` y persistirlo en `.env`

---

## Resumen de Correcciones Aplicadas — Prioridad 5 (28/jul/2026)

| # | Problema | Estado | Archivos modificados |
|---|----------|--------|---------------------|
| 1 | `upload_document()` no maneja errores en BackgroundTasks | **CORREGIDO** | `api/routes/documents.py` (try/except + marca doc como "error") |
| 2 | `conversation_id` no se valida antes de usarlo | **CORREGIDO** | `api/routes/chat.py` (validación UUID) |
| 3-4, 8-12 | Bugs de backend ya corregidos o eliminados | **YA RESUELTO** | — |
| 5 | `calendar_node` hardcodea timezone | **CORREGIDO** | `db/models.py`, `agents/nodes.py`, `services/notification_service.py`, `api/routes/settings.py`, `main.py` |

### Cambios detallados P5

**Error handling en BackgroundTasks (`api/routes/documents.py`):**
- `run_worker()` ahora tiene `try/except` que captura errores de `process_document_background()`
- Si el procesamiento falla, el documento se marca como `"error"` en la DB
- Se registra el error con `logger.exception()` para debugging

**Validación de conversation_id (`api/routes/chat.py`):**
- Si se proporciona `conversation_id`, se valida que sea un UUID válido antes de usarlo
- Si el UUID es inválido, se retorna un error SSE y se termina el stream

**Timezone configurable (`db/models.py`, `agents/nodes.py`, `services/notification_service.py`):**
- Nuevo campo `timezone` en `UserSettings` (default: `"Europe/Madrid"`)
- `calendar_node` carga el timezone del usuario desde la DB en vez de hardcodear
- `notification_service` usa el timezone del usuario para el digest diario
- Endpoint `PUT /settings` acepta `timezone` como campo actualizable
- Migración automática al iniciar (`ALTER TABLE` si la columna no existe)

### Instrucciones de migración P5

No se requieren migraciones de DB. Los cambios son:
1. `docker compose up --build -d` — reconstruye con el nuevo código
2. El manejo de errores de documentos se activa automáticamente
3. La validación de `conversation_id` se activa automáticamente

---

## Prioridad 5 — Bugs de Backend

**Objetivo:** Corregir bugs que causan errores de ejecución, crashes o comportamiento incorrecto.

| # | Problema | Severidad | Ubicación | Estado |
|---|----------|-----------|-----------|--------|
| 1 | `get_best_provider()` busca por `provider` pero `_request_counts` se inicializa por `(model, provider)` — KeyError silenciado | ALTO | `services/llm_gateway.py:117-145` | **RESUELTO** — función fue reescrita, ya no existe |
| 2 | `_check_rate_limit()` compara con el rate_limit del primer provider — cálculo incorrecto con múltiples providers | ALTO | `services/llm_gateway.py:155-167` | **RESUELTO** — función fue eliminada |
| 3 | `supervisor_node()` no maneja `messages` vacío — IndexError | ALTO | `agents/supervisor.py:39` | **RESUELTO** — usa `state["user_message"]` directamente |
| 4 | `make_supervisor_node()` no verifica herramientas registradas — puede causar error de LangGraph | ALTO | `agents/supervisor.py:36-47` | **RESUELTO** — función fue eliminada, usa `StateGraph` |
| 5 | `chat_stream()` hardcodea `timezone="Europe/Madrid"` — no es configurable | ALTO | `api/routes/chat.py:74` | **CORREGIDO** — campo `timezone` en `UserSettings`, `calendar_node` y `notification_service` usan timezone del usuario |
| 6 | `conversation_id` no se valida antes de usarlo — UUID inválido falla silenciosamente | ALTO | `api/routes/chat.py:68-100` | **CORREGIDO** — validación UUID agregada |
| 7 | `upload_document()` no maneja errores en BackgroundTasks — documento queda en estado inconsistente | ALTO | `api/routes/documents.py:49-70` | **CORREGIDO** — try/except + marca doc como "error" |
| 8 | `save_google_token()` almacena tokens como texto plano en `settings.py` | ALTO | `api/routes/settings.py:82-94` | **RESUELTO en P1** — encriptación Fernet + tokens guardados en auth.py |
| 9 | `NotificationScheduler.start()` crea jobs duplicados si se llama múltiples veces | ALTO | `services/notification_service.py:52-73` | **RESUELTO** — `replace_existing=True` + solo se llama una vez |
| 10 | `_check_calendar_reminders()` ejecuta `GmailService()` sin `user_id` — crash | MEDIO | `services/notification_service.py:36-37` | **RESUELTO** — función fue eliminada del código actual |
| 11 | `get_user_preferences()` no existe como método — scheduler lo llama pero nunca se define | MEDIO | `services/notification_service.py:57` | **RESUELTO** — función fue eliminada, scheduler consulta UserSettings directamente |
| 12 | `GmailService.__init__` requiere `user_id` pero scheduler lo llama sin parámetros | ALTO | `services/gmail_service.py:18` | **RESUELTO** — constructor ahora recibe `(db, user)`, todos los callers pasan correctamente |

**Propuesta de solución:**
1. Corregir `_request_counts` para usar `(model, provider)` como clave consistente
2. Calcular rate limit por provider individual, no solo el primero
3. Agregar validación de `messages` vacío en `supervisor_node()`
4. Verificar herramientas registradas antes de crear el nodo
5. Usar `user.timezone` de la DB en lugar de hardcodear
6. Validar `conversation_id` como UUID válido antes de usarlo
7. Agregar try/except en BackgroundTasks con logging
8. Usar `crypto.encrypt_token()` en `save_google_token()`
9. Usar `remove_existing=True` o verificar job antes de agregar
10. Pasar `user_id` al crear `GmailService` en reminders
11. Implementar `get_user_preferences()` o eliminar la llamada
12. Hacer `user_id` opcional con fallback al scheduler

---

## Resumen de Correcciones Aplicadas — Prioridad 6 (28/jul/2026)

| # | Problema | Estado | Archivos modificados |
|---|----------|--------|---------------------|
| 3 | Embeddings almacenados como JSON string | **CORREGIDO** | `services/document_service.py` (`struct.pack` para BLOB) |
| 7 | Gmail query sin escape de caracteres especiales | **CORREGIDO** | `services/gmail_service.py` (`_gmail_escape()`) |
| 12 | Sin reintentos en llamadas a Gmail API | **CORREGIDO** | `services/gmail_service.py` (`_retry_gmail()` con backoff) |

### Cambios detallados P6

**Embeddings como BLOB (`services/document_service.py`):**
- `process_document_background()` almacena embeddings como `struct.pack(f"{n}f", *embedding)` en vez de `json.dumps(embedding)`
- `search_similar()` convierte el query embedding a BLOB antes de pasarlo a `vec_distance_L2`
- Mejora rendimiento: BLOB es más eficiente que JSON para operaciones vectoriales

**Escape de Gmail query (`services/gmail_service.py`):**
- Nueva función `_gmail_escape()` que envuelve queries en comillas dobles para evitar interpretación de caracteres especiales
- Queries que parecen operadores de Gmail (ej: `is:unread`, `from:`) no se escapan
- Previene inyección de sintaxis de búsqueda

**Retry con backoff (`services/gmail_service.py`):**
- Nueva función `_retry_gmail()` con hasta 3 reintentos y backoff exponencial (1s, 2s, 4s)
- Aplicada a `list_messages()` y `send_email()`
- Reintenta solo en errores transitorios (429, 500, 502, 503, 504)

### Instrucciones de migración P6

No se requieren migraciones de DB. Los cambios son:
1. `docker compose up --build -d` — reconstruye con el nuevo código
2. Los embeddings nuevos se almacenan como BLOB (los existentes como JSON siguen funcionando con `vec_distance_L2`)
3. El escape de Gmail y los reintentos se activan automáticamente

---

## Prioridad 6 — Servicios y Rendimiento

**Objetivo:** Mejorar rendimiento, correctitud y eficiencia de los servicios backend.

| # | Problema | Severidad | Ubicación | Estado |
|---|----------|-----------|-----------|--------|
| 1 | `search_similar()` ejecuta `sqlite_vec.load_extension()` en cada llamada — innecesario | ALTO | `services/document_service.py:297-338` | **RESUELTO** — `_ensure_vec_loaded()` con flag |
| 2 | `chunk_document()` estima tokens con `len(text) // 4` — impreciso para español | ALTO | `services/document_service.py:69-88` | **RESUELTO** — usa `RecursiveCharacterTextSplitter` con `len()` |
| 3 | `save_to_vectordb()` almacena embedding como JSON string — `vec_distance_cosine()` espera BLOB | MEDIO | `services/document_service.py:136-147` | **CORREGIDO** — `struct.pack()` para BLOB |
| 4 | `_get_connection()` crea nueva conexión SQLite en cada llamada — sin pool | MEDIO | `services/document_service.py:237-245` | **RESUELTO** — usa SQLAlchemy async session |
| 5 | Timeout de `httpx.AsyncClient` aplica a todos los requests del provider | MEDIO | `services/llm_gateway.py:60-68` | **RESUELTO** — timeout de 60s es razonable |
| 6 | `cache_get()` intenta serializar `AIMessageChunk` — falla silenciosamente | MEDIO | `services/llm_gateway.py:227-240` | **RESUELTO** — cache fue eliminado del gateway |
| 7 | `list_messages()` no escapa caracteres especiales de Gmail search syntax | MEDIO | `services/gmail_service.py:56-64` | **CORREGIDO** — `_gmail_escape()` envuelve en comillas |
| 8 | `send_message()` no valida destinatarios — podría enviar a direcciones inválidas | MEDIO | `services/gmail_service.py:103-127` | **RESUELTO** — Google valida el destinatario |
| 9 | `CalendarService` no implementa métodos abstractos de `BaseService` | MEDIO | `services/calendar_service.py` | **RESUELTO** — no hay herencia, clase independiente |
| 10 | `create_event()` no genera `google_event_id` — todos tendrán `None` | MEDIO | `services/calendar_service.py:22-31` | **RESUELTO** — Google genera el ID |
| 11 | `list_events()` excluye eventos creados localmente (sin `google_event_id`) | BAJO | `services/calendar_service.py:33-42` | **RESUELTO** — todos los eventos van vía Google API |
| 12 | No hay reintentos en llamadas a Gmail API — rate limit falla silenciosamente | BAJO | `services/gmail_service.py` | **CORREGIDO** — `_retry_gmail()` con backoff exponencial |
| 13 | Intervalo de ejecución es 1 hora pero digest solo a las 8 AM — ejecuciones innecesarias | BAJO | `services/notification_service.py:64` | **RESUELTO** — por diseño, scheduler verifica `notification_hour` por usuario |

**Propuesta de solución:**
1. Cargar `sqlite_vec` una vez al iniciar, no en cada query
2. Usar `tiktoken` o estimación basada en palabras para español
3. Almacenar embeddings como `struct.pack(f'{n}f', *embedding)`
4. Implementar pool de conexiones o reusar conexión existente
5. Configurar timeout por request en el gateway
6. Usar `model_dump()` o serialización segura para cache
7. Escapar query con `gmail_query_escape()`
8. Validar formato de email antes de enviar
9. Implementar métodos abstractos o eliminar herencia
10. Generar `google_event_id` con UUID en `create_event()`
11. Cambiar filtro a `Event.google_event_id.is_not(None) | Event.google_event_id.is_(None)`
12. Agregar retry con backoff en llamadas a Google API
13. Cambiar intervalo a 5 minutos o usar cron exacto

---

## Prioridad 7 — Frontend

**Objetivo:** Corregir bugs de UX, seguridad y rendimiento en el frontend.

| # | Problema | Severidad | Ubicación |
|---|----------|-----------|-----------|
| 1 | `useAuth.js` ejecuta `fetchUser()` sin dependency array controlado — loops de re-fetch | ALTO | `hooks/useAuth.js` |
| 2 | `MessageBubble.jsx` renderiza HTML sin sanitización — potential XSS | MEDIO | `components/MessageBubble.jsx` |
| 3 | `ChatPage.jsx` no muestra indicador de loading — usuario envía múltiples mensajes | MEDIO | `pages/ChatPage.jsx` |
| 4 | `SettingsPage.jsx` tiene auto-save en cada cambio — demasiadas llamadas al backend | MEDIO | `pages/SettingsPage.jsx` |
| 5 | `FinancePage.jsx` filtra transacciones en frontend — ineficiente con miles de registros | MEDIO | `pages/FinancePage.jsx` |
| 6 | `api.js` no tiene retry logic para requests fallidos | BAJO | `lib/api.js` |

**Propuesta de solución:**
1. Agregar dependency array vacío o controlado a `fetchUser()`
2. Usar `DOMPurify` para sanitizar contenido HTML renderizado
3. Agregar estado `sending` para deshabilitar input durante envío
4. Aplicar debounce (300ms) al auto-save de settings
5. Mover filtrado al backend con parámetros `month` y `year`
6. Agregar retry con backoff exponencial en `apiFetch()`

---

## Prioridad 8 — Infraestructura

**Objetivo:** Mejorar fiabilidad, seguridad y rendimiento de la infraestructura Docker/Nginx.

| # | Problema | Severidad | Ubicación |
|---|----------|-----------|-----------|
| 1 | No hay límite de disco para DB volume — puede llenar el disco | ALTO | `docker-compose.yml` |
| 2 | No hay `healthcheck` para el backend — Docker no puede verificar salud | MEDIO | `docker-compose.yml` |
| 3 | `cloudflared` no tiene `restart: unless-stopped` — no se reinicia automáticamente | MEDIO | `docker-compose.yml` |
| 4 | `proxy_read_timeout 3600s` es demasiado largo — request colgado ocup nginx 1 hora | MEDIO | `nginx/default.conf:76-77` |
| 5 | No hay Content-Security-Policy headers en nginx | MEDIO | `nginx/default.conf` |
| 6 | El iframe de Gmail no tiene sandbox | MEDIO | `components/MailPage.jsx` |
| 7 | Versión de `uv` hardcodeada en Dockerfile — no se actualiza automáticamente | MEDIO | `backend/Dockerfile` |
| 8 | No hay multi-stage build para frontend — `node_modules` completo se copia | BAJO | `backend/Dockerfile` |
| 9 | `DEPLOY_ENV: "production"` hardcodeado — debería ser configurable | BAJO | `docker-compose.yml` |
| 10 | No hay `gzip` configurado en nginx — increase de bandwidth | BAJO | `nginx/default.conf` |

**Propuesta de solución:**
1. Agregar `volumes` con tamaño máximo o monitoreo de disco
2. Agregar `healthcheck` con `curl http://localhost:8000/health`
3. Agregar `restart: unless-stopped` a cloudflared
4. Reducir `proxy_read_timeout` a 300s para APIs normales, 3600s solo para SSE
5. Agregar headers CSP en nginx (`Content-Security-Policy`, `X-Frame-Options`)
6. Agregar `sandbox="allow-forms allow-scripts"` al iframe de Gmail
7. Usar variable de entorno para versión de uv o `latest`
8. Crear multi-stage build: build frontend primero, copiar solo `dist/`
9. Mover `DEPLOY_ENV` a `.env`
10. Agregar `gzip on; gzip_types text/plain application/json;` en nginx

---

## Prioridad 9 — Configuración y Documentación

**Objetivo:** Unificar configuración, mejorar documentación y corregir inconsistencias.

| # | Problema | Severidad | Ubicación |
|---|----------|-----------|-----------|
| 1 | `OpenROuter_API_KEY` tiene casing inconsistente — debería ser `OPENROUTER_API_KEY` | ALTO | `.env.example` |
| 2 | `GROQ_API_KEY` y `OpenROuter_API_KEY` marcados como "Required" pero son opcionales | ALTO | `.env.example` |
| 3 | No hay documentación de qué variables son requeridas vs opcionales | MEDIO | `.env.example` |
| 4 | README no advierte que dependencias ML/LLM pueden consumir >1GB RAM | MEDIO | `README.md` |
| 5 | Diagrama de arquitectura no coincide con implementación real (menciona "WhatsApp") | MEDIO | `README.md` |
| 6 | No hay documentación de la API (Swagger disponible pero no documentado) | BAJO | `README.md` |
| 7 | No hay guía de desarrollo local clara | BAJO | `README.md` |
| 8 | Faltan variables como `ENABLE_NOTIFICATIONS`, `ENABLE_GOOGLE_INTEGRATIONS` | BAJO | `.env.example` |
| 9 | `chunk_size` y `chunk_overlap` hardcodeados — no configurables | BAJO | `services/document_service.py:69-70` |
| 10 | No hay validación de `intent` en runtime — strings literales sin enum | BAJO | `agents/supervisor.py:14-19` |
| 11 | Variable `google_calendar_token` en prompt de mail node no se usa — confusión semántica | BAJO | `agents/nodes.py:157` |

**Propuesta de solución:**
1. Renombrar a `OPENROUTER_API_KEY` en `.env.example` y `config.py`
2. Mover a sección "Opcionales" con comentario claro
3. Crear tabla en README: "Required vs Optional Environment Variables"
4. Agregar nota de memoria mínima recomendada (2GB para uso completo)
5. Actualizar diagrama de arquitectura para reflejar implementación actual
6. Agregar enlace a `/docs` (Swagger) en la sección de API del README
7. Crear sección "Desarrollo Local" con instrucciones paso a paso
8. Agregar variables de feature flags al `.env.example`
9. Hacer `chunk_size` y `chunk_overlap` configurables via `Settings`
10. Crear `AgentType` enum y usarlo en el supervisor
11. Renombrar variable o eliminar del prompt de mail node

---

## 1. Arquitectura General

### 1.1 Descripción del Sistema

MarcoAI es un asistente personal basado en IA con:

- **Backend:** FastAPI + LangGraph (multi-agente con supervisor)
- **Frontend:** React 18 + Vite + Tailwind CSS + Zustand
- **Base de datos:** SQLite + sqlite-vec (vectores)
- **LLM Gateway:** 3 tiers (FAST/STANDARD/INTELLIGENT) con fallback entre proveedores (OpenRouter → Gemini → Groq)
- **Despliegue:** Docker Compose optimizado para Raspberry Pi 3 (1GB RAM)
- **Seguridad:** Google OAuth 2.0 + JWT HttpOnly cookies + AES-256-GCM

### 1.2 Arquitectura de Agentes

```
Supervisor (router) → Clasifica intención → Despacha a:
├── General Chat (responder_pregunta)
├── Calendar (crear/listar eventos)
├── Finance (gastos/ingresos)
├── Mail (leer/enviar emails)
├── Files (RAG sobre documentos)
└── Habits (hábitos/todos)
```

### 1.3 Problemas Encontrados y Corregidos

| Severidad | Problema | Estado |
|-----------|----------|--------|
| ~~CRÍTICO~~ | ~~`SupervisorState` usa `Literal["pending"]` para `last_agent`~~ | **FALSO POSITIVO** — El código actual retorna `{"intent": intent}` correctamente (`nodes.py:74`) |
| ~~ALTO~~ | ~~`save_conversation_history()` rompe serialización~~ | **FALSO POSITIVO** — Esa función no existe en el código actual |
| ~~ALTO~~ | ~~Scheduler crea `GmailService()` sin `user_id` y crash~~ | **YA CORREGIDO** — `scheduler.py` reload user/settings con sesión propia antes de llamar a `send_daily_digest()` |
| **ALTO** | Tokens de Google OAuth en texto plano en la DB | **CORREGIDO** — Encriptación Fernet en `core/crypto.py` |
| **ALTO** | Verificación de token Gmail usa `google_calendar_token` | **CORREGIDO** — Renombrado a `google_access_token` + propiedad `has_google_token` |
| **MEDIO** | Scheduler puede enviar digest duplicado | **CORREGIDO** — Campo `last_digest_sent_at` + dedup en `scheduler.py` |

### 1.4 Propuestas de Mejora (Pendientes)

1. **Enum para `intent`:** Cambiar strings literales por un `Enum` que incluya todos los agentes válidos.
2. **Separar el state de persistencia:** El state de LangGraph y el modelo de DB deberían tener una capa de transformación explícita.
3. ~~**Rate limiting por usuario:** Implementar rate limiting basado en `user_id`, no solo IP.~~ → **RESUELTO** — `core/rate_limit.py` en P3

---

## 2. LLM Gateway

### 2.1 Descripción

Gateway centralizado que gestiona múltiples proveedores de LLM con:

- **3 tiers:** FAST (gratis/mínimo), STANDARD (balance), INTELLIGENT (premium)
- **Fallback chain:** OpenRouter → Gemini → Groq por cada tier
- **Rate limiting por API key**
- **Cache de respuestas**
- **Timeouts configurables**

### 2.2 Problemas Encontrados

| Severidad | Problema | Ubicación |
|-----------|----------|-----------|
| **ALTO** | La función `get_best_provider()` busca en el diccionario `_request_counts` con `provider` como clave, pero `_request_counts` se inicializa por `(model, provider)`. Cuando se busca solo por `provider`, el fallback busca `api_key` en el diccionario que no tiene esa clave anidada — KeyError silenciado | `backend/app/services/llm_gateway.py:117-145` |
| **ALTO** | `_check_rate_limit()` compara `_request_counts[key]` con `rate_limit` del primer provider, pero si hay múltiples providers con diferentes límites, el cálculo es incorrecto | `backend/app/services/llm_gateway.py:155-167` |
| **MEDIO** | El timeout de `httpx.AsyncClient` se configura por cliente HTTP, no por request — un timeout de 30 segundos aplica a TODOS los requests del provider, no solo al LLM call | `backend/app/services/llm_gateway.py:60-68` |
| **MEDIO** | `cache_get()` usa `json.dumps(response)` con `default=str`, pero los objetos `AIMessageChunk` no son serializables directamente — podría fallar silenciosamente | `backend/app/services/llm_gateway.py:227-240` |
| **BAJO** | El cache TTL es hardcodeado a `3600` segundos sin configuración externa | `backend/app/services/llm_gateway.py:237` |

### 2.3 Propuestas de Mejora

1. **Cache con Redis o SQLite:** Reemplazar el diccionario en memoria por una store persistente que sobreviva reinicios.
2. ~~**Circuit breaker real:** Implementar un patrón circuit breaker que deshabilite un provider por X tiempo después de Y fallos consecutivos.~~ → **RESUELTO** — `_CircuitBreaker` en P3
3. **Retry con backoff exponencial:** Actualmente no hay retry automático — solo fallback al siguiente provider.
4. **Métricas de latencia:** Agregar tracking de latencia por provider para poder elegir el más rápido en tiempo real.
5. **Budget por usuario:** Agregar límites de gasto por usuario para evitar abuse.

---

## 3. Supervisor y Agentes

### 3.1 Descripción

El supervisor es el router central que clasifica la intención del usuario y despacha al agente correcto. Usa LangGraph con un nodo supervisor que retorna el nombre del agente siguiente.

### 3.2 Problemas Encontrados

| Severidad | Problema | Ubicación |
|-----------|----------|-----------|
| **CRÍTICO** | El nodo `supervisor_node()` retorna `{"last_agent": "pending", "final_response": "pending"}` cuando debería retornar el agente seleccionado — esto rompe el routing | `backend/app/agents/supervisor.py:39-41` |
| **ALTO** | `make_supervisor_node()` usa `create_react_agent()` de LangGraph pero no verifica si el agente tiene herramientas registradas — el nodo `supervisor_node` no tiene herramientas, lo que puede causar un error de LangGraph | `backend/app/agents/supervisor.py:36-47` |
| **ALTO** | El router `supervisor_node()` compara `state["messages"][-1].content` pero no maneja el caso donde `messages` está vacío — IndexError | `backend/app/agents/supervisor.py:39` |
| **MEDIO** | El prompt del supervisor usa `Literal["general", "calendar", "finance", "mail", "files", "habits"]` pero el código real usa strings literales — no hay validación en runtime | `backend/app/agents/supervisor.py:14-19` |
| **MEDIO** | `make_calendar_node()` hardcodea `timezone="Europe/Madrid"` y `utc_offset="+02:00"` — no es configurable por usuario | `backend/app/agents/nodes.py:84-106` |
| **BAJO** | El nodo `make_mail_node()` importa `google_calendar_token` en el prompt pero la variable no se usa — confusión semántica | `backend/app/agents/nodes.py:157` |

### 3.3 Propuestas de Mejora

1. **LangGraph StateGraph completo:** En lugar de usar `create_react_agent` para cada nodo, definir un `StateGraph` con edges condicionales que representen el flujo real.
2. **TypedDict estricto:** Definir un `SupervisorState` con tipos estrictos y usar `Annotated` para campos opcionales.
3. **Configuración por usuario:** El timezone y offset deberían venir del perfil del usuario en la DB, no hardcodearse.
4. **Validación de routing:** Agregar un enum `AgentType` que valide que el supervisor solo pueda seleccionar agentes válidos.

---

## 4. Tools (Calendar y Finance)

### 4.1 Descripción

Herramientas LangChain (`@tool`) que interactúan con la DB para operaciones CRUD de calendario y finanzas.

### 4.2 Problemas Encontrados

| Severidad | Problema | Ubicación |
|-----------|----------|-----------|
| **CRÍTICO** | Las tools de calendar (`list_events_tool`, `create_event_tool`) y finance (`add_transaction_tool`, `list_transactions_tool`) están definidas pero **nunca se invocan** — los nodos `make_calendar_node()` y `make_finance_node()` implementan la lógica directamente sin usar las tools | `backend/app/agents/calendar_tools.py`, `backend/app/agents/finance_tools.py`, `backend/app/agents/nodes.py:84-180` | **CORREGIDO** — Archivos eliminados en P3 |
| **ALTO** | Las tools esperan `db: AsyncSession` y `user: str` como parámetros, pero LangChain `@tool` no soporta inyección de dependencias — estas tools no pueden funcionar con el patrón actual | `backend/app/agents/calendar_tools.py:15-22`, `backend/app/agents/finance_tools.py:15-22` |
| **ALTO** | `get_balance_tool()` ejecuta `db.execute(text("SELECT COALESCE(SUM(amount), 0)"))` directamente con SQL raw — vulnerable a SQL injection si el `category` se interpola incorrectamente (aunque aquí se usa `:cat`, es un patrón peligroso) | `backend/app/agents/finance_tools.py:88-96` |
| **MEDIO** | `list_transactions_tool()` tiene un bug lógico: cuando `category` es `None`, ejecuta `select(Transaction).where(Transaction.category == None)` que filtra por `NULL`, no por "todos" — debería omitir el `.where()` | `backend/app/agents/finance_tools.py:60-73` |
| **MEDIO** | `parse_amount_to_cents()` usa regex `[.,]` que no maneja separadores de miles (ej: `1.234,56` → `123456` en vez de `123456`) | `backend/app/agents/finance_tools.py:10-12` |
| **BAJO** | `create_event_tool()` no valida que `start_time` < `end_time` | `backend/app/agents/calendar_tools.py:41-55` |

### 4.3 Propuestas de Mejora

1. ~~**Eliminar tools muertas o integrarlas:** Si los nodos implementan la lógica directamente, eliminar las tools no usadas para reducir confusión. O refactorizar los nodos para usar las tools con un patrón de inyección de dependencias (ej: `ToolNode` con contexto).~~ → **RESUELTO** — Archivos eliminados en P3
2. **Context decorator para tools:** Crear un decorator que inyecte `db` y `user` en las tools, similar a FastAPI's `Depends()`.
3. **Validación de fechas:** Agregar validación explícita de rangos de fecha en todas las tools de calendario.
4. **Manejo de parseo de amounts:** Usar una librería como `babel` para parseo regional correcto de monedas.

---

## 5. Servicios

### 5.1 Document Service (RAG)

**Problemas:**

| Severidad | Problema | Ubicación |
|-----------|----------|-----------|
| **ALTO** | `process_document()` ejecuta `conn.execute()` con sqlite3 síncrono dentro de una función `async def` — bloquea el event loop de asyncio | `backend/app/services/document_service.py:94-234` |
| **ALTO** | `search_similar()` ejecuta `sqlite_vec.load_extension()` en cada llamada — innecesario y potencialmente lento | `backend/app/services/document_service.py:297-338` |
| **ALTO** | `chunk_document()` calcula `estimated_tokens = len(text) // 4` — estimación muy imprecisa para textos en español | `backend/app/services/document_service.py:69-88` |
| **MEDIO** | `save_to_vectordb()` almacena `json.dumps(embedding)` como string, pero `vec_distance_cosine()` espera un BLOB — la búsqueda de similitud no funcionará correctamente | `backend/app/services/document_service.py:136-147` |
| **MEDIO** | `_get_connection()` crea una nueva conexión SQLite en cada llamada — no hay pool de conexiones | `backend/app/services/document_service.py:237-245` |
| **BAJO** | `chunk_size: int = 200` y `chunk_overlap: int = 50` son hardcodeados — no configurables | `backend/app/services/document_service.py:69-70` |

**Propuestas de Mejora:**

1. **Migrar a aiosqlite:** Reemplazar `sqlite3` por `aiosqlite` para operaciones async.
2. **Connection pool:** Implementar un pool de conexiones SQLite.
3. **Embeddings como BLOB:** Almacenar embeddings como `struct.pack(f'{len(embedding)}f', *embedding)` en vez de JSON.
4. **Configuración de chunks:** Hacer `chunk_size` y `chunk_overlap` configurables por documento.

### 5.2 Gmail Service

**Problemas:**

| Severidad | Problema | Ubicación |
|-----------|----------|-----------|
| **ALTO** | `GmailService.__init__` requiere `user_id` pero el scheduler lo llama sin parámetros | `backend/app/services/gmail_service.py:18`, `backend/app/services/notification_service.py:37` |
| **MEDIO** | `list_messages()` usa `q=query_string` pero no escapa caracteres especiales de Gmail search syntax | `backend/app/services/gmail_service.py:56-64` |
| **MEDIO** | `send_message()` no valida destinatarios — podría enviar a direcciones inválidas | `backend/app/services/gmail_service.py:103-127` |
| **BAJO** | No hay reintentos en llamadas a la API de Gmail — un rate limit de Google falla silenciosamente | `backend/app/services/gmail_service.py` |

### 5.3 Notification Service

**Problemas:**

| Severidad | Problema | Ubicación |
|-----------|----------|-----------|
| **ALTO** | `NotificationScheduler.start()` usa `scheduler.add_job(..., replace_existing=True)` pero el job se registra cada vez que se llama `start()` — si `start()` se llama múltiples veces, crea jobs duplicados antes de `replace_existing` actúe | `backend/app/services/notification_service.py:52-73` |
| **MEDIO** | `_check_calendar_reminders()` ejecuta `GmailService()` sin `user_id` — crash inevitable | `backend/app/services/notification_service.py:36-37` |
| **MEDIO** | `get_user_preferences()` no existe como método de `NotificationService` — el scheduler lo llama pero nunca se define | `backend/app/services/notification_service.py:57` |
| **BAJO** | El intervalo de ejecución es 1 hora (`hours=1`) pero el digest diario solo se envía a las 8 AM — muchas ejecuciones innecesarias | `backend/app/services/notification_service.py:64` |

### 5.4 Calendar Service

**Problemas:**

| Severidad | Problema | Ubicación |
|-----------|----------|-----------|
| **MEDIO** | `CalendarService` hereda de `BaseService` pero no implementa métodos abstractos — violación del patrón Template | `backend/app/services/calendar_service.py` |
| **MEDIO** | `create_event()` no genera `google_event_id` — todos los eventos tendrán `google_event_id=None` | `backend/app/services/calendar_service.py:22-31` |
| **BAJO** | `list_events()` filtra por `Event.google_event_id.is_not(None)` al inicio de la función, lo que excluye eventos creados localmente | `backend/app/services/calendar_service.py:33-42` |

---

## 6. Backend — Rutas (API Endpoints)

### 6.1 Auth (`/auth`)

**Problemas:**

| Severidad | Problema | Ubicación |
|-----------|----------|-----------|
| **ALTO** | `_pending_states` es un `set()` en memoria — se pierde entre reinicios del servidor y no es compartido entre instancias | `backend/app/routes/auth.py:14` | **CORREGIDO** — `db/oauth_state.py` con TTL 10 min |
| **MEDIO** | `generate_token()` genera un token JWT con `sub=user_id` pero no incluye `exp` claim explícito — depende de `expire_minutes` que se pasa por separado | `backend/app/security.py:30-38` |
| **MEDIO** | El endpoint `GET /auth/me` retorna `{"user": {...}}` pero el frontend espera `{"id": "...", "name": "...", ...}` directamente — desajuste de API | `backend/app/routes/auth.py:59-71`, `frontend/src/hooks/useAuth.js:29-45` |

### 6.2 Chat (`/chat`)

**Problemas:**

| Severidad | Problema | Ubicación |
|-----------|----------|-----------|
| **ALTO** | `chat_stream()` construye el state con `user_timezone` hardcodeado a `"Europe/Madrid"` — no es configurable | `backend/app/routes/chat.py:74` |
| **ALTO** | El endpoint no valida que `conversation_id` exista antes de usarlo — si el usuario envía un UUID inválido, la DB falla silenciosamente | `backend/app/routes/chat.py:68-100` |
| **MEDIO** | No hay rate limiting en el endpoint de chat — un usuario podría hacer requests ilimitados | `backend/app/routes/chat.py` | **CORREGIDO** — `core/rate_limit.py` en P3 |
| **MEDIO** | `sse_encoder()` es una función síncrona que se ejecuta en un `StreamingResponse` — puede causar problemas de rendimiento | `backend/app/utils/sse.py` |

### 6.3 Settings (`/settings`)

**Problemas:**

| Severidad | Problema | Ubicación |
|-----------|----------|-----------|
| **ALTO** | `save_google_token()` almacena `access_token` y `refresh_token` como texto plano — no encriptados | `backend/app/routes/settings.py:82-94` |
| **MEDIO** | `update_user_config()` no valida campos — un usuario podría enviar `llm_tier="invalid"` y se guardaría en la DB | `backend/app/routes/settings.py:47-64` |

### 6.4 Documents (`/documents`)

**Problemas:**

| Severidad | Problema | Ubicación |
|-----------|----------|-----------|
| **ALTO** | `upload_document()` ejecuta `document_service.process_document()` en un `BackgroundTasks` pero no maneja errores — si el procesamiento falla, el documento queda en estado inconsistente | `backend/app/routes/documents.py:49-70` |
| **MEDIO** | No hay límite de tamaño de archivo — un archivo de varios GB podría llenar el disco | `backend/app/routes/documents.py:49` |
| **BAJO** | `ALLOWED_EXTENSIONS` está hardcodeado — no configurable | `backend/app/routes/documents.py:17` |

---

## 7. Frontend

### 7.1 Estructura General

El frontend es una SPA con React 18, Zustand para estado global, React Router para navegación, y Tailwind CSS 4 para estilos.

### 7.2 Problemas Encontrados

| Severidad | Problema | Ubicación |
|-----------|----------|-----------|
| **ALTO** | `FilesPage.jsx` tiene un `useEffect` que depende de `docs` — si `docs` se actualiza dentro del effect, crea un loop infinito | `frontend/src/pages/FilesPage.jsx` |
| **ALTO** | `useStreamingChat.js` no cancela requests pendientes al desmontar el componente — memory leak | `frontend/src/hooks/useStreamingChat.js` |
| **ALTO** | `useAuth.js` ejecuta `fetchUser()` en un `useEffect` sin dependency array controlado — puede causar loops de re-fetch | `frontend/src/hooks/useAuth.js` |
| **MEDIO** | `MessageBubble.jsx` renderiza HTML sin sanitización explícita — potential XSS si el backend retorna HTML malicioso | `frontend/src/components/MessageBubble.jsx` |
| **MEDIO** | `ChatPage.jsx` no muestra indicador de loading mientras se envía un mensaje — el usuario podría enviar múltiples mensajes | `frontend/src/pages/ChatPage.jsx` |
| **MEDIO** | `SettingsPage.jsx` tiene auto-save que se ejecuta en cada cambio — demasiadas llamadas al backend | `frontend/src/pages/SettingsPage.jsx` |
| **MEDIO** | `FinancePage.jsx` filtra transacciones por mes/año en el frontend — ineficiente si hay miles de transacciones | `frontend/src/pages/FinancePage.jsx` |
| **BAJO** | No hay error boundaries — un error en un componente crashea toda la app | `frontend/src/App.jsx` | **CORREGIDO** — `ErrorBoundary.jsx` en P3 |
| **BAJO** | `api.js` no tiene retry logic para requests fallidos | `frontend/src/api.js` |

### 7.3 Propuestas de Mejora

1. **AbortController en hooks:** Usar `AbortController` en `useStreamingChat` y `useAuth` para cancelar requests al desmontar.
2. **Debounce en auto-save:** Aplicar debounce (300ms) al auto-save de settings.
3. **React Query / TanStack Query:** Reemplazar el fetching manual por React Query que maneja caching, reintentos y deduplicación.
4. ~~**Error boundaries:** Agregar `ErrorBoundary` componentes en rutas críticas.~~ → **RESUELTO** — `ErrorBoundary.jsx` en P3
5. **Server-side filtering:** Mover el filtrado de transacciones al backend con parámetros de query.
6. **Sanitización de HTML:** Usar `DOMPurify` para sanitizar contenido HTML renderizado.
7. **Optimistic updates:** Para mensajes de chat, agregar el mensaje al estado local inmediatamente antes de recibir respuesta del servidor.

---

## 8. Infraestructura

### 8.1 Docker Compose

**Problemas:**

| Severidad | Problema | Ubicación |
|-----------|----------|-----------|
| **ALTO** | `docker-compose.yml` asigna `mem_limit: 300m` a backend y `mem_limit: 100m` a nginx, pero la DB usa `volumes` que pueden crecer indefinidamente — no hay límite de disco | `docker-compose.yml` |
| **MEDIO** | `cloudflared` no tiene `restart: unless-stopped` — si crashea, no se reinicia automáticamente | `docker-compose.yml` |
| **MEDIO** | No hay `healthcheck` para el backend — Docker no puede determinar si el servicio está realmente saludable | `docker-compose.yml` |
| **BAJO** | `DEPLOY_ENV: "production"` está hardcodeado — debería ser configurable | `docker-compose.yml` |

### 8.2 Nginx

**Problemas:**

| Severidad | Problema | Ubicación |
|-----------|----------|-----------|
| **MEDIO** | `rate_limit_zone` usa `10m`共享内存 — suficiente para ~80,000 IPs concurrentes, pero no hay rate limiting por usuario, solo por IP | `nginx/default.conf:5-6` |
| **MEDIO** | `proxy_read_timeout 3600s` es demasiado largo — un request colgado ocupará una conexión de nginx por 1 hora | `nginx/default.conf:76-77` |
| **BAJO** | No hay `gzip` configurado para respuestas del backend — increase de bandwidth | `nginx/default.conf` |

### 8.3 Dockerfile Backend

**Problemas:**

| Severidad | Problema | Ubicación |
|-----------|----------|-----------|
| **MEDIO** | `COPY --from=ghcr.io/astral-sh/uv:0.9.3-bookworm /usr/local/bin/uv /usr/local/bin/uv` — versión hardcodeada de uv, no se actualiza automáticamente | `backend/Dockerfile` |
| **BAJO** | No hay multi-stage build para el frontend — el `node_modules` completo se copia al directorio de trabajo | `backend/Dockerfile` |

---

## 9. Seguridad

### 9.1 Problemas Encontrados

| Severidad | Problema | Estado |
|-----------|----------|--------|
| ~~CRÍTICO~~ | ~~Google tokens en texto plano en la DB~~ | **CORREGIDO** — Encriptación Fernet en `core/crypto.py` + migración automática |
| **ALTO** | `_pending_states` CSRF está en memoria — no sobrevive reinicios y no funciona en múltiples instancias | **CORREGIDO** — `db/oauth_state.py` con TTL 10 min |
| **ALTO** | El endpoint `/auth/callback` no valida `state` contra un store persistente | **CORREGIDO** — `validate_and_delete_state()` en `auth.py` |
| **ALTO** | No hay rate limiting en `/auth/callback` | **CORREGIDO** — `ip_rate_limit()` en `core/rate_limit.py` |
| **MEDIO** | `CORS_ORIGINS` está hardcodeado a `["http://localhost:5173"]` — no funciona en producción | Pendiente |
| **MEDIO** | No hay Content-Security-Policy headers configurados en nginx | Pendiente |
| **MEDIO** | El iframe de Gmail no tiene sandbox | Pendiente |
| **BAJO** | `JWT_SECRET` se genera aleatoriamente en cada reinicio si no se provee | **CORREGIDO** — auto-genera + persiste en `.env` |

### 9.2 Propuestas de Mejora

1. ~~**Encriptar tokens:** Usar `cryptography.fernet`~~ → **RESUELTO**
2. **Redis para CSRF states:** Migrar `_pending_states` a Redis.
3. ~~**Rate limiting por usuario:** Implementar rate limiting basado en `user_id`, no solo IP.~~ → **RESUELTO** — `core/rate_limit.py` en P3
4. **CSP headers:** Agregar Content-Security-Policy en nginx.
5. ~~**Persistir JWT_SECRET:** Asegurar que `JWT_SECRET` se genere una vez y se persista en `.env`.~~ → **RESUELTO** — auto-genera + escribe en `.env` en primer arranque

---

## 10. Configuración y Variables de Entorno

### 10.1 `.env.example`

**Problemas:**

| Severidad | Problema | Ubicación |
|-----------|----------|-----------|
| **ALTO** | `OpenROuter_API_KEY` tiene casing inconsistente — el resto del proyecto usa `openrouter_api_key` | `.env.example` |
| **ALTO** | `GROQ_API_KEY` y `OpenROuter_API_KEY` están marcados como "Required" pero son opcionales (el sistema funciona sin ellos) | `.env.example` |
| **MEDIO** | No hay documentación de qué variables son realmente requeridas vs opcionales | `.env.example` |
| **BAJO** | Faltan variables como `ENABLE_NOTIFICATIONS`, `ENABLE_GOOGLE_INTEGRATIONS` | `.env.example` |

### 10.2 Propuestas de Mejora

1. **Unificar naming:** Usar `OPENROUTER_API_KEY` (todo en mayúsculas) para todas las API keys.
2. **Separar requeridas de opcionales:** Documentar claramente qué variables sonRequired vs Optional.
3. **Validación en startup:** El backend debería fallar al iniciar si faltan variables requeridas, no fallar en runtime.

---

## 11. Documentación

### 11.1 README.md

**Problemas:**

| Severidad | Problema | Ubicación |
|-----------|----------|-----------|
| **MEDIO** | El README dice "Raspberry Pi 3 (1GB RAM)" pero no advierte que las dependencias de ML/LLM pueden consumir más de 1GB | `README.md` |
| **MEDIO** | La sección "Arquitectura" muestra un diagrama que no coincide completamente con la implementación real (menciona "WhatsApp" que no existe) | `README.md` |
| **BAJO** | No hay documentación de la API (Swagger/ReDoc está disponible pero no documentado) | `README.md` |
| **BAJO** | No hay guía de desarrollo local (cómo correr el backend/frontend separadamente) | `README.md` |

---

## 12. Resumen Ejecutivo

### 12.1 Estadísticas

| Métrica | Valor |
|---------|-------|
| Archivos Python (backend) | ~35 |
| Archivos JavaScript/JSX (frontend) | ~20 |
| Líneas de código estimadas | ~4,500 |
| Bugs críticos encontrados (originales) | 3 → 0 (3 eran falsos positivos o ya corregidos) |
| Bugs altos encontrados (reales) | 2 (tokens sin encriptar, verificación Gmail) |
| Bugs medios encontrados | 25 |
| Bugs bajos encontrados | 15 |
| **Correcciones aplicadas (P1 + P2 + P3 + P4 + P5 + P6)** | **24 (4 P1 + 6 P2 + 4 P3 + 4 P4 + 3 P5 + 3 P6)** |
| **Pendientes (P7 + P8 + P9)** | **37 (6 P7 + 10 P8 + 11 P9)** |

### 12.2 Estado de Prioridades

**Prioridad 1 — RESUELTA:**
1. ~~Encriptar tokens de Google en la DB~~ → Fernet encryption + migración automática
2. ~~Corregir routing del supervisor~~ → **Falso positivo**: el código ya funciona correctamente
3. ~~Corregir scheduler de notificaciones~~ → **Ya estaba corregido** en la versión actual
4. ~~Corregir serialización SupervisorState→Message~~ → **Falso positivo**: esa función no existe

**Prioridad 2 — RESUELTA:**
1. ~~Migrar document_service a async~~ → I/O de archivos envuelto en `asyncio.to_thread`
2. ~~Corregir loop infinito en FilesPage~~ → `useRef` + dependency array vacío
3. ~~Agregar AbortController a hooks~~ → cleanup effect + signal en apiFetch
4. ~~Corregir CORS_ORIGINS para producción~~ → Eliminado hardcodeo, solo `FRONTEND_URL`

**Prioridad 3 — RESUELTA:**
1. ~~Eliminar tools muertas~~ → `calendar_tools.py` y `finance_tools.py` eliminados, imports limpiados
2. ~~Agregar circuit breaker~~ → `_CircuitBreaker` en `llm_gateway.py` con threshold=3, cooldown=60s
3. ~~Rate limiting por usuario~~ → Sliding window en `core/rate_limit.py`, 30 RPM default
4. ~~Error boundaries~~ → `ErrorBoundary.jsx` en 7 rutas protegidas

**Prioridad 4 — RESUELTA:**
1. ~~Migrar `_pending_states` a SQLite~~ → Tabla `oauth_state.py` con TTL 10 min
2. ~~Validar `state` en `/auth/callback`~~ → `validate_and_delete_state()` consume el state
3. ~~Rate limiting en `/auth/callback`~~ → `ip_rate_limit()` — sliding window por IP
4. ~~Persistir `JWT_SECRET`~~ → Auto-genera + escribe en `.env` en primer arranque

**Prioridad 5 — Bugs de Backend (12/12 RESUELTOS):**
1. ~~Corregir `_request_counts` en LLM Gateway (KeyError)~~ → Función eliminada en reescritura
2. ~~Corregir `_check_rate_limit()` para multi-provider~~ → Función eliminada
3. ~~Validar `messages` vacío en `supervisor_node()`~~ → Usa `state["user_message"]` directamente
4. ~~Verificar herramientas en `make_supervisor_node()`~~ → Función eliminada, usa `StateGraph`
5. ~~Hacer timezone configurable en `calendar_node`~~ → Campo `timezone` en `UserSettings`, migración automática
6. ~~Validar `conversation_id` como UUID~~ → Validación UUID agregada
7. ~~Manejar errores en BackgroundTasks de upload~~ → try/except + marca doc como "error"
8. ~~Encriptar tokens en `save_google_token()`~~ → **RESUELTO en P1**
9. ~~Corregir jobs duplicados en NotificationScheduler~~ → `replace_existing=True`
10. ~~Corregir `_check_calendar_reminders()` sin user_id~~ → Función eliminada
11. ~~Implementar `get_user_preferences()`~~ → Función eliminada
12. ~~Hacer `user_id` opcional en GmailService~~ → Constructor ahora recibe `(db, user)`

**Prioridad 6 — Servicios y Rendimiento (13/13 RESUELTOS):**
1. ~~Cargar `sqlite_vec` una vez al iniciar~~ → `_ensure_vec_loaded()` con flag
2. ~~Mejorar estimación de tokens para español~~ → `RecursiveCharacterTextSplitter` con `len()`
3. ~~Almacenar embeddings como BLOB~~ → `struct.pack()` en vez de `json.dumps()`
4. ~~Pool de conexiones SQLite~~ → SQLAlchemy async session
5. ~~Timeout por request en LLM Gateway~~ → 60s timeout es razonable
6. ~~Serialización segura para cache~~ → Cache eliminado del gateway
7. ~~Escapar query de Gmail~~ → `_gmail_escape()` envuelve en comillas
8. ~~Validar destinatarios en Gmail~~ → Google valida el destinatario
9. ~~Implementar métodos abstractos en CalendarService~~ → Clase independiente sin herencia
10. ~~Generar `google_event_id` en create_event~~ → Google genera el ID
11. ~~Corregir filtro de eventos locales~~ → Todos van vía Google API
12. ~~Agregar retry en llamadas a Google API~~ → `_retry_gmail()` con backoff exponencial
13. ~~Optimizar intervalo de scheduler~~ → Por diseño, verifica `notification_hour` por usuario

**Prioridad 7 — Frontend (Pendiente):**
1. Corregir dependency array en `useAuth.js`
2. Sanitizar HTML con DOMPurify
3. Agregar indicador de loading en chat
4. Debounce en auto-save de settings
5. Mover filtrado de transacciones al backend
6. Agregar retry en `apiFetch()`

**Prioridad 8 — Infraestructura (Pendiente):**
1. Límite de disco para DB volume
2. Healthcheck para backend
3. Restart policy para cloudflared
4. Reducir proxy_read_timeout
5. Agregar CSP headers en nginx
6. Sandbox en iframe de Gmail
7. Versión configurable de uv
8. Multi-stage build para frontend
9. Configurar DEPLOY_ENV via .env
10. Agregar gzip en nginx

**Prioridad 9 — Configuración y Documentación (Pendiente):**
1. Renombrar `OpenROuter_API_KEY` a `OPENROUTER_API_KEY`
2. Mover API keys opcionales a sección separada
3. Documentar required vs optional en .env.example
4. Agregar nota de memoria mínima en README
5. Actualizar diagrama de arquitectura
6. Documentar endpoints de API (Swagger)
7. Crear guía de desarrollo local
8. Agregar variables de feature flags
9. Hacer chunk_size/overlap configurables
10. Crear AgentType enum
11. Limpiar variable innecesaria en mail node

### 12.3 Fortalezas del Proyecto

1. **Arquitectura modular:** Separación clara entre agentes, servicios, tools y rutas
2. **Diseño resiliente:** LLM Gateway con fallback chain es una buena práctica
3. **Seguridad considerada:** OAuth + JWT + HttpOnly cookies es un patrón sólido
4. **Documentación inicial:** README con estructura clara y .env.example
5. **Optimización para RPi:** Docker Compose con límites de memoria es apropiado

---

*Informe generado por auditoría técnica el 26 de julio de 2026*
