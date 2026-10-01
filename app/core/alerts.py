import datetime
import logging
from typing import Dict, Any, Optional

from app.core.config_manager import config_manager, AppDynamicConfig
from app.schemas.status import StatusResponse
from app.services.telegram import TelegramService

logger = logging.getLogger(__name__)


class DailyTracker:
    """Mantiene las estadísticas acumuladas de la jornada en curso."""

    def __init__(self):
        self.date: str = datetime.date.today().strftime("%Y-%m-%d")
        self.grid_outages_count: int = 0
        self.min_battery_pct: float = 100.0
        self.daily_report_sent: bool = False

    def roll_day_if_needed(self, current_battery: float = 100.0):
        """Reinicia las estadísticas automáticamente al cambiar la fecha de medianoche."""
        today = datetime.date.today().strftime("%Y-%m-%d")
        if self.date != today:
            logger.info(f"Nuevo día detectado ({today}). Reiniciando estadísticas diarias.")
            self.date = today
            self.grid_outages_count = 0
            self.min_battery_pct = float(current_battery)
            self.daily_report_sent = False

    def record_battery(self, battery_pct: float):
        if battery_pct is not None and battery_pct > 0:
            if battery_pct < self.min_battery_pct:
                self.min_battery_pct = round(float(battery_pct), 1)

    def record_outage(self):
        self.grid_outages_count += 1
        logger.info(f"Corte de red contabilizado. Total hoy: {self.grid_outages_count}")


class AlertState:
    """Mantiene el estado y marca temporal de una condición de alerta específica."""
    def __init__(self, key: str, name: str):
        self.key = key
        self.name = name
        self.is_active = False
        self.last_sent_at: Optional[datetime.datetime] = None

    def should_notify_active(self, cooldown_minutes: int) -> bool:
        """Determina si se debe enviar notificación de activación o recordatorio."""
        now = datetime.datetime.now()
        if not self.is_active:
            return True
        if self.last_sent_at:
            elapsed = (now - self.last_sent_at).total_seconds() / 60.0
            if elapsed >= cooldown_minutes:
                return True
        return False

    def mark_sent(self):
        self.is_active = True
        self.last_sent_at = datetime.datetime.now()

    def mark_resolved(self) -> bool:
        if self.is_active:
            self.is_active = False
            self.last_sent_at = None
            return True
        return False


