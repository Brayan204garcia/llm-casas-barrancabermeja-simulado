from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.enums.barrio import BarrioEnum


class CasaCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    barrio: BarrioEnum | None = None
    barrio_encoded: float | None = Field(default=None, ge=0)

    area_construida_m2: float = Field(
        validation_alias=AliasChoices("area_construida_m2", "area_m2", "area"),
        gt=0,
    )
    habitaciones: int = Field(ge=1)
    banos: int = Field(ge=1)
    garaje: int | str | bool
    estrato: int = Field(ge=1, le=6)

    patio: int | str | bool = 0
    cocina_integral: int | str | bool = 0
    dos_plantas: int | str | bool = 0
    balcon: int | str | bool = 0
    antejardin: int | str | bool = 0
    uso_comercial: int | str | bool = 0

    @field_validator("barrio", mode="before")
    def validar_barrio(cls, v):
        if v is None:
            return v
        barrios_validos = [b.value for b in BarrioEnum]
        if v not in barrios_validos:
            raise ValueError(f"Barrio '{v}' no reconocido.")
        return v

    @field_validator("habitaciones", "banos", mode="before")
    def validar_entero_con_mas(cls, v):
        if isinstance(v, str):
            valor = v.strip()
            if valor.endswith("+"):
                valor = valor[:-1]
            return int(valor)
        return v

    @field_validator(
        "patio",
        "cocina_integral",
        "dos_plantas",
        "balcon",
        "antejardin",
        "uso_comercial",
        mode="before",
    )
    def validar_binario(cls, v):
        if isinstance(v, bool):
            return int(v)
        if isinstance(v, str):
            valor = v.strip().lower()
            if valor in {"si", "sí", "true", "1", "yes"}:
                return 1
            if valor in {"no", "false", "0"}:
                return 0
        if v in {0, 1}:
            return v
        raise ValueError("Las caracteristicas adicionales deben ser si/no o 0/1.")

    @field_validator("garaje", mode="before")
    def validar_garaje(cls, v):
        if isinstance(v, bool):
            return int(v)
        if isinstance(v, str):
            valor = v.strip().lower()
            if valor in {"no", "ninguno", "0"}:
                return 0
            if valor in {"1", "uno", "sencillo", "simple"}:
                return 1
            if valor in {"2", "doble"}:
                return 2
        if v in {0, 1, 2}:
            return v
        raise ValueError("Garaje debe ser No, 1 o Doble.")
