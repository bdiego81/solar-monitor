from typing import List, Optional
from pydantic import BaseModel, Field


class HistoryPoint(BaseModel):
    """Punto temporal discreto de telemetría histórica."""
    timestamp: str = Field(..., description="Marca de tiempo del registro (HH:MM o YYYY-MM-DD HH:MM)")
    pv_power_w: float = Field(default=0.0, description="Generación solar en Vatios")
    load_power_w: float = Field(default=0.0, description="Consumo en Vatios")
    battery_pct: float = Field(default=0.0, description="Porcentaje de carga de batería (%)")
    grid_voltage_v: float = Field(default=0.0, description="Tensión de red en Voltios")
    temp_c: float = Field(default=30.0, description="Temperatura estimada del inversor en °C")


class HistorySummary(BaseModel):
    """Resumen de integración de energía total en el periodo."""
    pv_energy_kwh: float = Field(default=0.0, description="Energía solar generada acumulada en kWh")
    load_energy_kwh: float = Field(default=0.0, description="Energía consumida acumulada en kWh")


class HistoryResponse(BaseModel):
    """Respuesta del endpoint /api/history."""
    dates: List[str] = Field(default_factory=list, description="Fechas incluidas en el rango consultado")
    history: List[HistoryPoint] = Field(default_factory=list, description="Serie temporal de registros")
    summary: HistorySummary = Field(default_factory=HistorySummary, description="Integración de energía")
    error: Optional[str] = Field(default=None, description="Detalle del error si ocurrió alguno")