class AlertManager:
    """
    Gestor central de evaluación de alertas, Watchdog y Reporte Diario programado.
    Obtiene dinámicamente umbrales de ConfigManager (data/config.json).
    """

    def __init__(self):
        self.telegram = TelegramService()
        self.daily_tracker = DailyTracker()

        # Marca de tiempo de la última telemetría válida recibida
        self.last_valid_telemetry_time: datetime.datetime = datetime.datetime.now()

        # Estados de alerta
        self.states: Dict[str, AlertState] = {
            "high_temperature": AlertState("high_temperature", "Temperatura Alta en Inversor"),
            "grid_loss": AlertState("grid_loss", "Corte de Red Eléctrica"),
            "overload_risk": AlertState("overload_risk", "Riesgo de Sobrecarga"),
            "low_battery": AlertState("low_battery", "Nivel Crítico de Batería"),
            "telemetry_loss": AlertState("telemetry_loss", "Pérdida de Telemetría (Watchdog)"),
        }

    @property
    def config(self) -> AppDynamicConfig:
        return config_manager.get_config()

    async def evaluate_status(self, status: StatusResponse, service_instance=None) -> Dict[str, Any]:
        """
        Evalúa el estado actual del inversor, watchdog y chequeo de reporte diario.
        """
        now = datetime.datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        cfg = self.config
        cooldown = cfg.alert_cooldown_minutes

        if not _is_live_telemetry(status):
            # Demo, offline o sin datos: no contar la lectura ni disparar alertas de planta.
            await self._check_watchdog(now, cfg)
            state_name = status.status if status else "desconocido"
            return {
                "evaluated": False,
                "reason": f"Sin telemetría real del inversor (estado: {state_name})",
            }

        metrics = status.metrics
        alerts = status.alerts
        sn = status.device_sn or "Inversor"

        # Registrar telemetría válida para el Watchdog
        self.last_valid_telemetry_time = now
        telemetry_state = self.states["telemetry_loss"]
        if telemetry_state.mark_resolved():
            msg = (
                f"✅ <b>TELEMETRÍA RESTABLECIDA</b>\n\n"
                f"🔌 <b>Equipo:</b> {sn}\n"
                f"📡 Se ha reanudado la recepción de datos en tiempo real de ShineMonitor.\n"
                f"⏱️ <i>{now_str}</i>"
            )
            await self.telegram.send_message(msg)

        # Actualizar acumuladores diarios (batería mínima y cambio de día)
        self.daily_tracker.roll_day_if_needed(current_battery=metrics.battery_capacity_percent)
        self.daily_tracker.record_battery(metrics.battery_capacity_percent)

        # 1. ALERTA: ALTA TEMPERATURA (> alert_temp_max_c, ej: 75°C)
        temp_c = metrics.temp_c or 0.0
        temp_state = self.states["high_temperature"]
        if temp_c >= cfg.alert_temp_max_c:
            if temp_state.should_notify_active(cooldown):
                msg = (
                    f"🚨 <b>ALERTA CRÍTICA: TEMPERATURA ELEVADA</b>\n\n"
                    f"🔌 <b>Equipo:</b> {sn}\n"
                    f"🌡️ <b>Temperatura actual:</b> <code>{temp_c}°C</code> (Límite: {cfg.alert_temp_max_c}°C)\n"
                    f"⚡ <b>Consumo hogar:</b> {round(metrics.load_power_w)} W ({metrics.load_percent}%)\n"
                    f"☀️ <b>Generación solar:</b> {round(metrics.pv_power_w)} W\n"
                    f"⏱️ <i>{now_str}</i>"
                )
                await self.telegram.send_message(msg)
                temp_state.mark_sent()
        else:
            if temp_state.mark_resolved():
                msg = (
                    f"✅ <b>TEMPERATURA NORMALIZADA</b>\n\n"
                    f"🔌 <b>Equipo:</b> {sn}\n"
                    f"🌡️ Temperatura actual: <code>{temp_c}°C</code>\n"
                    f"El inversor ha retornado a su temperatura segura de operación.\n"
                    f"⏱️ <i>{now_str}</i>"
                )
                await self.telegram.send_message(msg)

        # 2. ALERTA: CORTE DE RED ELÉCTRICA (pasa a 0V) Y RESTABLECIMIENTO (> 180V)
        grid_v = metrics.grid_voltage_v or 0.0
        grid_state = self.states["grid_loss"]
        is_grid_loss = (grid_v == 0.0) or alerts.grid_loss

        if is_grid_loss:
            if not grid_state.is_active:
                # Transición a corte detectada: contabilizar en el reporte diario
                self.daily_tracker.record_outage()

            if grid_state.should_notify_active(cooldown):
                msg = (
                    f"⚡ <b>ALERTA CRÍTICA: CORTE DE RED ELÉCTRICA</b>\n\n"
                    f"🔌 <b>Equipo:</b> {sn}\n"
                    f"⚠️ <b>Tensión de Red:</b> <code>0 V</code> (Suministro Caído)\n"
                    f"🔋 <b>Batería de Respaldo:</b> {metrics.battery_capacity_percent}% ({metrics.battery_voltage_v} V)\n"
                    f"🏠 <b>Consumo en Isla:</b> {round(metrics.load_power_w)} W\n"
                    f"⏱️ <i>{now_str}</i>"
                )
                await self.telegram.send_message(msg)
                grid_state.mark_sent()
        elif grid_v >= cfg.grid_restore_min_v:
            # Solo consideramos restablecida si supera el umbral de tensión mínima (ej: 180V)
            if grid_state.mark_resolved():
                msg = (
                    f"✅ <b>RED ELÉCTRICA RESTABLECIDA</b>\n\n"
                    f"🔌 <b>Equipo:</b> {sn}\n"
                    f"⚡ <b>Tensión detectada:</b> <code>{grid_v} V</code> ({metrics.grid_frequency_hz} Hz)\n"
                    f"El inversor ha sincronizado nuevamente con la red de distribución pública.\n"
                    f"⏱️ <i>{now_str}</i>"
                )
                await self.telegram.send_message(msg)

        # 3. ALERTA: RIESGO DE SOBRECARGA (>= 6100W o >= 85%)
        load_w = metrics.load_power_w or 0.0
        load_pct = metrics.load_percent or 0.0
        overload_state = self.states["overload_risk"]
        is_overload = (load_w >= cfg.alert_overload_w) or (load_pct >= cfg.alert_overload_pct)

        if is_overload:
            if overload_state.should_notify_active(cooldown):
                msg = (
                    f"⚠️ <b>ALERTA CRÍTICA: RIESGO DE SOBRECARGA</b>\n\n"
                    f"🔌 <b>Equipo:</b> {sn}\n"
                    f"📊 <b>Potencia de Consumo:</b> <code>{round(load_w)} W</code> (Límite: {cfg.alert_overload_w} W)\n"
                    f"⚡ <b>Demanda de Carga:</b> <code>{load_pct}%</code>\n"
                    f"Reduzca artefactos de alto consumo para evitar desconexión del inversor.\n"
                    f"⏱️ <i>{now_str}</i>"
                )
                await self.telegram.send_message(msg)
                overload_state.mark_sent()
        else:
            if overload_state.mark_resolved():
                msg = (
                    f"✅ <b>CONSUMO NORMALIZADO</b>\n\n"
                    f"🔌 <b>Equipo:</b> {sn}\n"
                    f"📊 Carga actual: <code>{round(load_w)} W</code> ({load_pct}%)\n"
                    f"⏱️ <i>{now_str}</i>"
                )
                await self.telegram.send_message(msg)

        # 4. ALERTA: BATERÍA CRÍTICA (<= 20%)
        bat_pct = metrics.battery_capacity_percent or 0.0
        bat_state = self.states["low_battery"]
        if bat_pct <= cfg.alert_low_battery_pct:
            if bat_state.should_notify_active(cooldown):
                msg = (
                    f"🪫 <b>ALERTA CRÍTICA: BATERÍA EN NIVEL MÍNIMO</b>\n\n"
                    f"🔌 <b>Equipo:</b> {sn}\n"
                    f"🔋 <b>Nivel de Carga:</b> <code>{bat_pct}%</code> (Umbral: {cfg.alert_low_battery_pct}%)\n"
                    f"⚡ <b>Tensión Banco:</b> {metrics.battery_voltage_v} V\n"
                    f"Apague cargas no prioritarias para evitar apagado por descarga profunda.\n"
                    f"⏱️ <i>{now_str}</i>"
                )
                await self.telegram.send_message(msg)
                bat_state.mark_sent()
        else:
            if bat_state.mark_resolved():
                msg = (
                    f"✅ <b>BATERÍA RECUPERADA</b>\n\n"
                    f"🔌 <b>Equipo:</b> {sn}\n"
                    f"🔋 Nivel de batería actual: <code>{bat_pct}%</code> ({metrics.battery_voltage_v} V)\n"
                    f"⏱️ <i>{now_str}</i>"
                )
                await self.telegram.send_message(msg)

        # 5. REPORTE DIARIO PROGRAMADO (20:00 hrs)
        if service_instance:
            await self._check_daily_report(now, cfg, status, service_instance)

        return {
            "evaluated": True,
            "active_alerts": [k for k, v in self.states.items() if v.is_active],
            "daily_stats": {
                "grid_outages": self.daily_tracker.grid_outages_count,
                "min_battery_pct": self.daily_tracker.min_battery_pct,
                "daily_report_sent": self.daily_tracker.daily_report_sent
            }
        }

    async def _check_watchdog(self, now: datetime.datetime, cfg: AppDynamicConfig):
        """Verifica si ha expirado el tiempo de telemetría sin recibir datos."""
        elapsed_minutes = (now - self.last_valid_telemetry_time).total_seconds() / 60.0
        watchdog_state = self.states["telemetry_loss"]

        if elapsed_minutes >= cfg.watchdog_timeout_minutes:
            if watchdog_state.should_notify_active(cfg.alert_cooldown_minutes):
                last_time_str = self.last_valid_telemetry_time.strftime("%H:%M:%S")
                msg = (
                    f"📡 <b>ALERTA DE SISTEMA: PÉRDIDA DE TELEMETRÍA (WATCHDOG)</b>\n\n"
                    f"⚠️ <b>Han transcurrido {int(elapsed_minutes)} minutos sin recibir datos de ShineMonitor.</b>\n"
                    f"Última actualización recibida a las: <code>{last_time_str}</code>\n\n"
                    f"Por favor compruebe:\n"
                    f"1. La conexión WiFi / Datalogger del inversor.\n"
                    f"2. El estado de los servidores de ShineMonitor."
                )
                await self.telegram.send_message(msg)
                watchdog_state.mark_sent()

    async def _check_daily_report(self, now: datetime.datetime, cfg: AppDynamicConfig, current_status: StatusResponse, service):
        """Verifica y envía el reporte diario a la hora configurada (ej. 20:00)."""
        if not cfg.daily_report_enabled or self.daily_tracker.daily_report_sent:
            return

        try:
            target_h, target_m = map(int, cfg.daily_report_time.split(":"))
        except Exception:
            target_h, target_m = 20, 0

        # Disparar si ya es la hora programada
        if now.hour == target_h and now.minute >= target_m:
            try:
                today_str = datetime.date.today().strftime("%Y-%m-%d")
                history_resp = service.get_historical_data([today_str])
                if history_resp.error:
                    logger.warning(f"Reporte diario omitido: {history_resp.error}")
                    return

                pv_kwh = history_resp.summary.pv_energy_kwh if history_resp.summary else 0.0
                load_kwh = history_resp.summary.load_energy_kwh if history_resp.summary else 0.0

                current_bat = current_status.metrics.battery_capacity_percent if current_status.metrics else 0.0
                min_bat = self.daily_tracker.min_battery_pct
                outages = self.daily_tracker.grid_outages_count
                sn = current_status.device_sn or "Inversor"

                report_msg = (
                    f"📋 <b>RESUMEN DE CIERRE DE JORNADA</b>\n"
                    f"📅 <i>{today_str} ({cfg.daily_report_time} hrs)</i>\n"
                    f"🔌 <b>Equipo:</b> {sn}\n\n"
                    f"☀️ <b>Generación Solar Hoy:</b> <code>{pv_kwh} kWh</code>\n"
                    f"🏠 <b>Consumo Hogar Hoy:</b> <code>{load_kwh} kWh</code>\n\n"
                    f"🔋 <b>Batería:</b>\n"
                    f"   • Nivel Actual: <b>{current_bat}%</b>\n"
                    f"   • Mínimo Registrado: <b>{min_bat}%</b>\n\n"
                    f"⚡ <b>Cortes de Red Hoy:</b> <b>{outages} cortes</b> registrados\n\n"
                    f"<i>Monitoreo solar continuo y reporte automático completado.</i>"
                )

                sent = await self.telegram.send_message(report_msg)
                if sent:
                    self.daily_tracker.daily_report_sent = True
                    logger.info("Reporte diario de las 20:00 enviado exitosamente a Telegram.")
            except Exception as e:
                logger.error(f"Fallo al generar reporte diario: {e}")

    async def trigger_daily_report_now(self, service, current_status: StatusResponse) -> Dict[str, Any]:
        """Permite disparar el reporte diario inmediatamente para pruebas."""
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        history_resp = service.get_historical_data([today_str])
        if history_resp.error:
            return {"success": False, "error": history_resp.error}

        pv_kwh = history_resp.summary.pv_energy_kwh if history_resp.summary else 0.0
        load_kwh = history_resp.summary.load_energy_kwh if history_resp.summary else 0.0

        current_bat = current_status.metrics.battery_capacity_percent if current_status.metrics else 0.0
        min_bat = self.daily_tracker.min_battery_pct
        outages = self.daily_tracker.grid_outages_count
        sn = current_status.device_sn or "Inversor"

        report_msg = (
            f"📋 <b>PRUEBA DE REPORTE DE JORNADA</b>\n"
            f"📅 <i>{today_str}</i>\n"
            f"🔌 <b>Equipo:</b> {sn}\n\n"
            f"☀️ <b>Generación Solar:</b> <code>{pv_kwh} kWh</code>\n"
            f"🏠 <b>Consumo Hogar:</b> <code>{load_kwh} kWh</code>\n\n"
            f"🔋 <b>Batería:</b>\n"
            f"   • Nivel Actual: <b>{current_bat}%</b>\n"
            f"   • Mínimo Registrado Hoy: <b>{min_bat}%</b>\n\n"
            f"⚡ <b>Cortes de Red Hoy:</b> <b>{outages} cortes</b> registrados"
        )
        ok = await self.telegram.send_message(report_msg)
        return {"success": ok, "message": "Reporte diario enviado a Telegram" if ok else "Fallo al enviar reporte"}

    def get_active_alerts(self) -> Dict[str, Any]:
        return {
            key: {
                "name": state.name,
                "is_active": state.is_active,
                "last_sent_at": state.last_sent_at.isoformat() if state.last_sent_at else None
            }
            for key, state in self.states.items()
        }


def _is_live_telemetry(status: Optional[StatusResponse]) -> bool:
    """Solo un inversor en línea es una lectura real. Demo y offline no disparan alertas."""
    return bool(status and status.status == "online" and status.metrics)


# Instancia singleton
alert_manager = AlertManager()
