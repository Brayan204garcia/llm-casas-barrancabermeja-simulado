
import json

from anyio.functools import lru_cache
from pydantic_settings import SettingsConfigDict, BaseSettings

from app.schemas.Casa import  CasaCreate
from groq import AsyncGroq, RateLimitError

from app.schemas.prediccion import PrediccionResponse, PrediccionData

class Settings(BaseSettings):
    groq_api_key : str
    model_config = SettingsConfigDict(env_file="llmcasasbca/.env", env_file_encoding="utf-8")

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()




class PrediccionService:
    """CLASE SERVICIO PARA TODO EL PROCESO DE PREDICCION DEL LLM"""
    async def llm_rol(self, valores_casa) -> dict:
        try:
            client = AsyncGroq(api_key=settings.groq_api_key)
            """PENDIENTE"""
            system_prompt = """
            Eres un modelo experto en valoración inmobiliaria en Colombia, especializado en la ciudad de Barrancabermeja.
            Tu objetivo es estimar el precio de viviendas de forma precisa, razonada y coherente con el mercado local, considerando factores como ubicación dentro de Barrancabermeja, estrato, área construida, estado del inmueble, antigüedad, tipo de vivienda y tendencias del mercado inmobiliario regional.
            Debes:
            - Analizar los datos de la vivienda de forma objetiva.
            - Estimar un rango de precio realista en pesos colombianos (COP).
            - Dar una recomendacion sobre el mercado actual
            - Evitar inventar datos del mercado; basa tus respuestas en lógica y patrones generales del sector inmobiliario.
            
            Responde de manera clara, profesional y orientada a toma de decisiones.
    """
            prediccion_response = await client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages = [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },

                    {"role": "user",
                     "content": valores_casa,
                     }
                ],
                response_format=
                {
                    "type": "json_schema",
                    "json_schema":
                        {

                        "name": "api_response_validation",
                        "schema": PrediccionData.model_json_schema()
                        }
                }

            )
            return json.loads(prediccion_response.choices[0].message.content or "{}")
        except RateLimitError:
            print("SE AGOTARON LOS TOKENS DE LA APIKEY, VUELVA A INTENTARLO EN UNAS HORAS")

    async def predecir_precio(self, casa_create : CasaCreate) -> dict:
        """PENDIENTE"""
        #Construyendo los parametros de la casa a JSON, para el llm
        casa_create_json = casa_create.model_dump_json()
        prediccion_data = await self.llm_rol(valores_casa=casa_create_json)

        return PrediccionResponse(
            data=PrediccionData(**prediccion_data)
        )