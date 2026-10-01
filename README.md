# ☀️ Solar Monitor Pro

Sistema integral de telemetría y monitoreo fotovoltaico en tiempo real construido sobre **FastAPI**, **Pydantic v2**, **Vanilla JS Modular**, **SVG Animado** y empaquetado para producción con **Docker**.

---

## 🏛️ Arquitectura del Proyecto

El proyecto implementa una arquitectura desacoplada por capas con separación estricta de responsabilidades:

```text
solar-monitor/
├── .env.example              # Plantilla de variables de entorno
├── .env                      # Configuración local de credenciales y puertos
├── .gitignore                # Exclusiones estándar de Git
├── Dockerfile                # Imagen ligera basada en python:3.11-slim (usuario no-root)
├── docker-compose.yml        # Orquestación de contenedor con healthchecks
├── requirements.txt          # Dependencias de producción
├── README.md                 # Documentación técnica
├── app/
│   ├── __init__.py
│   ├── main.py               # Entrypoint de FastAPI, CORS y rutas estáticas
│   ├── config.py             # Gestión tipada de configuración con Pydantic Settings
│   ├── api/                  # Capa de Controladores / Endpoints
│   │   ├── __init__.py
│   │   ├── deps.py           # Inyección de dependencias (DI)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py     # Agregador de rutas de la API v1
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── status.py # GET /api/v1/status (telemetría actual)
│   │           └── history.py# GET /api/v1/history (curva y kWh)
│   ├── core/                 # Lógica de dominio pura
│   │   ├── __init__.py
│   │   └── calculator.py     # Estimación de temperatura, integración kWh y alertas
│   ├── schemas/              # Esquemas Pydantic v2 (DTOs de entrada/salida)
│   │   ├── __init__.py
│   │   ├── status.py         # StatusResponse, MetricsSchema, AlertsSchema, RatingsSchema
│   │   └── history.py        # HistoryResponse, HistoryPoint, HistorySummary
│   └── services/             # Integración con APIs externas
│       ├── __init__.py
│       └── shinemonitor.py   # ShineMonitorService con fallback a modo demostración
└── static/                   # Frontend desacoplado
    ├── css/
    │   └── styles.css        # Dark mode, Glassmorphism, CSS Grid y animaciones de flujo
    ├── js/
    │   ├── api_client.js     # Cliente HTTP fetch() para FastAPI con soporte de reintento
    │   ├── flow_diagram.js   # Controlador y animación SVG del flujo de 4 nodos
    │   ├── unified_chart.js  # Gráfico unificado Chart.js con doble eje Y
    │   └── app.js            # Coordinador principal, polling de 30s y eventos UI
    └── index.html            # Dashboard HTML5 semántico y accesible
```

---

## 🚀 Despliegue Rápido con Docker

La forma recomendada de desplegar la aplicación en cualquier servidor o máquina local es utilizando Docker y Docker Compose:

### 1. Configurar Credenciales
Edita el archivo `.env` e ingresa tus credenciales de ShineMonitor:
```bash
SHINEMONITOR_USERNAME="tu_usuario@ejemplo.com"
SHINEMONITOR_PASSWORD="tu_password_secreta"
PORT=8000
```
*(Nota: Si no se configuran credenciales, el sistema activa automáticamente un **Modo Demostración** con telemetría solar realista para previsualización).*

### 2. Iniciar el Contenedor
```bash
docker compose up -d --build
```

### 3. Acceder a la Interfaz
Abre tu navegador en:
```text
http://localhost:8000
```

Para detener el contenedor:
```bash
docker compose down
```

---

## 💻 Ejecución Local con Python (Opcional)

Si dispones de Python 3.10+ en tu máquina local:

