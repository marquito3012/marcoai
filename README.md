# 🤖 MarcoAI – Personal Intelligence Assistant

**MarcoAI** es un asistente personal inteligente de última generación diseñado para centralizar tu productividad, finanzas y conocimientos en un solo lugar. Construido con una arquitectura de **agentes supervisores (LangGraph)** y capacidades de **RAG (Retrieval-Augmented Generation)**, Marco no solo responde preguntas, sino que gestiona tu vida digital de forma proactiva.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![React](https://img.shields.io/badge/frontend-React%20%2B%20Vite-blue.svg)
![RAG](https://img.shields.io/badge/RAG-SQLite--vec-orange.svg)

---

## ✨ Características Principales

### 🧠 Supervisor Inteligente (LangGraph)
Marco utiliza un sistema de agentes coordinados por un "Supervisor" que clasifica tus intenciones en tiempo real y delega tareas a nodos especializados:
*   **General Chat:** Conversación fluida y contextual.
*   **Files (RAG):** Tu propia "nube privada" con búsqueda semántica sobre documentos PDF y texto (procesado con `gemini-embedding-001`).
*   **Finance:** Gestión de ingresos, gastos y balances mensuales con visualizaciones automáticas.
*   **Calendar:** Integración completa con Google Calendar para agendar y consultar eventos.
*   **Mail:** Lectura y gestión inteligente de correos electrónicos (Gmail).
*   **Habits:** Seguimiento de hábitos y consistencia diaria.

### 🔒 Privacidad y Rendimiento (Edge-Ready)
*   **Local First:** Base de datos SQLite ligera con extensiones vectoriales nativas (`sqlite-vec`).
*   **Optimizado para RPi:** Diseñado para correr de forma fluida en hardware limitado como una Raspberry Pi.
*   **Cloudflare Tunnels:** Acceso seguro desde cualquier lugar del mundo sin necesidad de abrir puertos ni configuraciones complejas de red.

### 💎 Interfaz de Usuario Luxury
Frontend moderno construido con **React + Vite** y un sistema de diseño refinado, con modo oscuro, animaciones sutiles y una experiencia de usuario de nivel premium.

---

## 🛠️ Stack Tecnológico

**Backend:**
*   **FastAPI:** API de alto rendimiento y baja latencia.
*   **LangGraph:** Orquestación de agentes mediante grafos de estado.
*   **Gemini AI:** Modelos de lenguaje y embeddings de última generación.
*   **SQLAlchemy + SQLite-vec:** Persistencia de datos y búsqueda vectorial eficiente.

**Frontend:**
*   **React 18:** Componentización y estado reactivo.
*   **Vite:** Herramienta de construcción ultra-rápida.
*   **Vanilla CSS:** Diseño responsivo y estético personalizado.

**Infraestructura:**
*   **Docker & Docker Compose:** Despliegue en contenedores aislados.
*   **Nginx:** Servidor web y proxy inverso optimizado.
*   **Cloudflare Cloudflared:** Túneles seguros para exposición a internet.

---

## 🚀 Instalación Rápida

### Requisitos Previos
*   Docker y Docker Compose instalados.
*   Una API Key de Google Gemini (obtenida en [Google AI Studio](https://aistudio.google.com/)).

### Pasos
1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/tu-usuario/marcoai.git
   cd marcoai
   ```

2. **Configurar variables de entorno:**
   Crea un archivo `.env` en la raíz:
   ```bash
   GOOGLE_API_KEY=tu_api_key_aqui
   SECRET_KEY=una_clave_segura_para_jwt
   CLOUDFLARE_TUNNEL_TOKEN=tu_token_opcional
   ```

3. **Desplegar con Docker Compose:**
   ```bash
   docker compose up -d --build
   ```

4. **Acceder:**
   Abre tu navegador en `http://localhost` (o en tu dominio configurado en Cloudflare).

---

## 📂 Estructura del Proyecto

```text
├── backend/            # Lógica del servidor, Agentes y RAG
├── frontend/           # Interfaz de usuario React
├── nginx/              # Configuración del servidor y Proxy Inverso
├── data/               # Base de datos persistente (Volumen Docker)
├── uploads/            # Archivos procesados para RAG (Volumen Docker)
└── docker-compose.yml  # Orquestación de los servicios
```

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más detalles.

---

<p align="center">
  Desarrollado con ❤️ para centralizar tu vida digital.
</p>
