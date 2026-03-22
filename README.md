# Marco AI - Agente Personal Inteligente

Aplicación web full-stack que actúa como agente personal multiusuario, optimizada para desplegarse en una **Raspberry Pi 3** usando Docker y la API de Groq para inferencia LLM ultra ruda y rápida.

![Marco AI](https://github.com/user-attachments/assets/1493c3d5-f1da-4fb2-8f33-98fd9bada40d)

## 🚀 Despliegue en Raspberry Pi 3 (vía SSH)

Sigue estos comandos exactos en tu terminal SSH conectada a la Raspberry Pi:

### 1. Clonar el repositorio y entrar a la carpeta

```bash
git clone https://github.com/marquito3012/marcoai.git
cd marcoai
```

### 2. Configurar Variables de Entorno

Copia el archivo de ejemplo y edítalo con nano:

```bash
cp .env.example .env
nano .env
```

Dentro de `nano`, configura tus credenciales reales:

- `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET` (obtenidos de Google Cloud Console con APIs de Calendar y Gmail activadas)
- `GROQ_API_KEY`
- `SECRET_KEY` (puedes generar una rápida ejecutando `openssl rand -hex 32` en otra terminal)
- `CLOUDFLARE_TUNNEL_TOKEN` (tu token de Cloudflared, esencial para acceso externo)
- `FRONTEND_URL` (Debe ser tu dominio público, ej: `https://www.marcoai.com`)

_Guarda y sal con `Ctrl+O`, `Enter`, `Ctrl+X`._

### 3. Levantar la infraestructura con Docker Compose

Este comando descargará las imágenes base ARM, construirá el Backend Multi-stage instalando `sqlite-vss`, el Frontend estático con Nginx, e iniciará todos los contenedores:

```bash
docker compose up -d --build
```

### 4. Verificar que todo está corriendo

Puedes ver los logs de los contenedores para asegurarte de que el backend ha arrancado la DB correctamente y de que Cloudflared se ha conectado:

```bash
docker compose logs -f
```

### 5. Actualizar

Puedes actualizar el agente con los siguientes comandos después de haber hecho commit de los cambios:

```bash
git pull
docker compose restart
```

## Arquitectura

- **Base de Datos**: SQLite nativo montado en un volumen de Docker. La tabla vectorial (RAG) se maneja con la extensión `sqlite-vss` o fallback en Python con Numpy para maximizar la compatibilidad ARM.
- **Backend API**: FastAPI (Python 3.11). Rápido, ligero y asíncrono.
- **Frontend SPA**: Vanilla JS + CSS System (Glassmorphism), despachado por Nginx Alpine (consumo <5MB RAM).
- **Procesamiento de Lenguaje**: Toda la inferencia se delega a Groq a través del orquestador manual de herramientas de Marco AI, dejando a la RPi3 la simple tarea de servir la web y buscar en la base de datos SQL.

## Notas de Seguridad del RAG y Multi-usuario

Este agente fue diseñado para un grupo cerrado limitado a **20 usuarios máximos**.
Absolutamente todas las inserciones y búsquedas de la memoria del agente (RAG) se filtran a nivel SQL con el `user_id` asociado a la sesión de Google OAuth del usuario autenticado, asegurando cero fuga de datos entre los residentes del sistema.
