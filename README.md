# MarcoAI – Personal Intelligence Assistant

**MarcoAI** es un asistente personal inteligente diseñado para centralizar tu productividad, finanzas y conocimientos en un solo lugar. Construido con una arquitectura de **agentes supervisores (LangGraph)** y capacidades de **RAG (Retrieval-Augmented Generation)**, Marco no solo responde preguntas, sino que gestiona tu vida digital de forma proactiva.

Diseñado para funcionar en hardware limitado como una **Raspberry Pi 3** (1-2 GB RAM), con una arquitectura **Local-First** que prioriza la privacidad y el rendimiento.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![React](https://img.shields.io/badge/frontend-React%20%2B%20Vite-blue.svg)
![RAG](https://img.shields.io/badge/RAG-SQLite--vec-orange.svg)
![Docker](https://img.shields.io/badge/docker-compose-%23037a99.svg)

---

## Caracteristicas Principales

### Arquitectura Multi-Agente Supervisada

Marco implementa un sistema jerarquico con un **Supervisor** que clasifica las intenciones del usuario y enruta las tareas a nodos especializados:

```
User Message -> Supervisor Node (clasificacion de intencion via LLM FAST)
                   |
     Routes to: General Chat / Calendar / Finance / Mail / Files / Habits
                   |
     Cada agente ejecuta herramientas especificas del dominio
                   |
     Respuesta generada con streaming SSE al frontend
```

**Capacidades de los Agentes:**

- **General Chat:** Conversacional contextual con memoria de sesion y tono personalizado del usuario (amigable, profesional, motivacional).
- **Files (RAG):** Busqueda semantica sobre documentos PDF y texto usando **SQLite-vec** con embeddings de Gemini. Tu "nube privada" de conocimiento.
- **Finance:** Seguimiento de ingresos y gastos, balances mensuales, analisis por categoria con deteccion automatica y visualizaciones con Recharts.
- **Calendar:** CRUD completo con Google Calendar — crear, listar, actualizar y eliminar eventos. Soporta timezone configurable por usuario.
- **Mail:** Lectura de la bandeja de entrada y redaccion de mensajes a traves de Gmail.
- **Habits:** Creacion, gestion y seguimiento de habitos con horarios configurables y logs diarios.

### Privacidad y Rendimiento (Edge-Ready)

- **Local First:** Base de datos SQLite ligera con extensiones vectoriales nativas (`sqlite-vec`). Todo el procesamiento se ejecuta localmente.
- **Optimizado para RPi:** Disenado para funcionar en hardware limitado como una **Raspberry Pi 3** (minimo 1 GB RAM, 2 GB recomendado).
- **Cloudflare Tunnels:** Acceso seguro desde cualquier lugar sin abrir puertos ni configurar DNS.
- **JWT + HttpOnly Cookies:** Autenticacion con Google OAuth 2.0, JWT en cookies HttpOnly (inaccesibles por JS).
- **Token Encryption:** Los tokens de Google OAuth se almacenan encriptados con **Fernet (AES-128-CBC)** en la base de datos.
- **CSRF Protection:** States OAuth almacenados en SQLite con TTL de 10 minutos (no en memoria).
- **Rate Limiting:** Proteccion por usuario (sliding window, configurable) y por IP en endpoints sensibles.
- **Circuit Breaker:** Providers de LLM deshabilitados automaticamente tras 3 fallos consecutivos (cooldown 60s).
- **Error Boundaries:** Componentes React por pagina para aislar crashes del frontend.

### Gateway de LLM con Failover

- **Multi-Provider:** Soporte para **Google Gemini**, **Groq** y **OpenRouter** con fallback automatico.
- **Cost-Aware Routing:** Enrutamiento inteligente por tier (FAST / STANDARD / INTELLIGENT).
- **Resiliencia:** Si un proveedor falla, el sistema pasa automaticamente al siguiente disponible.

### Interfaz de Usuario Moderna

Frontend construido con **React 18 + Vite**, **Tailwind CSS v4**, **Zustand** para estado y **React Router v7** para navegacion. Incluye:

- Modo oscuro con diseno responsivo.
- Streaming de respuestas en tiempo real con SSE.
- Visualizaciones de datos con **Recharts**.
- Iconos con **lucide-react**.
- Renderizado de markdown con **react-markdown**.
- Error boundaries por pagina para mayor resiliencia.

---

## Stack Tecnologico

### Backend

| Tecnologia               | Proposito                                                                    |
| ------------------------ | ---------------------------------------------------------------------------- |
| **Python 3.11**          | Lenguaje principal                                                           |
| **FastAPI**              | Framework API REST de alto rendimiento                                       |
| **Uvicorn** (con uvloop) | Servidor ASGI                                                                |
| **LangGraph**            | Orquestacion de agentes con grafos de estado                                 |
| **LangChain**            | Capa de abstraccion para LLM                                                 |
| **Google Gemini**        | LLM principal + embeddings (`gemini-3.5-flash-lite`, `gemini-embedding-001`) |
| **Groq**                 | LLM de respaldo (`llama-3.3-70b`)                                            |
| **OpenRouter**           | LLM de respaldo (multi-modelo)                                               |
| **SQLAlchemy**           | ORM para SQLite asincrono                                                    |
| **aiosqlite**            | Driver SQLite asincrono                                                      |
| **sqlite-vec**           | Busqueda de similitud vectorial                                              |
| **PyMuPDF**              | Extraccion de texto de PDF para RAG                                          |
| **PyJWT**                | Autenticacion con tokens JWT                                                 |
| **cryptography (Fernet)**| Encriptacion de tokens OAuth en reposo                                        |
| **APScheduler**          | Programador para notificaciones diarias                                      |
| **Google API Client**    | Integracion con Gmail y Calendar                                             |
| **httpx**                | Cliente HTTP asincrono                                                       |

### Frontend

| Tecnologia                      | Proposito                               |
| ------------------------------- | --------------------------------------- |
| **JavaScript (React 18)**       | Framework UI                            |
| **Vite**                        | Herramienta de build ultra-rapida       |
| **React Router v7**             | Ruteo client-side                       |
| **Tailwind CSS (v4)**           | Estilos utility-first                   |
| **Zustand**                     | Gestion de estado                       |
| **Recharts**                    | Visualizacion de datos (graficos)       |
| **lucide-react**                | Libreria de iconos                      |
| **react-markdown + remark-gfm** | Renderizado de markdown para respuestas |

### Infraestructura

| Tecnologia                  | Proposito                                     |
| --------------------------- | --------------------------------------------- |
| **Docker + Docker Compose** | Orquestacion de contenedores                  |
| **Nginx**                   | Proxy inverso y serving de archivos estaticos |
| **Cloudflared**             | Tuneles seguros para exposicion a internet    |

---

## Instalacion Rapida

### Requisitos Previos

- Docker y Docker Compose instalados.
- Una API Key de Google Gemini (obtenida en [Google AI Studio](https://aistudio.google.com/)).
- Google OAuth 2.0 credentials (Client ID + Client Secret) del [Google Cloud Console](https://console.cloud.google.com/).
- API Keys opcionales para providers de respaldo (Groq, OpenRouter).

### Pasos

1. **Clonar el repositorio:**

   ```bash
   git clone https://github.com/tu-usuario/marcoai.git
   cd marcoai
   ```

2. **Configurar variables de entorno:**
   Copia el archivo de ejemplo y ajusta los valores:

   ```bash
   cp .env.example .env
   ```

   **Variables requeridas:**

   ```bash
   GOOGLE_API_KEY=tu_api_key_gemini
   GOOGLE_CLIENT_ID=tu_client_id_oauth
   GOOGLE_CLIENT_SECRET=tu_client_secret_oauth
   DATABASE_URL=sqlite+aiosqlite:///./marcoai.db
   FRONTEND_URL=http://localhost:5173

   # Encriptacion de tokens (generar una vez):
   ENCRYPTION_KEY=           # Ver instruccion abajo

   # JWT signing (se auto-genera si esta vacio):
   SECRET_KEY=
   ```

   Generar `ENCRYPTION_KEY`:
   ```bash
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

   **Variables opcionales:**

   ```bash
   # LLM de respaldo con fallback
   GROQ_API_KEY=tu_groq_api_key
   OPENROUTER_API_KEY=tu_openrouter_api_key

   # Rate limiting (default: 30 RPM por usuario)
   RATE_LIMIT_RPM=30

   # Tunel seguro (sin necesidad de abrir puertos)
   CLOUDFLARE_TUNNEL_TOKEN=tu_token_opcional
   ```

3. **Desplegar con Docker Compose:**

   ```bash
   docker compose up -d --build
   ```

   Las migraciones de DB se ejecutan automaticamente al iniciar. La tabla `oauth_states` y las columnas nuevas se crean sin intervencion manual.

4. **Acceder:**
   Abre tu navegador en `http://localhost` (o en tu dominio configurado con Cloudflare).

### Desarrollo Local

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## API Endpoints

La API esta disponible en `/api/v1/` con documentacion automatica en `/docs` (Swagger/OpenAPI).

| Metodo   | Endpoint                      | Descripcion                         |
| -------- | ----------------------------- | ----------------------------------- |
| `GET`    | `/health`                     | Health check                        |
| `GET`    | `/docs`                       | Documentacion Swagger/OpenAPI       |
| `GET`    | `/api/v1/auth/google`         | Iniciar sesion con Google (SSO)     |
| `GET`    | `/api/v1/auth/google/callback`| Callback OAuth de Google            |
| `GET`    | `/api/v1/auth/me`             | Obtener usuario autenticado         |
| `POST`   | `/api/v1/auth/logout`         | Cerrar sesion                       |
| `POST`   | `/api/v1/chat`                | Chat single-turn (JSON)             |
| `POST`   | `/api/v1/chat/stream`         | Chat streaming con SSE + LangGraph  |
| `GET`    | `/api/v1/calendar/events`     | Listar eventos de Google Calendar   |
| `POST`   | `/api/v1/calendar/events`     | Crear evento en Google Calendar     |
| `DELETE` | `/api/v1/calendar/events/:id` | Eliminar evento                     |
| `GET`    | `/api/v1/finance/transactions`| Listar transacciones                |
| `POST`   | `/api/v1/finance/transactions`| Crear transaccion                   |
| `GET`    | `/api/v1/finance/balance`     | Balance mensual                     |
| `GET`    | `/api/v1/gmail/messages`      | Listar correos                      |
| `GET`    | `/api/v1/gmail/messages/:id`  | Leer un correo                      |
| `POST`   | `/api/v1/gmail/send`          | Enviar correo                       |
| `GET`    | `/api/v1/documents`           | Listar documentos                   |
| `POST`   | `/api/v1/documents/upload`    | Subir documento (PDF/TXT)           |
| `DELETE` | `/api/v1/documents/:id`       | Eliminar documento                  |
| `GET`    | `/api/v1/habits`              | Listar habitos                      |
| `POST`   | `/api/v1/habits`              | Crear habito                        |
| `DELETE` | `/api/v1/habits/:id`          | Eliminar habito                     |
| `GET`    | `/api/v1/settings`            | Obtener ajustes del usuario         |
| `PUT`    | `/api/v1/settings`            | Actualizar ajustes (tono, TZ, etc.) |

---

## Estructura del Proyecto

```text
├── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py                    # Entry point, lifespan, CORS, auto-migrations
│       ├── agents/
│       │   ├── supervisor.py          # LangGraph graph + streaming API
│       │   ├── nodes.py               # Agent nodes (supervisor, calendar, finance, mail, files, habits)
│       │   ├── states.py              # AgentState TypedDict
│       │   ├── prompts.py             # System prompts, INTENT_LABELS
│       │   └── tools/
│       │       ├── gmail_tools.py
│       │       └── doc_tools.py
│       ├── api/
│       │   ├── routes/
│       │   │   ├── auth.py            # Google OAuth: login, callback, /me, logout
│       │   │   ├── chat.py            # Chat (JSON + SSE streaming)
│       │   │   ├── calendar.py        # Google Calendar endpoints
│       │   │   ├── documents.py       # Upload + RAG search
│       │   │   ├── finance.py         # Finance CRUD
│       │   │   ├── gmail.py           # Gmail endpoints
│       │   │   ├── habits.py          # Habits CRUD
│       │   │   ├── llm.py             # LLM gateway test
│       │   │   └── settings.py        # User preferences
│       │   ├── schemas.py             # Pydantic request/response models
│       │   └── deps.py                # Auth dependency injection
│       ├── core/
│       │   ├── config.py              # pydantic-settings (.env)
│       │   ├── crypto.py              # Fernet encryption for OAuth tokens
│       │   ├── rate_limit.py          # Per-user + per-IP rate limiting
│       │   ├── security.py            # JWT creation + password hashing
│       │   └── scheduler.py           # APScheduler for daily digest
│       ├── db/
│       │   ├── base.py                # Async SQLAlchemy engine + session
│       │   ├── models.py              # ORM: User, ChatMessage, Transaction, Document,
│       │   │                          #   Habit, HabitLog, UserSettings
│       │   └── oauth_state.py         # CSRF state table (SQLite, TTL 10 min)
│       └── services/
│           ├── llm_gateway.py         # Multi-provider gateway + circuit breaker
│           ├── calendar_service.py    # Google Calendar API wrapper
│           ├── finance_service.py     # Finance CRUD service
│           ├── gmail_service.py       # Gmail API wrapper
│           ├── document_service.py    # PDF/TXT parsing + RAG + sqlite-vec
│           ├── habits_service.py      # Habits tracking service
│           └── notification_service.py # Daily digest via Gmail
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx                    # React Router + ErrorBoundary per route
│       ├── components/
│       │   ├── chat/
│       │   │   ├── MessageBubble.jsx
│       │   │   └── RouteIndicator.jsx
│       │   ├── layout/
│       │   │   ├── AppShell.jsx
│       │   │   └── Sidebar.jsx
│       │   └── ui/
│       │       ├── ErrorBoundary.jsx  # Per-page error boundary
│       │       └── ProtectedRoute.jsx
│       ├── hooks/
│       │   ├── useAuth.js
│       │   └── useStreamingChat.js    # SSE streaming + AbortController
│       ├── lib/
│       │   └── api.js                 # apiFetch with signal support
│       ├── pages/
│       │   ├── LoginPage.jsx
│       │   ├── ChatPage.jsx
│       │   ├── CalendarPage.jsx
│       │   ├── FinancePage.jsx
│       │   ├── MailPage.jsx
│       │   ├── FilesPage.jsx
│       │   ├── HabitsPage.jsx
│       │   ├── SettingsPage.jsx
│       │   └── ComingSoonPage.jsx
│       └── store/
│           ├── authStore.js
│           └── uiStore.js
└── nginx/
    ├── Dockerfile
    └── default.conf
```

---

## Seguridad

- **Google OAuth 2.0:** Autenticacion exclusiva via Google (no passwords locales).
- **JWT HttpOnly Cookies:** Tokens en cookies HttpOnly + SameSite=Lax (inaccesibles por JS).
- **Fernet Encryption:** Tokens de Google OAuth encriptados con AES-128-CBC en la DB.
- **CSRF States:** States OAuth en SQLite con TTL de 10 min (no en memoria).
- **Rate Limiting:** Sliding window por usuario (30 RPM default) + por IP en auth (20 RPM).
- **Circuit Breaker:** Providers de LLM deshabilitados tras 3 fallos consecutivos.
- **Error Boundaries:** React error boundaries por pagina para aislar crashes.
- **Auto-generated SECRET_KEY:** JWT secret se genera y persiste automaticamente en `.env`.

---

## Licencia

Este proyecto esta bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para mas detalles.

---

<p align="center">
  Desarrollado con para la comunidad open source.
</p>
