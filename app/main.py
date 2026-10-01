import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.v1.router import api_router
from app.services.shinemonitor import ShineMonitorService
from app.core.alerts import alert_manager

logger = logging.getLogger(__name__)
settings = get_settings()


async def background_alert_monitor():
    """
    Tarea en segundo plano que monitorea continuamente el inversor
    y despacha alertas a Telegram incluso si no hay usuarios navegando la web.
    """
    service = ShineMonitorService(settings)
    interval = max(10, settings.ALERT_CHECK_INTERVAL_SECONDS)
    logger.info(f"Monitor de alertas iniciado: intervalo de chequeo cada {interval} segundos.")

    # Esperar 5s al inicio para arranque limpio
    await asyncio.sleep(5)

    while True:
        try:
            status = await asyncio.to_thread(service.get_current_status)
            await alert_manager.evaluate_status(status, service_instance=service)
        except asyncio.CancelledError:
            logger.info("Monitor de alertas detenido correctamente.")
            break
        except Exception as e:
            logger.warning(f"Error en ciclo del monitor de alertas: {e}")

        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manejo del ciclo de vida de la aplicación FastAPI."""
    monitor_task = asyncio.create_task(background_alert_monitor())
    yield
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Sistema de Monitoreo y Telemetria Solar en tiempo real con Alertas Telegram",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas versionadas v1 (/api/v1/status, /api/v1/history, /api/v1/alerts)
app.include_router(api_router, prefix=settings.API_V1_STR)

# Rutas de compatibilidad directa (/api/status, /api/history)
app.include_router(api_router, prefix="/api")

# Montaje de archivos estáticos
static_dir_path = os.path.abspath(settings.STATIC_DIR)
if os.path.isdir(static_dir_path):
    app.mount("/static", StaticFiles(directory=static_dir_path), name="static")

    # Montajes directos adicionales para compatibilidad total
    css_dir = os.path.join(static_dir_path, "css")
    if os.path.isdir(css_dir):
        app.mount("/css", StaticFiles(directory=css_dir), name="css")

    js_dir = os.path.join(static_dir_path, "js")
    if os.path.isdir(js_dir):
        app.mount("/js", StaticFiles(directory=js_dir), name="js")


@app.get("/health", tags=["Health"], summary="Chequeo de salud del servicio")
def health_check():
    """Endpoint ligero para healthchecks en Docker y balanceadores."""
    return {"status": "healthy", "version": settings.VERSION}


@app.get("/", tags=["Frontend"], summary="Página principal")
def read_root():
    """Sirve la interfaz web estática principal."""
    index_file = os.path.join(settings.STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Bienvenido a Solar Monitor API. Visite /docs para ver la API."}
