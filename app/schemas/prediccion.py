
from pydantic import BaseModel, Field

class PrediccionData(BaseModel):
    precio_casa : float = Field(description="Estimación del valor total de la casa expresado en pesos colombianos (COP)."
                                            "Debe ser un número real sin símbolos ni formato de texto.")
    rango_precio : str = Field(description="Rango estimado del valor de la casa en pesos colombianos (COP), expresado "
                                           "como intervalo, por ejemplo: '180.000.000 - 220.000.000 COP'. Debe reflejar incertidumbre del modelo")
    recomendaciones : str = Field(description="Análisis breve con recomendaciones sobre la estimación del precio, "
                                              "incluyendo factores que influyen en el valor (ubicación, tamaño, estado, etc.) y posibles mejoras o advertencias.")
    confianza : float = Field(description="CONFIANZA DE LA PREDICCION")

class PrediccionResponse(BaseModel):
    success: bool = True
    data: PrediccionData