# Plan de Implementación de MarcoAI

Este plan detalla los pasos para construir el Sistema Orquestador de Agentes Personales Inteligentes (MarcoAI), teniendo en cuenta las limitaciones de hardware (Raspberry Pi 3 con 1GB RAM) y la arquitectura híbrida y modular propuesta en los documentos del proyecto.

## Fase 1: Configuración Inicial e Infraestructura Base
- [x] Inicializar el repositorio del Backend (Python 3.11+).
- [x] Configurar el entorno virtual y añadir las dependencias base (`fastapi`, `uvicorn`, `sqlite`, etc.).
- [x] Inicializar el repositorio Frontend usando React + Vite (para minimizar la carga y construir rápido).
- [x] Instalar e inicializar Tailwind CSS en el Frontend para estilado estructurado.
- [x] Añadir `Zustand` para la gestión global del estado de UI, y componentes base.
- [x] Cargar las variables del `.env` global en el backend y preparar un entorno base dockerizado.
- [x] Configurar `docker-compose.yml` base con límites estrictos de recursos (`memory: 400M` para el backend) y un estricto `logging driver` (`max-size: "10m"`, `max-file: "3"`) para evitar daños en la SD.
- [x] Configurar SQLite en modo WAL y definir scripts para la primera migración de esquema.

## Fase 2: Autenticación, Core de Datos y Seguridad (HU01, HU04)
- [x] Implementar el esquema básico de base de datos para la tabla `Usuarios` (con campos `user_id`, `email`, etc.).
- [x] Implementar el proceso de Single Sign-On (SSO) OAuth 2.0 con Google usando `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET`.
- [x] Generar e implementar JSON Web Tokens (JWT) para mantener sesiones "stateless", validando con `SECRET_KEY`.
- [x] Desarrollar el middleware en FastAPI que intercepte rutas, verifique el JWT e inyecte siempre el `user_id`.
- [x] Asegurar que toda llamada a base de datos aplique restricciones de Row-Level Security basándose en `user_id`.

## Fase 3: Controlador Multi-LLM y Gateway de IA (HU49)
- [x] Desarrollar la clase o servicio `LLMGateway` en el backend.
- [x] Configurar los clientes para conectar con Google Gemini (`GOOGLE_API_KEY`), Groq (`GROQ_API_KEY`) y OpenRouter (`OpenROuter_API_KEY`).
- [x] Implementar la lógica de enrutamiento inteligente basada en el coste/complejidad de la tarea.
- [x] Implementar el mecanismo de fallback automático: si la API principal falla o devuelve 429, pasar a la siguiente opción.

## Fase 4: Experiencia "Chat-First" y UI Base (HU02, HU03, HU06)
- [x] Diseñar el Layout global de la SPA (Barra lateral para navegación, Área interactiva central).
- [x] Desarrollar el componente de Chat, preparándolo para parsear y renderizar Markdown.
- [x] Implementar Server-Sent Events (SSE) en FastAPI para enviar las respuestas por _streaming_ al frontend (baja latencia).
- [x] Preparar el esqueleto visual de la zona de Dashboards y la lógica en Zustand para alternar entre paneles.

## Fase 5: Agente Supervisor y LangGraph (HU07, HU08, HU50)
- [x] Configurar el entorno de LangGraph.
- [x] Implementar el Agente Supervisor que recibe el mensaje del usuario y determina la intención (clasificación de tareas con el LLM más barato).
- [x] Desarrollar al menos los primeros sub-agentes: el agente de `Chat General` (HU02) y el agente de `Intención Financiera` (base para HU20 y HU21).
- [x] Conectar el grafo de LangGraph en el backend con el endpoint de streaming SSE existente.
- [x] Añadir soporte para "Small Talk" manejado directamente por el Supervisor.

## Fase 6: Módulo - Calendario (HU09-HU14) ✅ COMPLETADA
- [x] Autenticar/obtener tokens de acceso funcionales a la Google Calendar API por usuario.
- [x] Crear las herramientas (Tools) del Agente para operaciones CRUD de eventos.
- [x] Conectar el Agente de Calendario al Supervisor.
- [x] Desarrollar su Dashboard respectivo en el frontend para mostrar una agenda o línea de tiempo integrada.

## Fase 7: Módulo - Finanzas y Gastos (HU15-HU22) ✅ COMPLETADA
- [x] Crear el esquema SQLite para Finanzas: `Transacciones` (monto, tipo, categoría, recurrencia, `user_id`).
- [x] Crear Agente Financiero y herramientas para clasificar gastos ingresados en lenguaje natural e insertarlos a BD.
- [x] Habilitar herramientas para consultas al balance mensual (RAG de SQL o consultas estructuradas directas).
- [x] Desarrollar Dashboard con paneles de balance de liquidez mensual, usar `Recharts` para gráficas circulares/barras de gasto.

## Fase 8: Módulo - Correo (Gmail) (HU23-HU28)
- [x] Autenticar Google Workspace/Gmail API.
- [x] Crear herramientas para buscar, recuperar, etiquetar hilos y remitir borradores de mails.
- [x] Desarrollar el Agente Especialista asociado y conectarlo al Supervisor LangGraph.

## Fase 9: Módulo - Nube Privada y Documentos RAG (HU29-HU35)
- [x] Crear los endpoints REST para subida y borrado de documentos `.pdf`, `.docx`, `.txt`.
- [x] Ubicar el almacenamiento temporal/permanente seguro montando volumen al contenedor.
- [x] Incorporar `sqlite-vec` al sistema para almacenar vectores en DB local (extensión nativa).
- [x] Desarrollar un sistema de encolado/background o worker ligero en Python que extraiga texto, aplique chunking, cree los embeddings y guarde en BD.
- [x] Crear Agente "Bibliotecario" o self-querying retriever, optimizando el prompt para evitar alucinaciones y forzar la cita (ej. `[Archivo.pdf]`).

## Fase 10: Módulos Adicionales - Tareas y Hábitos (HU36-HU48)
- [x] Aumentar el modelo SQLite para To-Dos y Trazabilidad de Hábitos (fechas completadas).
- [x] Crear herramientas que desglosen "proyectos grandes" en tareas menores (con llamadas a un LLM "Razonador").
- [x] Crear panel frontal con un gráfico tipo "Contribuciones" (GitHub-style calendar) con colores verde/rojo/blanco.
- [x] Crear la rutina de evaluación retrospectiva que pregunte al usuario por sus hábitos fallidos si finaliza el día.

## Fase 11: Optimización, Seguridad y Publicación
- [x] Configurar las reglas y túnel de Cloudflare nativo leyendo del `.env`.
- [x] Implementar la "Escritura Diferida" en transacciones cotidianas: encolarlas en memoria Python y guardar en batch en SQLite cada X minutos (protegiendo el desgaste de la tarjeta SD).
- [x] Añadir rate limiting en Nginx (ej. máximo de 10 request/seg) o middleware en FastAPI.
- [x] Incorporar Helmet/HSTS equivalent en FastAPI con Content Security Policy.
- [x] Puesta a punto final y empaquetado del `docker-compose.yml`.
- [x] Minimizar por completo las dependencias de memoria para asegurar que el sistema se mantiene holgadamente dentro del giga de RAM.
- [x] Realizar pruebas manuales (QA) de interfaz en dispositivos móviles y de escritorio.
- [x] Testear la mitigación de alucinaciones (RAG) solicitando datos irreales y forzando la respuesta negativa por parte del modelo.
