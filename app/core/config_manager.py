import os
import json
import logging
from typing import Optional, Callable, List
from pydantic import BaseModel, ConfigDict, Field

from app.config import get_settings

logger = logging.getLogger(__name__)


class AppDynamicConfig(BaseModel):
    """
    Configuración dinámica de credenciales, alertas, umbrales y Telegram persistida en data/config.json.
    Permite ser editada desde la interfaz web sin requerir bases de datos externas ni reinicio.
    """
    # Credenciales ShineMonitor
    shinemonitor_username: str = Field(default="", description="Usuario o email de ShineMonitor")
    shinemonitor_password: str = Field(default="", description="Contraseña de ShineMonitor")

    # Telegram
    telegram_bot_token: str = Field(default="", description="Token del bot de Telegram (@BotFather)")
    telegram_chat_id: str = Field(default="", description="Chat ID o Grupo de Telegram")
    telegram_enabled: bool = Field(default=True, description="Habilitar/Deshabilitar notificaciones")

    # Alertas Críticas
    alert_temp_max_c: float = Field(default=75.0, description="Umbral de alta temperatura (°C)")
    alert_overload_w: float = Field(default=6100.0, description="Potencia límite de sobrecarga (W)")
    alert_overload_pct: float = Field(default=85.0, description="Porcentaje límite de sobrecarga (%)")
    alert_low_battery_pct: float = Field(default=20.0, description="Nivel crítico de batería (%)")
    grid_restore_min_v: float = Field(default=180.0, description="Tensión mínima para considerar red restablecida (V)")

    # Alerta de Sistema (Watchdog)
    watchdog_timeout_minutes: int = Field(default=15, description="Minutos sin datos para disparar alerta de telemetría perdida")

    # Reporte Diario Programado
    daily_report_enabled: bool = Field(default=True, description="Habilitar reporte automático de cierre de jornada")
    daily_report_time: str = Field(default="20:00", description="Hora de envío del reporte diario (HH:MM)")

    # Anti-Spam
    alert_cooldown_minutes: int = Field(default=30, description="Minutos de cooldown entre alertas repetidas")

    @property
    def has_shinemonitor_credentials(self) -> bool:
        return bool(self.shinemonitor_username.strip() and self.shinemonitor_password.strip())

    @property
    def is_telegram_ready(self) -> bool:
        return bool(self.telegram_bot_token.strip() and self.telegram_chat_id.strip() and self.telegram_enabled)


class AppDynamicConfigPublic(BaseModel):
    """Vista de la configuración sin token de Telegram ni contraseña de ShineMonitor."""

    shinemonitor_username: str = ""
    shinemonitor_password_set: bool = False
    telegram_bot_token_set: bool = False
    telegram_chat_id: str = ""
    telegram_enabled: bool = True
    alert_temp_max_c: float = 75.0
    alert_overload_w: float = 6100.0
    alert_overload_pct: float = 85.0
    alert_low_battery_pct: float = 20.0
    grid_restore_min_v: float = 180.0
    watchdog_timeout_minutes: int = 15
    daily_report_enabled: bool = True
    daily_report_time: str = "20:00"
    alert_cooldown_minutes: int = 30

    @classmethod
    def from_stored(cls, cfg: AppDynamicConfig) -> "AppDynamicConfigPublic":
        payload = cfg.model_dump(exclude={"shinemonitor_password", "telegram_bot_token"})
        payload["shinemonitor_password_set"] = bool(cfg.shinemonitor_password.strip())
        payload["telegram_bot_token_set"] = bool(cfg.telegram_bot_token.strip())
        return cls(**payload)


class AppDynamicConfigUpdate(BaseModel):
    """
    Actualización parcial. Un secreto vacío o ausente conserva el valor ya guardado.
    """

    model_config = ConfigDict(extra="ignore")

    shinemonitor_username: Optional[str] = None
    shinemonitor_password: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    telegram_enabled: Optional[bool] = None
    alert_temp_max_c: Optional[float] = None
    alert_overload_w: Optional[float] = None
    alert_overload_pct: Optional[float] = None
    alert_low_battery_pct: Optional[float] = None
    grid_restore_min_v: Optional[float] = None
    watchdog_timeout_minutes: Optional[int] = None
    daily_report_enabled: Optional[bool] = None
    daily_report_time: Optional[str] = None
    alert_cooldown_minutes: Optional[int] = None


