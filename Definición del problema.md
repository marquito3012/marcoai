# Definición del Proyecto: Sistema Orquestador de Agentes Personales Inteligentes (MarcoAI)

## 1. Contexto y Planteamiento del Problema

En el entorno digital actual, los usuarios gestionan su vida personal y profesional a través de múltiples plataformas desconectadas (Google Calendar para el tiempo, Gmail para comunicaciones, aplicaciones de terceros o Excel para finanzas, y plataformas en la nube para archivos). Esta fragmentación obliga al usuario a realizar tareas manuales, repetitivas y a cambiar constantemente de contexto.

Además, existe una creciente preocupación por la privacidad y el control de los datos personales (archivos, documentos). Los usuarios carecen de una interfaz unificada, proactiva e inteligente que no solo centralice la información, sino que ejecute acciones por ellos y permita interactuar con sus documentos privados de forma conversacional.

## 2. Visión del Producto

Desarrollar una aplicación web self-hosted (desplegada en una Raspberry Pi 3) que actúe como un **Asistente Personal Unificado**. El núcleo del sistema será una **orquestación de agentes de IA** especializados por dominio. El usuario interactuará con el sistema principalmente a través de lenguaje natural (Chat), mientras el sistema refleja el estado de las operaciones en un ecosistema de _Dashboards_ interactivos.

El sistema aprovechará el almacenamiento local (Tarjeta SD de 500 GB) para crear una "nube privada" interactiva mediante tecnología RAG (Retrieval-Augmented Generation).

## 3. Arquitectura y Entorno de Ejecución

- **Hardware:** Raspberry Pi 3 Model B/B+ con tarjeta SD de 500 GB.
- **Autenticación:** Single Sign-On (SSO) mediante Google OAuth 2.0.
- **Paradigma de Interacción:** "Chat-First" interactivo complementado con visualización de datos en Dashboards (UI unificada o por módulos).
- **Procesamiento de IA:** Arquitectura híbrida (Orquestación, almacenamiento e indexación vectorial alojados localmente en la RPi; inferencia LLM delegada a APIs en la nube para garantizar rendimiento).

## 4. Alcance y Módulos del Sistema

El sistema funcionará mediante un **Agente Supervisor** (Router) que interpretará la intención del usuario en el chat y delegará la tarea al Agente Especializado correspondiente.

### 4.1 Módulo de Calendario (Gestión del Tiempo)

- **Funciones del Agente:** Interpretar lenguaje natural para planificar el tiempo ("Traslada todas mis reuniones de mañana al viernes").
- **Capacidades:** Operaciones CRUD (Crear, Leer, Actualizar, Eliminar) sobre eventos.
- **Integración:** Google Calendar API.

### 4.2 Módulo de Finanzas (Gestor Económico)

- **Funciones del Agente:** Clasificación automática de gastos dictados por el usuario ("Apunta que he gastado 45€ en gasolina").
- **Capacidades:** \* Registro de ingresos y gastos mensuales fijos (suscripciones, nóminas, alquiler).
  - Registro de gastos puntuales (ocio, compras).
  - Cálculo de balances y previsiones.
- **Dashboard:** Gráficas de distribución de gastos, balance mensual y alertas de presupuesto.

### 4.3 Módulo de Correo (Gestión de Gmail)

- **Funciones del Agente:** Redacción de borradores, resumen de hilos largos, y categorización inteligente.
- **Capacidades:** Leer bandeja de entrada, buscar correos específicos, enviar emails y etiquetar.
- **Integración:** Gmail API.

### 4.4 Módulo de Nube Privada y RAG (Gestión Documental)

- **Funciones del Agente:** Actuar como un bibliotecario personal para los archivos del usuario.
- **Capacidades:** \* Gestor de archivos tradicional (Subir, descargar, organizar en carpetas).
  - Indexación automática de documentos (PDFs, Word, TXT) en una base de datos vectorial local (ej. ChromaDB o Qdrant).
  - **RAG:** Capacidad de responder preguntas complejas basadas _exclusivamente_ en los documentos del usuario ("¿Qué dice el contrato de alquiler sobre las mascotas?").

### 4.5 Módulos Adicionales Propuestos (Fase 2)

1.  **Módulo de Tareas y Notas (Second Brain):** Un gestor de tareas pendientes (To-Do) vinculado al calendario. El agente puede crear subtareas automáticamente para un proyecto grande.
2.  **Módulo de Hábitos:** Un agente que te acompañe a iniciar un nuevo hábito, al que puedas especificar con qué frecuencia quieres realizarlo (totalmente flexible, ya sea diariamente, semanalmente, los lunes y miércoles, etc.) y te recuerde cuando debas realizarlo. Que puedas marcar como hecha la tarea y el agente te dé una respuesta de ánimo. Si no lo haces, que te pregunte qué ha pasado y te anime a seguir. Que te muestre estadísticas de tus hábitos y te anime a seguir. las tareas pueden ser marcadas como hechas y los días que no se han realizado se quedan en rojo, si se han realizado se quedan en verde y si todavía no se ha acabado el día y todavía no se ha marcado como hecha la tarea, se queda en blanco.

## 5. Criterios de Éxito

1.  **Seguridad:** Autenticación robusta y aislamiento de los datos en la nube personal. Aislamiento entre usuarios.
2.  **Baja Latencia de Interfaz:** El sistema debe responder en tiempos razonables a pesar de las limitaciones de la Raspberry Pi 3.
3.  **Precisión del RAG:** El agente debe ser capaz de citar la fuente (el archivo exacto) al responder preguntas sobre la nube local, minimizando las alucinaciones.

## 6. Desafíos Técnicos Identificados (Risk Management)

- **Limitaciones de Memoria (RAM):** La Raspberry Pi 3 cuenta con 1GB de RAM. Se priorizará el uso de lenguajes/frameworks eficientes (ej. Go, Rust o Python altamente optimizado) y bases de datos ligeras (SQLite).
- **Desgaste de la Tarjeta SD:** Las operaciones de lectura/escritura constantes (especialmente bases de datos y logs) pueden corromper la SD. Se aplicarán estrategias de escritura diferida, deshabilitación de swap innecesario y logs en memoria (RAM disk) donde sea posible.
- **Aislamiento entre usuarios:** Es fundamental garantizar que los datos de un usuario no sean accesibles por otro. Se implementarán medidas de seguridad robustas para garantizar el aislamiento entre usuarios.
- **Uso de APIs externas:** Se utilizarán APIs externas para la inferencia LLM, lo que implica una dependencia de servicios externos y puede generar costos adicionales. Se implementarán medidas para minimizar el uso de APIs externas y se buscarán alternativas de código abierto para reducir costos. Se busca minimizar el uso de tokens en las peticiones, aunque se van a usar 3 APIs externas para rotar de proveedor al alcanzar el límite de tokens o por si alguna está caída.
