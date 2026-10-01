from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.core.config_manager import (
    config_manager,
    AppDynamicConfigPublic,
    AppDynamicConfigUpdate,
    merge_config,
)
from app.services.shinemonitor import ShineMonitorService
from app.api.deps import get_shinemonitor_service

router = APIRouter()


class ShineMonitorTestPayload(BaseModel):
    username: Optional[str] = Field(None, description="Usuario para probar")
    password: Optional[str] = Field(None, description="Contrasena para probar")


@router.get(
    "",
    include_in_schema=False,
    response_model=AppDynamicConfigPublic,
    summary="Obtener configuracion dinamica persistente",
    description="Retorna umbrales y horarios. El token de Telegram y la contrasena de ShineMonitor no se incluyen."
)
def get_dynamic_config() -> AppDynamicConfigPublic:
    """Retorna la configuracion activa sin secretos."""
    return AppDynamicConfigPublic.from_stored(config_manager.get_config())


@router.post(
    "",
    include_in_schema=False,
    response_model=AppDynamicConfigPublic,
    summary="Guardar configuracion dinamica persistente",
    description="Actualiza umbrales y credenciales. Un token o contrasena vacios conservan el valor ya guardado."
)
def update_dynamic_config(update: AppDynamicConfigUpdate) -> AppDynamicConfigPublic:
    """Fusiona la actualizacion y la persiste en data/config.json."""
    merged = merge_config(config_manager.get_config(), update)
    success = config_manager.save(merged)
    if not success:
        raise HTTPException(status_code=500, detail="No se pudo escribir en data/config.json")
    return AppDynamicConfigPublic.from_stored(config_manager.get_config())


@router.post(
    "/test-shinemonitor",
    include_in_schema=False,
    summary="Verificar conexion y credenciales de ShineMonitor",
    description="Prueba la autenticacion y deteccion de inversores con las credenciales dadas o guardadas."
)
def test_shinemonitor_credentials(
    payload: Optional[ShineMonitorTestPayload] = None,
    service: ShineMonitorService = Depends(get_shinemonitor_service)
):
    """Valida usuario y contrasena contra la API de ShineMonitor."""
    u = payload.username if payload else None
    p = payload.password if payload else None
    return service.test_credentials(username=u, password=p)
