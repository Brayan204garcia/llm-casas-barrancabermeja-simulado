
from pydantic import BaseModel, field_validator, Field

from app.enums.barrio import BarrioEnum


class CasaCreate(BaseModel):
    barrio : BarrioEnum
    num_hab : int = Field(ge=1)
    num_banos : int = Field(ge=1)
    estrato : int = Field(ge=1, le=6)
    area_const : int = Field(ge=30)
    garaje : bool
    anos_antigueda : int
    estado : str

    @field_validator("barrio", mode="before")
    def barrio(cls, v):
        barrios_validos = [b.value for b in BarrioEnum]
        if v not in barrios_validos:
            raise ValueError(f"Barrio '{v}' no reconocido."
            )
        return v

