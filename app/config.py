from functools import lru_cache
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración global de la aplicación gestionada mediante Pydantic Settings.
    Carga variables desde el entorno del sistema y opcionalmente desde un archivo .env.
    """
    PROJECT_NAME: str = "Solar Monitor API"
    VERSION: str = "3.0.0"
    DEBUG: bool = False
    
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    API_V1_STR: str = "/api/v1"
    STATIC_DIR: str = "static"
    
    # Credenciales ShineMonitor
    SHINEMONITOR_USERNAME: str = ""
    SHINEMONITOR_PASSWORD: str = ""
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Configuración de Notificaciones en Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_ENABLED: bool = True
    
    # Umbrales y frecuencia de alertas
    ALERT_TEMP_MAX_C: float = 65.0
    ALERT_OVERLOAD_PCT: float = 85.0
    ALERT_LOW_BATTERY_PCT: float = 20.0
    ALERT_CHECK_INTERVAL_SECONDS: int = 60
    ALERT_COOLDOWN_MINUTES: int = 30

    @property
    def has_credentials(self) -> bool:
        """Indica si las credenciales de ShineMonitor han sido configuradas."""
        return bool(self.SHINEMONITOR_USERNAME and self.SHINEMONITOR_PASSWORD)

    @property
    def is_telegram_configured(self) -> bool:
        """Indica si el bot de Telegram tiene token y chat_id válidos."""
        return bool(self.TELEGRAM_BOT_TOKEN and self.TELEGRAM_CHAT_ID and self.TELEGRAM_ENABLED)


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna una instancia singleton cacheada de la configuración.
    """
    return Settings()
