import datetime
from typing import List, Dict


def calculate_temperature(load_pct: float) -> float:
    """
    Estima la temperatura del inversor en función del porcentaje de carga.
    Fórmula lineal: base de 30°C + hasta 45°C adicionales a 100% de carga.
    """
    pct = max(0.0, float(load_pct or 0.0))
    return round(30.0 + ((pct / 100.0) * 45.0), 1)


def calculate_step_energy_wh(power_w: float, interval_minutes: float = 5.0) -> float:
    """
    Calcula los Vatios-hora (Wh) acumulados en un intervalo temporal específico.
    Por defecto, ShineMonitor reporta métricas cada 5 minutos (5 / 60 h).
    """
    interval_hours = float(interval_minutes) / 60.0
    return float(power_w or 0.0) * interval_hours


def wh_to_kwh(total_wh: float, decimals: int = 2) -> float:
    """
    Convierte Vatios-hora a Kilovatios-hora redondeado.
    """
    return round(float(total_wh or 0.0) / 1000.0, decimals)


def generate_dates_list(start_str: str, end_str: str, max_days: int = 15) -> List[str]:
    """
    Genera una lista de fechas en formato 'YYYY-MM-DD' entre start_date y end_date,
    limitada a max_days y sin superar la fecha actual.
    """
    try:
        start_dt = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
        end_dt = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return []

    today = datetime.date.today()
    if end_dt > today:
        end_dt = today

    delta = (end_dt - start_dt).days
    if delta < 0:
        return []

    delta = min(delta, max_days - 1)
    return [(start_dt + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(delta + 1)]


def evaluate_alerts(grid_voltage: float, load_pct: float, battery_pct: float) -> Dict[str, bool]:
    """
    Evalúa las condiciones operativas para generar banderas de alerta:
    - grid_loss: corte de suministro eléctrico de red (0 V)
    - overload_risk: consumo cercano al límite del inversor (>= 85%)
    - low_battery: nivel crítico de batería (<= 20%)
    """
    return {
        "grid_loss": float(grid_voltage or 0.0) == 0.0,
        "overload_risk": float(load_pct or 0.0) >= 85.0,
        "low_battery": float(battery_pct or 0.0) <= 20.0,
    }
