# 🛡️ RepuShield AI — Monitor de Reputación Local y Reseñas B2B

Un MVP Micro-SaaS completo para comercios y negocios locales (restaurantes, clínicas dentales, talleres, retail) que monitoriza reseñas en tiempo real, alerta inmediatamente al dueño ante quejas de 1 o 2 estrellas por Telegram/Email y redacta respuestas diplomáticas profesionales con IA (Groq / OpenAI) para neutralizar el impacto negativo y recuperar clientes.

---

## 🏗️ Arquitectura del Sistema

```
Monitor de Reputación Local y Reseñas/
├── app/
│   ├── __init__.py
│   ├── config.py                 # Validación de variables de entorno (.env) con Pydantic Settings
│   ├── database.py               # Configuración SQLite/SQLAlchemy y gestión de sesiones
│   ├── models.py                 # Modelo relacional Review (calificación, sentimiento, respuesta IA)
│   ├── schemas.py                # Esquemas Pydantic para Webhooks, Scan, Estadísticas y Respuestas
│   ├── main.py                   # Servidor FastAPI (Webhooks, Scraper, CRUD, Analítica)
│   └── services/
│       ├── __init__.py
│       ├── scraper_service.py    # Conector a Google Places API + Simulador realista en español
│       ├── ai_service.py         # Análisis de sentimiento y redacción de respuestas (Groq/OpenAI)
│       └── notification_service.py # Alertas automáticas por Telegram Bot API y SMTP Email
├── frontend/
│   ├── __init__.py
│   └── app.py                    # Dashboard en Streamlit (Bandeja crítica, métricas, aprobación)
├── .env.example                  # Plantilla de variables de entorno
├── .env                          # Configuración local por defecto
├── requirements.txt              # Dependencias del proyecto
└── README.md                     # Documentación completa
```

---

## 🚀 Puesta en Marcha Rápida

### 1. Requisitos Previos
- Python 3.10 o superior instalado.

### 2. Instalación de Dependencias
```bash
pip install -r requirements.txt
```

### 3. Configuración de Variables de Entorno
Copia el archivo `.env.example` a `.env` si aún no lo has hecho:
```bash
cp .env.example .env
```
Edita `.env` para añadir tus credenciales opcionales:
- **Groq API Key:** Clave en `GROQ_API_KEY` (utiliza por defecto `llama-3.3-70b-versatile`). Si no se configura, el sistema utiliza un motor heurístico de contingencia garantizando que la aplicación nunca falle.
- **Telegram Bot:** Configura `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` para recibir las alertas en tiempo real en tu teléfono.

---

## 🖥️ Ejecución de la Plataforma

### Paso A: Iniciar el Backend (FastAPI)
En tu primera terminal:
```bash
python -m uvicorn app.main:app --reload --port 8000
```
- API pública y Webhooks: `http://127.0.0.1:8000`
- Documentación Swagger Interactiva: `http://127.0.0.1:8000/docs`

### Paso B: Iniciar el Frontend (Streamlit Dashboard)
En tu segunda terminal:
```bash
streamlit run frontend/app.py
```
- Acceso al Dashboard: `http://localhost:8501`

---

## 📡 Endpoints Principales del Backend

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `POST` | `/api/v1/reviews/webhook` | Webhook para recibir reseñas desde Make/Zapier/Scrapers. |
| `POST` | `/api/v1/reviews/scan` | Dispara el rastreador o simulador de reseñas. |
| `GET` | `/api/v1/reviews` | Lista de reseñas con filtros (sentimiento, estrellas, estado). |
| `GET` | `/api/v1/reviews/{id}` | Detalle completo de una reseña. |
| `POST` | `/api/v1/reviews/{id}/approve` | Aprueba, edita y marca como publicada una respuesta. |
| `POST` | `/api/v1/reviews/{id}/regenerate-ai` | Solicita una nueva variante de respuesta a la IA. |
| `GET` | `/api/v1/stats` | Estadísticas agregadas y métricas de reputación. |
| `POST` | `/api/v1/notifications/test-telegram` | Envía mensaje de verificación al bot de Telegram. |

---

## 🧪 Pruebas con cURL o PowerShell

### Probar Ingesta de Reseña Negativa vía Webhook (Simular cliente molesto)
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/reviews/webhook" \
     -H "Content-Type: application/json" \
     -d '{
       "author_name": "Alfonso Gómez",
       "rating": 1,
       "text": "Pésimo servicio. Tardaron 50 minutos en servirnos y la carne estaba completamente fría. No vuelvo.",
       "business_name": "Restaurante Parrilla Los Olivos",
       "source": "Google Places"
     }'
```

### Disparar un Escaneo Simulado de 5 Reseñas
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/reviews/scan" \
     -H "Content-Type: application/json" \
     -d '{"count": 5, "force_negative": false}'
```

---

## 🤖 Integración de Telegram Bot en 2 Minutos

1. En Telegram, inicia conversación con **@BotFather** y envía `/newbot`.
2. Dale un nombre y usuario a tu bot (ej: `MiRestauranteAlertasBot`).
3. Copia el token generado y pégalo en `TELEGRAM_BOT_TOKEN`.
4. Inicia conversación con **@userinfobot** en Telegram para obtener tu **Id** numérico y pégalo en `TELEGRAM_CHAT_ID`.
5. Pulsa el botón **"🔔 Probar Bot de Telegram"** en el panel o ejecuta `/api/v1/notifications/test-telegram`.

