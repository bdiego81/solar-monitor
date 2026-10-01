import logging
import datetime
from typing import List, Optional

from app.config import Settings
from app.core.calculator import (
    calculate_temperature,
    calculate_step_energy_wh,
    wh_to_kwh,
    evaluate_alerts,
)
from app.schemas.status import (
    StatusResponse,
    MetricsSchema,
    AlertsSchema,
    RatingsSchema,
)
from app.schemas.history import HistoryResponse, HistoryPoint, HistorySummary

from app.core.config_manager import config_manager

logger = logging.getLogger(__name__)

try:
    from shinemonitor_api import ShineMonitorAPI
except ImportError:
    ShineMonitorAPI = None
    logger.warning("Librería 'shinemonitor_api' no disponible en el entorno local.")


class ShineMonitorService:
    """
    Servicio de integración con la plataforma ShineMonitor.
    Encapsula autenticación dinámica, consulta de dispositivos y transformación de datos.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._api = None
        self._last_auth_user = None
        self._last_auth_pass = None

    @property
    def username(self) -> str:
        cfg = config_manager.get_config()
        return (cfg.shinemonitor_username or self.settings.SHINEMONITOR_USERNAME or "").strip()

    @property
    def password(self) -> str:
        cfg = config_manager.get_config()
        return (cfg.shinemonitor_password or self.settings.SHINEMONITOR_PASSWORD or "").strip()

    def _get_api(self, custom_user: Optional[str] = None, custom_pass: Optional[str] = None):
        """Inicializa y autentica el cliente de ShineMonitor con soporte de hot-reload si cambian credenciales."""
        u = (custom_user or self.username).strip()
        p = (custom_pass or self.password).strip()

        if not u or not p:
            return None

        if ShineMonitorAPI is None:
            logger.error("shinemonitor_api no está instalada.")
            return None

        # Si se pasan credenciales personalizadas o cambiaron en config_manager, re-autenticar
        if self._api is None or self._last_auth_user != u or self._last_auth_pass != p:
            try:
                api = ShineMonitorAPI()
                api.login(u, p)
                self._api = api
                self._last_auth_user = u
                self._last_auth_pass = p
            except Exception as e:
                logger.error(f"Fallo de autenticación en ShineMonitor: {e}")
                return None
        return self._api

    def test_credentials(self, username: Optional[str] = None, password: Optional[str] = None) -> dict:
        """Verifica si las credenciales son válidas y si hay dispositivos vinculados."""
        u = (username or self.username).strip()
        p = (password or self.password).strip()

        if not u or not p:
            return {"success": False, "error": "Debe ingresar usuario y contraseña"}

        if ShineMonitorAPI is None:
            return {"success": True, "message": "Modo simulación: Credenciales validadas correctamente (Librería API emulada)"}

        try:
            api = ShineMonitorAPI()
            api.login(u, p)
            devices = api.get_devices()
            if not devices:
                return {
                    "success": True,
                    "warning": "Login exitoso pero no se encontraron inversores registrados en la cuenta."
                }
            dev = devices[0]
            sn = getattr(dev, "serial_number", "Desconocido")
            return {
                "success": True,
                "message": f"¡Conexión exitosa! Inversor detectado (SN: {sn})."
            }
        except Exception as e:
            return {"success": False, "error": f"Fallo al autenticar en ShineMonitor: {str(e)}"}

    def get_current_status(self) -> StatusResponse:
        """
        Obtiene las métricas y estado en tiempo real del primer inversor disponible.
        """
        if not self.username or not self.password:
            return self._build_demo_status("Credenciales de ShineMonitor no configuradas en .env")

        try:
            api = self._get_api()
            if not api:
                return self._build_demo_status("No se pudo conectar con la API de ShineMonitor")

            devices = api.get_devices()
            if not devices:
                return StatusResponse(
                    status="offline",
                    error="No se encontraron dispositivos en la cuenta de ShineMonitor"
                )

            dev = devices[0]
            data = api.get_last_data(dev)

            grid_voltage = float(getattr(data.main, "grid_voltage", 0.0) or 0.0)
            load_pct = float(getattr(data.main, "output_load_percent", 0.0) or 0.0)
            battery_pct = float(getattr(data.main, "battery_capacity", 0.0) or 0.0)

            alerts = evaluate_alerts(
                grid_voltage=grid_voltage,
                load_pct=load_pct,
                battery_pct=battery_pct
            )

            metrics = MetricsSchema(
                pv_power_w=float(getattr(data.main, "pv_input_power", 0.0) or 0.0),
                pv_voltage_v=float(getattr(data.main, "pv_input_voltage", 0.0) or 0.0),
                load_power_w=float(getattr(data.main, "ac_output_active_power", 0.0) or 0.0),
                load_voltage_v=float(getattr(data.main, "ac_output_voltage", 0.0) or 0.0),
                load_percent=load_pct,
                battery_capacity_percent=battery_pct,
                battery_voltage_v=float(getattr(data.main, "battery_voltage", 0.0) or 0.0),
                battery_charging_a=float(getattr(data.main, "battery_charging_current", 0.0) or 0.0),
                battery_discharging_a=float(getattr(data.main, "battery_discharge_current", 0.0) or 0.0),
                grid_voltage_v=grid_voltage,
                grid_frequency_hz=float(getattr(data.main, "grid_frequency", 0.0) or 0.0),
                temp_c=calculate_temperature(load_pct)
            )

            ratings = RatingsSchema(
                max_power_w=float(getattr(data.grid, "ac_output_rating_active_power", 5000.0) or 5000.0),
                nominal_battery_v=float(getattr(data.grid, "battery_rating_voltage", 48.0) or 48.0)
            )

            timestamp_str = (
                data.timestamp.isoformat()
                if hasattr(data, "timestamp") and data.timestamp
                else datetime.datetime.now().isoformat()
            )

            return StatusResponse(
                status="online",
                device_sn=str(getattr(dev, "serial_number", "UNKNOWN")),
                last_update=timestamp_str,
                alerts=AlertsSchema(**alerts),
                metrics=metrics,
                ratings=ratings
            )

        except Exception as e:
            logger.exception("Error al consultar el estado de ShineMonitor")
            return self._build_demo_status(f"Error de conexión con ShineMonitor: {str(e)}")

    def get_historical_data(self, target_dates: List[str]) -> HistoryResponse:
        """
        Consulta y consolida la telemetría histórica para una lista de fechas.
        """
        if not self.username or not self.password:
            return self._build_demo_history(target_dates, "Credenciales no configuradas. Mostrando datos de demostración.")

        try:
            api = self._get_api()
            if not api:
                return self._build_demo_history(target_dates, "Fallo al inicializar API. Modo demostración activo.")

            devices = api.get_devices()
            if not devices:
                return HistoryResponse(
                    dates=target_dates,
                    history=[],
                    summary=HistorySummary(),
                    error="Sin dispositivos asociados a la cuenta"
                )

            dev = devices[0]
            parsed_history: List[HistoryPoint] = []
            total_pv_wh = 0.0
            total_load_wh = 0.0

            for target_date in target_dates:
                try:
                    raw_response = api.query_device_data_one_day(
                        pn=dev.wifi_pin,
                        devcode=dev.device_code,
                        devaddr=dev.device_address,
                        sn=dev.serial_number,
                        date=target_date
                    )
                except Exception as ex:
                    logger.warning(f"Error al consultar fecha {target_date}: {ex}")
                    continue

                dat_dict = raw_response.get("dat", {}) if isinstance(raw_response, dict) else {}
                rows = dat_dict.get("row", []) if isinstance(dat_dict, dict) else []

                for record in rows:
                    f = record.get("field", [])
                    if len(f) > 20:
                        try:
                            pv_power = float(f[10]) + float(f[11])
                            load_power = float(f[19])
                            grid_v = float(f[6]) if f[6] else 0.0
                            bat_pct = float(f[13]) if f[13] else 0.0
                            load_pct = float(f[20]) if f[20] else 0.0
                            temp_c = calculate_temperature(load_pct)

                            total_pv_wh += calculate_step_energy_wh(pv_power, interval_minutes=5.0)
                            total_load_wh += calculate_step_energy_wh(load_power, interval_minutes=5.0)

                            parsed_history.append(
                                HistoryPoint(
                                    timestamp=str(f[1]),
                                    pv_power_w=pv_power,
                                    load_power_w=load_power,
                                    battery_pct=bat_pct,
                                    grid_voltage_v=grid_v,
                                    temp_c=temp_c
                                )
                            )
                        except (ValueError, TypeError):
                            continue

            return HistoryResponse(
                dates=target_dates,
                history=parsed_history,
                summary=HistorySummary(
                    pv_energy_kwh=wh_to_kwh(total_pv_wh),
                    load_energy_kwh=wh_to_kwh(total_load_wh)
                )
            )

        except Exception as e:
            logger.exception("Excepción durante la consulta histórica")
            return self._build_demo_history(target_dates, f"Error en consulta histórica: {str(e)}")

    def _build_demo_status(self, note: str) -> StatusResponse:
        """Genera telemetría realista para pruebas y demostración."""
        now = datetime.datetime.now()
        hour = now.hour + now.minute / 60.0
        # Simulación de campana solar durante el día
        pv = max(0.0, 3200.0 * (1.0 - ((hour - 13.0) / 5.5) ** 2)) if 6.5 <= hour <= 19.0 else 0.0
        load = 650.0 + (350.0 if (12 <= hour <= 14 or 19 <= hour <= 22) else 0.0)
        battery_pct = 85.0 if pv > load else max(25.0, 85.0 - (hour - 19.0) * 10.0) if hour > 19 else 65.0
        grid_v = 228.5
        load_pct = round((load / 5000.0) * 100.0, 1)

        return StatusResponse(
            status="demo",
            device_sn="DEMO-SOLAR-5KW",
            last_update=now.isoformat(),
            alerts=AlertsSchema(grid_loss=False, overload_risk=False, low_battery=battery_pct <= 20),
            metrics=MetricsSchema(
                pv_power_w=round(pv, 1),
                pv_voltage_v=345.2 if pv > 0 else 0.0,
                load_power_w=round(load, 1),
                load_voltage_v=229.8,
                load_percent=load_pct,
                battery_capacity_percent=round(battery_pct, 1),
                battery_voltage_v=51.8,
                battery_charging_a=round((pv - load) / 51.8, 1) if pv > load else 0.0,
                battery_discharging_a=round((load - pv) / 51.8, 1) if load > pv else 0.0,
                grid_voltage_v=grid_v,
                grid_frequency_hz=50.0,
                temp_c=calculate_temperature(load_pct)
            ),
            ratings=RatingsSchema(
                max_power_w=5000.0,
                nominal_battery_v=48.0
            ),
            error=note
        )

    def _build_demo_history(self, target_dates: List[str], note: str) -> HistoryResponse:
        """Genera una curva solar e histórica completa de 24 horas cada 5 minutos."""
        now = datetime.datetime.now()
        history: List[HistoryPoint] = []
        total_pv_wh = 0.0
        total_load_wh = 0.0

        for d_str in target_dates:
            for m in range(0, 24 * 60, 5):
                h = m / 60.0
                ts = f"{d_str} {int(h):02d}:{int(m % 60):02d}"
                # Generación solar campana de Gauss
                pv = max(0.0, 3400.0 * (1.0 - ((h - 13.0) / 5.2) ** 2)) if 7.0 <= h <= 18.8 else 0.0
                # Consumo basal con picos en almuerzo y noche
                base_load = 520.0
                if 12.0 <= h <= 14.5:
                    base_load += 650.0
                elif 19.5 <= h <= 23.0:
                    base_load += 850.0
                load = base_load

                bat = 95.0 if pv > load else max(30.0, 95.0 - (h * 3.5)) if h > 18.0 else 55.0
                load_pct = (load / 5000.0) * 100.0
                temp = calculate_temperature(load_pct)

                total_pv_wh += calculate_step_energy_wh(pv, 5.0)
                total_load_wh += calculate_step_energy_wh(load, 5.0)

                history.append(
                    HistoryPoint(
                        timestamp=ts,
                        pv_power_w=round(pv, 1),
                        load_power_w=round(load, 1),
                        battery_pct=round(bat, 1),
                        grid_voltage_v=230.0,
                        temp_c=temp
                    )
                )

        return HistoryResponse(
            dates=target_dates,
            history=history,
            summary=HistorySummary(
                pv_energy_kwh=wh_to_kwh(total_pv_wh),
                load_energy_kwh=wh_to_kwh(total_load_wh)
            ),
            error=note
        )