```bash
# 1. Crear y activar entorno virtual
python -m venv .venv
source .venv/bin/activate    # En Linux/macOS
.venv\Scripts\activate       # En Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Iniciar el servidor de desarrollo
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📊 Características y Funcionalidades del Frontend

1. **Diagrama de Flujo de Energía en Tiempo Real (SVG)**:
   - 4 nodos principales: ☀️ **Solar (PV)**, ⚡ **Red Eléctrica**, 🏠 **Consumo Hogar**, 🔋 **Batería**, interconectados por un inversor central.
   - Animación de partículas y dirección de líneas dinámicas según la procedencia de la energía (descarga de batería hacia consumo, inyección solar hacia batería o consumo, corte de red).
2. **HUD de Métricas Operativas**:
   - Tarjetas de lectura rápida para Potencia Solar, Consumo Activo, Nivel de Batería (SOC %), Tensión de Red, Temperatura de Inversor y Balance Total de Energía (kWh).
3. **Curva de Telemetría Unificada (Chart.js)**:
   - **Selector de Modo**:
     - *Simple*: Visualiza exclusivamente Generación Solar vs Consumo Hogar sobre un eje de Potencia (W).
     - *Experto*: Despliega adicionalmente Nivel de Batería (%), Temperatura del Inversor (°C) y Tensión de Red (V) activando ejes secundarios automáticos.
   - **Filtros Rápidos sin Latencia**:
     - Filtros locales sobre el día precargado: `1h`, `2h`, `3h` *(activo por defecto)*, `6h`, `12h`, `Día completo`.
     - Filtros históricos automáticos por rango: `Ayer`, `Hace 2 días`, `Hace 3 días`, `Hace 7 días`, `Hace 14 días`.
4. **Banners Reactivos de Alerta**:
   - Detección de pérdida de red (0V).
   - Aviso de riesgo por sobrecarga del inversor (demanda ≥ 85%).
   - Aviso de batería baja (almacenamiento ≤ 20%).
5. **Polling Automático**:
   - Consulta el estado cada 30 segundos e incluye botón de refresco manual con retroalimentación visual.

---

## 📡 Endpoints de la API

La API cuenta con documentación interactiva Swagger disponible en `http://localhost:8000/docs`:

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `GET` | `/api/v1/status` | Métricas instantáneas, estado del dispositivo y alertas |
| `GET` | `/api/v1/history` | Serie temporal y balance de kWh (`date`, `start_date`, `end_date`) |
| `POST` | `/api/v1/alerts/test-telegram` | Envía mensaje de prueba a tu chat o grupo de Telegram |
| `GET` | `/api/v1/alerts/status` | Estado actual de alertas activas y umbrales configurados |
| `POST` | `/api/v1/alerts/check-now` | Forzar ciclo de evaluación de alertas de inmediato |
| `GET` | `/health` | Chequeo de salud del servicio (para Docker y monitoreo) |
| `GET` | `/api/status` | Alias de retrocompatibilidad con clientes anteriores |
| `GET` | `/api/history` | Alias de retrocompatibilidad con clientes anteriores |

---

## 🤖 Configuración del Bot de Alertas en Telegram

El sistema cuenta con un monitor autónomo en segundo plano (24/7) que despacha notificaciones críticas a tu Telegram sin importar si tienes la web abierta.

### 1. Crear tu Bot en Telegram
1. Abre Telegram y busca a [@BotFather](https://t.me/BotFather).
2. Envía el comando `/newbot` y sigue las instrucciones para asignarle un nombre (ej. `MiSolarMonitorBot`).
3. Copia el **HTTP API Token** proporcionado (ej: `7123456789:ABCdefGh...`).

### 2. Obtener tu Chat ID
1. En Telegram, busca [@userinfobot](https://t.me/userinfobot) y pulsa `/start`. Te responderá con tu `Id` numérico (ej: `123456789`).
2. *(Opcional)* Si deseas recibir alertas en un grupo, agrega a tu bot al grupo y obtén el Chat ID del grupo (suele empezar con `-100...`).
3. **Importante:** Inicia una conversación con tu propio bot pulsando `/start` en su chat para autorizarlo a enviarte mensajes.

### 3. Configurar en `.env`
Edita tu archivo `.env`:
```env
TELEGRAM_BOT_TOKEN="7123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
TELEGRAM_CHAT_ID="123456789"
TELEGRAM_ENABLED=true

# Umbrales
ALERT_TEMP_MAX_C=65.0
ALERT_OVERLOAD_PCT=85.0
ALERT_LOW_BATTERY_PCT=20.0
ALERT_CHECK_INTERVAL_SECONDS=60
ALERT_COOLDOWN_MINUTES=30
```

### 4. Probar la Conexión
Puedes verificar el envío del mensaje de prueba abriendo:
`http://localhost:8000/docs` -> `POST /api/v1/alerts/test-telegram` -> **Execute**.

---

## 🛡️ Buenas Prácticas Aplicadas

- **Seguridad**: Ejecución de contenedor bajo usuario no privilegiado `appuser` (UID 1000).
- **Tipado Fuerte**: Modelos de entrada y salida validados con **Pydantic v2**.
- **Inyección de Dependencias**: El servicio `ShineMonitorService` y la configuración se inyectan a través de `fastapi.Depends`.
- **Modo Demostración / Resiliencia**: Si el inversor se encuentra apagado o no hay credenciales disponibles, la app entrega datos simulados para no interrumpir la experiencia de usuario.
- **Optimización de Caché**: Las capas del `Dockerfile` separan la instalación de librerías del código fuente para acelerar reconstrucciones.
