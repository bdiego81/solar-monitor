import json
import logging
import urllib.request
import urllib.error
import asyncio
from typing import Dict, Any, Optional

from app.config import get_settings, Settings
from app.core.config_manager import config_manager

logger = logging.getLogger(__name__)


class TelegramService:
    """
    Servicio para el despacho de alertas y notificaciones a través de Telegram Bot API.
    Obtiene credenciales dinámicamente de ConfigManager o Settings.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    @property
    def bot_token(self) -> str:
        cfg = config_manager.get_config()
        return (cfg.telegram_bot_token or self.settings.TELEGRAM_BOT_TOKEN or "").strip()

    @property
    def chat_id(self) -> str:
        cfg = config_manager.get_config()
        return str(cfg.telegram_chat_id or self.settings.TELEGRAM_CHAT_ID or "").strip()

    @property
    def enabled(self) -> bool:
        cfg = config_manager.get_config()
        return bool(cfg.telegram_enabled and self.bot_token and self.chat_id)

    async def send_message(self, text: str, parse_mode: str = "HTML", token: Optional[str] = None, chat_id: Optional[str] = None) -> bool:
        """
        Envía un mensaje de texto formateado al chat o grupo configurado.
        """
        t = (token or self.bot_token).strip()
        c = str(chat_id or self.chat_id).strip()

        if not t or not c:
            logger.info("TelegramService: Notificaciones desactivadas o token/chat_id vacíos.")
            return False

        return await asyncio.to_thread(self._sync_send_message, text, parse_mode, t, c)

    def _sync_send_message(self, text: str, parse_mode: str, token: str, chat_id: str) -> bool:
        """Envío síncrono mediante HTTP POST a Telegram API."""
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    logger.info("Alerta de Telegram enviada exitosamente.")
                    return True
                logger.warning(f"Telegram API respondió con código {resp.status}")
                return False
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="ignore")
            logger.error(f"Error HTTP al enviar a Telegram ({e.code}): {err_msg}")
            return False
        except Exception as e:
            logger.error(f"Excepción al conectar con Telegram: {e}")
            return False

    async def test_connection(self, token: Optional[str] = None, chat_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Envía un mensaje de prueba para verificar credenciales y conectividad.
        """
        t = (token or self.bot_token).strip()
        c = str(chat_id or self.chat_id).strip()

        if not t or not c:
            return {
                "success": False,
                "error": "Debe especificar TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID para probar."
            }

        msg = (
            "☀️ <b>Solar Monitor Pro - Prueba de Conexión</b>\n\n"
            "✅ <i>¡Tu bot de Telegram ha sido vinculado correctamente!</i>\n\n"
            "Recibirás alertas críticas cuando se detecte:\n"
            "• Corte o restablecimiento de red eléctrica\n"
            "• Alta temperatura del inversor\n"
            "• Sobrecarga de potencia o batería crítica\n"
            "• Pérdida de telemetría (Watchdog)\n"
            "• Reporte diario a las 20:00 hrs"
        )
        ok = await self.send_message(msg, token=t, chat_id=c)
        return {
            "success": ok,
            "message": "Mensaje de prueba enviado exitosamente a tu Telegram" if ok else "No se pudo entregar el mensaje. Revisa el Token y Chat ID."
        }
