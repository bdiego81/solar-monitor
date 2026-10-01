"""
External service integrations.
"""
from app.services.shinemonitor import ShineMonitorService
from app.services.telegram import TelegramService

__all__ = ["ShineMonitorService", "TelegramService"]
