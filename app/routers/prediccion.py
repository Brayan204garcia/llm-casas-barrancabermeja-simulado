from fastapi import APIRouter

from app.schemas.Casa import CasaCreate
from app.schemas.prediccion import PrediccionResponse
from app.services.prediccion_services import PrediccionService


router = APIRouter(prefix="/prediccion", tags=["prediccion"])
servicio = PrediccionService()

@router.post("/", response_model=PrediccionResponse)
async def prediccion(valores_casa : CasaCreate):
    return await servicio.predecir_precio(casa_create=valores_casa)