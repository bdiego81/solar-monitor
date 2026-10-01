from typing import Optional
from pydantic import BaseModel, Field


class AlertsSchema(BaseModel):
    """Banderas de alerta operativa del inversor."""
    grid_loss: bool = Field(default=False, description="Corte de red eléctrica")
    overload_risk: bool = Field(default=False, description="Sobrecarga en inversor (>=85%)")
    low_battery: bool = Field(default=False, description="Nivel crítico de batería (<=20%)")


class MetricsSchema(BaseModel):
    """Telemetría en tiempo real del sistema solar y red."""
    pv_power_w: float = Field(default=0.0, description="Potencia fotovoltaica en Vatios")
    pv_voltage_v: float = Field(default=0.0, description="Tensión fotovoltaica en Voltios")
    load_power_w: float = Field(default=0.0, description="Potencia activa de consumo en Vatios")
    load_voltage_v: float = Field(default=0.0, description="Tensión de salida AC en Voltios")
    load_percent: float = Field(default=0.0, description="Porcentaje de carga del inversor (%)")
    battery_capacity_percent: float = Field(default=0.0, description="Nivel de batería (%)")
    battery_voltage_v: float = Field(default=0.0, description="Tensión de batería en Voltios")
    battery_charging_a: float = Field(default=0.0, description="Corriente de carga en Amperios")
    battery_discharging_a: float = Field(default=0.0, description="Corriente de descarga en Amperios")
    grid_voltage_v: float = Field(default=0.0, description="Tensión de red en Voltios")
    grid_frequency_hz: float = Field(default=0.0, description="Frecuencia de red en Hz")
    temp_c: Optional[float] = Field(default=None, description="Temperatura estimada del inversor en °C")


class RatingsSchema(BaseModel):
    """Capacidades nominales de fábrica del equipo."""
    max_power_w: float = Field(default=0.0, description="Potencia nominal máxima en Vatios")
    nominal_battery_v: float = Field(default=0.0, description="Tensión nominal del banco de baterías")


class StatusResponse(BaseModel):
    """Respuesta consolidada para el endpoint /api/status."""
    status: str = Field(default="online", description="Estado del sistema: 'online', 'offline', 'error', 'demo'")
    device_sn: Optional[str] = Field(default=None, description="Número de serie del dispositivo")
    last_update: Optional[str] = Field(default=None, description="Timestamp ISO del último reporte")
    alerts: AlertsSchema = Field(default_factory=AlertsSchema)
    metrics: MetricsSchema = Field(default_factory=MetricsSchema)
    ratings: RatingsSchema = Field(default_factory=RatingsSchema)
    error: Optional[str] = Field(default=None, description="Detalle del error si existe")
