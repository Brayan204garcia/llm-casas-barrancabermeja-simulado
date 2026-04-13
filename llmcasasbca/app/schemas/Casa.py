
from pydantic import BaseModel, field_validator

from llmcasasbca.app.enums.barrio import BarrioEnum


class CasaCreate(BaseModel):
    barrio : BarrioEnum
    num_hab : int
    num_banos : int
    estrato : int
    area_const : int
    garaje : bool
    anos_antigueda : int
    estado : str

    @field_validator("barrio", mode="before")
    def barrio(cls, v):
        barrios_validos = [b.value for b in BarrioEnum]
        if v not in barrios_validos:
            raise ValueError(
                f"Barrio '{v}' no reconocido. "
            )
        return v