_SECRET_FIELDS = ("telegram_bot_token", "shinemonitor_password")


def merge_config(current: AppDynamicConfig, update: AppDynamicConfigUpdate) -> AppDynamicConfig:
    """Aplica solo los campos enviados. No borra secretos si llegan vacíos."""
    data = current.model_dump()
    for key, value in update.model_dump(exclude_unset=True).items():
        if key in _SECRET_FIELDS:
            if value is None or not str(value).strip():
                continue
            data[key] = str(value).strip()
            continue
        if value is None:
            continue
        data[key] = value
    return AppDynamicConfig(**data)


class ConfigManager:
    """
    Gestor singleton de persistencia para la configuración dinámica.
    Almacena los ajustes en un archivo JSON local 'data/config.json'.
    """

    def __init__(self, file_path: str = "data/config.json"):
        self.file_path = file_path
        self._config: Optional[AppDynamicConfig] = None
        self._listeners: List[Callable[[AppDynamicConfig], None]] = []
        self.load()

    def get_config(self) -> AppDynamicConfig:
        if self._config is None:
            self.load()
        return self._config

    def load(self) -> AppDynamicConfig:
        """Carga la configuración desde el archivo JSON o crea el archivo inicial."""
        os.makedirs(os.path.dirname(os.path.abspath(self.file_path)), exist_ok=True)
        settings = get_settings()

        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    # Migración / Fallback si no tiene credenciales en el json pero sí en .env
                    if not data.get("shinemonitor_username") and settings.SHINEMONITOR_USERNAME:
                        data["shinemonitor_username"] = settings.SHINEMONITOR_USERNAME
                    if not data.get("shinemonitor_password") and settings.SHINEMONITOR_PASSWORD:
                        data["shinemonitor_password"] = settings.SHINEMONITOR_PASSWORD
                    if not data.get("telegram_bot_token") and settings.TELEGRAM_BOT_TOKEN:
                        data["telegram_bot_token"] = settings.TELEGRAM_BOT_TOKEN
                    if not data.get("telegram_chat_id") and settings.TELEGRAM_CHAT_ID:
                        data["telegram_chat_id"] = settings.TELEGRAM_CHAT_ID

                    self._config = AppDynamicConfig(**data)
                    logger.info(f"Configuración cargada desde {self.file_path}")
                    return self._config
            except Exception as e:
                logger.error(f"Error al leer {self.file_path}, usando valores por defecto: {e}")

        # Si no existe, inicializar con variables de entorno de .env o defaults
        self._config = AppDynamicConfig(
            shinemonitor_username=settings.SHINEMONITOR_USERNAME or "",
            shinemonitor_password=settings.SHINEMONITOR_PASSWORD or "",
            telegram_bot_token=settings.TELEGRAM_BOT_TOKEN or "",
            telegram_chat_id=settings.TELEGRAM_CHAT_ID or "",
            telegram_enabled=settings.TELEGRAM_ENABLED,
            alert_temp_max_c=75.0,
            alert_overload_w=6100.0,
            alert_overload_pct=85.0,
            alert_low_battery_pct=20.0,
            grid_restore_min_v=180.0,
            watchdog_timeout_minutes=15,
            daily_report_enabled=True,
            daily_report_time="20:00",
            alert_cooldown_minutes=settings.ALERT_COOLDOWN_MINUTES or 30
        )
        self.save(self._config)
        return self._config

    def save(self, new_config: AppDynamicConfig) -> bool:
        """Persiste la configuración en disco y notifica a los componentes suscritos."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.file_path)), exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(new_config.model_dump_json(indent=2))
            self._config = new_config
            logger.info(f"Configuración guardada exitosamente en {self.file_path}")

            # Notificar listeners en caliente
            for listener in self._listeners:
                try:
                    listener(self._config)
                except Exception as ex:
                    logger.warning(f"Error en listener de configuración: {ex}")
            return True
        except Exception as e:
            logger.error(f"Error al escribir en {self.file_path}: {e}")
            return False

    def on_change(self, callback: Callable[[AppDynamicConfig], None]):
        """Registra una función callback para ser llamada cuando la configuración cambie."""
        self._listeners.append(callback)


# Singleton
config_manager = ConfigManager()
