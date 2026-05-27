import json
import math
import pickle
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.schemas.Casa import CasaCreate
from app.schemas.prediccion import PrediccionData, PrediccionResponse


BASE = Path(__file__).resolve().parents[2]
ENV_RUTA = BASE / ".env"

FEATURE_COLUMNS = [
    "area_construida_m2",
    "habitaciones",
    "banos",
    "garaje",
    "estrato",
    "am_basicos_completos",
    "am_basicos_complementarios",
    "am_basicos_incompletos",
    "am_garaje",
    "am_comedor",
    "am_sala",
    "am_patio",
    "am_2_plantas",
    "am_cocina_integral",
    "am_antejardin",
    "am_comercial",
    "am_balcon",
    "barrio_encoded",
    "estado_construccion_EXCELENTE ESTADO",
    "estado_construccion_NPH",
    "estado_construccion_PH",
    "estado_construccion_REMODELADA",
    "estado_construccion_USADO",
    "area_por_hab",
    "ratio_banos_hab",
    "total_amenidades",
    "estrato_x_area",
    "area_vs_estrato",
]

MODEL_METRICS = {
    "mae_cop": 60_100_000,
    "mape": 0.301,
    "r2": 0.7103,
}


class Settings(BaseSettings):
    modelo_pkl_path: Path = BASE / "models" / "modelo_precio.pkl"
    barrio_encoding_path: Path = BASE / "models" / "barrio_encoding.json"
    groq_api_key: str | None = Field(default=None, validation_alias="GROQ_API_KEY")
    recomendacion_model: str = Field(
        default="openai/gpt-oss-120b",
        validation_alias="RECOMENDACION_MODEL",
    )

    model_config = SettingsConfigDict(
        env_file=ENV_RUTA,
        env_file_encoding="utf-8-sig",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def cargar_modelo(modelo_path: str) -> Any:
    path = Path(modelo_path)
    if not path.is_absolute():
        path = BASE / path

    if not path.exists():
        raise FileNotFoundError(f"No existe el modelo pkl en: {path}")

    with path.open("rb") as modelo_file:
        return pickle.load(modelo_file)


def normalizar_barrio(nombre: str) -> str:
    nombre = unicodedata.normalize("NFKD", nombre)
    nombre = "".join(char for char in nombre if not unicodedata.combining(char))
    nombre = re.sub(r"[^a-zA-Z0-9]+", " ", nombre).strip().lower()

    prefijos = (
        "barrio ",
        "j v c ",
        "jvc ",
        "urb ",
        "urbanizacion ",
        "asentamiento humano ",
    )
    for prefijo in prefijos:
        if nombre.startswith(prefijo):
            nombre = nombre.removeprefix(prefijo).strip()

    return re.sub(r"\s+", " ", nombre)


@lru_cache
def cargar_barrio_encoding(encoding_path: str) -> tuple[dict[str, float], float]:
    path = Path(encoding_path)
    if not path.is_absolute():
        path = BASE / path

    if not path.exists():
        raise FileNotFoundError(f"No existe el encoding de barrios en: {path}")

    with path.open("r", encoding="utf-8-sig") as encoding_file:
        data = json.load(encoding_file)

    barrio_encoding = data.get("barrios") or data.get("barrio_encoding") or data
    if not isinstance(barrio_encoding, dict):
        raise ValueError("El encoding de barrios debe ser un diccionario.")

    barrio_encoding = {str(nombre): float(valor) for nombre, valor in barrio_encoding.items()}
    global_mean = data.get("global_mean")

    if global_mean is None:
        if not barrio_encoding:
            raise ValueError("El encoding de barrios no tiene valores para calcular global_mean.")
        global_mean = sum(barrio_encoding.values()) / len(barrio_encoding)

    barrio_encoding.update(
        {normalizar_barrio(nombre): valor for nombre, valor in barrio_encoding.items()}
    )

    return barrio_encoding, float(global_mean)


class PrediccionService:
    """Servicio de prediccion usando el modelo local serializado en pkl."""

    def _modelo(self) -> Any:
        settings = get_settings()
        try:
            return cargar_modelo(str(settings.modelo_pkl_path))
        except FileNotFoundError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail="No fue posible cargar el modelo pkl. Verifica que el archivo sea confiable y compatible.",
            ) from exc

    def _resolver_barrio_encoded(self, datos: dict[str, Any]) -> float:
        barrio_encoded = datos.get("barrio_encoded")
        if barrio_encoded is not None:
            return float(barrio_encoded)

        barrio = datos.get("barrio")
        if barrio is None:
            raise HTTPException(
                status_code=400,
                detail="Envia barrio_encoded o barrio para poder calcular la variable barrio_encoded.",
            )

        nombre_barrio = getattr(barrio, "value", barrio)
        settings = get_settings()

        try:
            barrio_encoding, global_mean = cargar_barrio_encoding(str(settings.barrio_encoding_path))
        except FileNotFoundError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail="No fue posible cargar barrio_encoding. Verifica el JSON y el valor global_mean.",
            ) from exc

        return barrio_encoding.get(
            str(nombre_barrio),
            barrio_encoding.get(normalizar_barrio(str(nombre_barrio)), global_mean),
        )

    def _construir_features(self, casa_create: CasaCreate) -> dict[str, float]:
        datos = casa_create.model_dump(by_alias=True)

        datos["barrio_encoded"] = self._resolver_barrio_encoded(datos)
        datos["garaje"] = int(datos["garaje"])
        datos["am_basicos_completos"] = 1
        datos["am_basicos_complementarios"] = 0
        datos["am_basicos_incompletos"] = 0
        datos["am_sala"] = 1
        datos["am_comedor"] = 1
        datos["am_garaje"] = 1 if datos["garaje"] > 0 else 0
        datos["am_patio"] = int(datos["patio"])
        datos["am_2_plantas"] = int(datos["dos_plantas"])
        datos["am_cocina_integral"] = int(datos["cocina_integral"])
        datos["am_antejardin"] = int(datos["antejardin"])
        datos["am_comercial"] = int(datos["uso_comercial"])
        datos["am_balcon"] = int(datos["balcon"])
        datos["estado_construccion_EXCELENTE ESTADO"] = 0
        datos["estado_construccion_NPH"] = 0
        datos["estado_construccion_PH"] = 0
        datos["estado_construccion_REMODELADA"] = 0
        datos["estado_construccion_USADO"] = 1
        datos["area_por_hab"] = datos["area_construida_m2"] / datos["habitaciones"]
        datos["ratio_banos_hab"] = datos["banos"] / datos["habitaciones"]
        datos["total_amenidades"] = sum(
            int(datos[columna])
            for columna in (
                "am_basicos_completos",
                "am_basicos_complementarios",
                "am_basicos_incompletos",
                "am_garaje",
                "am_comedor",
                "am_sala",
                "am_patio",
                "am_2_plantas",
                "am_cocina_integral",
                "am_antejardin",
                "am_comercial",
                "am_balcon",
            )
        )
        datos["estrato_x_area"] = datos["estrato"] * datos["area_construida_m2"]
        datos["area_vs_estrato"] = datos["area_construida_m2"] / datos["estrato"]

        try:
            return {columna: float(datos[columna]) for columna in FEATURE_COLUMNS}
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=f"Falta la variable requerida: {exc.args[0]}") from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Las variables del modelo deben ser numericas.") from exc

    @staticmethod
    def _predecir(modelo: Any, features: dict[str, float]) -> float:
        try:
            import pandas as pd
        except ImportError:
            entrada = [[features[columna] for columna in FEATURE_COLUMNS]]
        else:
            entrada = pd.DataFrame([features], columns=FEATURE_COLUMNS)

        prediccion = modelo.predict(entrada)
        precio = float(prediccion[0])
        if precio < 1_000:
            return float(math.exp(precio))
        return precio

    @staticmethod
    def _rango_precio(precio: float) -> str:
        minimo = precio * 0.9
        maximo = precio * 1.1
        return f"{minimo:,.0f} - {maximo:,.0f} COP".replace(",", ".")

    @staticmethod
    def _amenidades_texto(casa_create: CasaCreate) -> str:
        amenidades = []
        if int(casa_create.garaje) > 0:
            amenidades.append("garaje")
        if int(casa_create.patio):
            amenidades.append("patio")
        if int(casa_create.cocina_integral):
            amenidades.append("cocina integral")
        if int(casa_create.dos_plantas):
            amenidades.append("dos plantas")
        if int(casa_create.balcon):
            amenidades.append("balcon")
        if int(casa_create.antejardin):
            amenidades.append("antejardin")
        if int(casa_create.uso_comercial):
            amenidades.append("uso comercial")
        return ", ".join(amenidades) if amenidades else "sin amenidades adicionales destacadas"

    @staticmethod
    def _nombre_barrio(casa_create: CasaCreate) -> str:
        if casa_create.barrio is None:
            return "el barrio seleccionado"
        return getattr(casa_create.barrio, "value", str(casa_create.barrio))

    def _recomendacion_fallback(
        self,
        precio: float,
        rango_precio: str,
        features: dict[str, float],
        casa_create: CasaCreate,
    ) -> str:
        precio_formateado = f"{precio:,.0f}".replace(",", ".")
        mae_formateado = f"{MODEL_METRICS['mae_cop']:,.0f}".replace(",", ".")
        barrio = self._nombre_barrio(casa_create)
        amenidades = self._amenidades_texto(casa_create)
        return (
            f"Para una vivienda en {barrio}, de {features['area_construida_m2']:.0f} m2, "
            f"{features['habitaciones']:.0f} habitaciones, {features['banos']:.0f} banos "
            f"y estrato {features['estrato']:.0f}, el modelo estima un valor cercano a "
            f"{precio_formateado} COP. Recomiendo mirar mas el rango {rango_precio} que el "
            f"valor puntual, porque el modelo tiene un margen de error promedio de "
            f"{mae_formateado} COP y MAPE de {MODEL_METRICS['mape']:.1%}. Las condiciones "
            f"que mas pesan aqui son el area, el estrato y las caracteristicas reportadas: "
            f"{amenidades}. Valida con comparables recientes y el estado fisico real antes de negociar."
        )

    async def _generar_recomendacion_llm(
        self,
        precio: float,
        rango_precio: str,
        features: dict[str, float],
        casa_create: CasaCreate,
    ) -> str:
        settings = get_settings()
        if not settings.groq_api_key:
            return self._recomendacion_fallback(precio, rango_precio, features, casa_create)

        try:
            from groq import AsyncGroq
        except ImportError:
            return self._recomendacion_fallback(precio, rango_precio, features, casa_create)

        system_prompt = """
Eres un analista inmobiliario para Barrancabermeja, Colombia. Recibes la salida de un modelo predictivo de precios de vivienda y debes redactar una recomendacion breve, profesional y honesta para el usuario final.

Reglas obligatorias:
- No inventes datos de mercado, comparables, tasas, zonas premium ni tendencias que no vengan en el input.
- Explica que la cifra es una estimacion estadistica, no un avalúo formal.
- Usa las metricas del modelo para comunicar incertidumbre: MAE 60.1 millones COP, MAPE 30.1% y R2 71.03%.
- Menciona que el rango de precio es mas util que el punto exacto.
- Si el MAPE/MAE sugieren alta incertidumbre, dilo con claridad sin alarmismo.
- Da 2 o 3 factores concretos del inmueble usando nombres entendibles: barrio, area, habitaciones, banos, garaje, estrato y amenidades. No menciones variables tecnicas como barrio_encoded, ratio_banos_hab o estrato_x_area.
- Termina con una recomendacion practica: validar con comparables recientes, estado fisico y negociacion.
- Responde en español, en un solo parrafo, maximo 90 palabras.
""".strip()

        payload = {
            "precio_casa_cop": round(precio),
            "rango_precio": rango_precio,
            "metricas_modelo": {
                "mae_cop": MODEL_METRICS["mae_cop"],
                "mape_porcentaje": 30.1,
                "r2_porcentaje": 71.03,
            },
            "inmueble": {
                "barrio": self._nombre_barrio(casa_create),
                "area_m2": features["area_construida_m2"],
                "habitaciones": features["habitaciones"],
                "banos": features["banos"],
                "garaje": features["garaje"],
                "estrato": features["estrato"],
                "amenidades": self._amenidades_texto(casa_create),
            },
            "variables_tecnicas_modelo": features,
        }

        try:
            client = AsyncGroq(api_key=settings.groq_api_key, timeout=12.0)
            response = await client.chat.completions.create(
                model=settings.recomendacion_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                temperature=0.2,
                max_tokens=220,
            )
            recomendacion = response.choices[0].message.content
        except Exception as exc:
            print(f"No fue posible generar recomendacion con LLM: {type(exc).__name__}: {exc}")
            return self._recomendacion_fallback(precio, rango_precio, features, casa_create)

        if not recomendacion:
            return self._recomendacion_fallback(precio, rango_precio, features, casa_create)

        return recomendacion.strip()

    async def predecir_precio(self, casa_create: CasaCreate) -> PrediccionResponse:
        modelo = self._modelo()
        features = self._construir_features(casa_create)

        try:
            precio = self._predecir(modelo, features)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail="El modelo no pudo generar la prediccion con las variables recibidas.",
            ) from exc

        rango_precio = self._rango_precio(precio)
        recomendaciones = await self._generar_recomendacion_llm(
            precio=precio,
            rango_precio=rango_precio,
            features=features,
            casa_create=casa_create,
        )

        return PrediccionResponse(
            data=PrediccionData(
                precio_casa=precio,
                rango_precio=rango_precio,
                recomendaciones=recomendaciones,
                confianza=1.0,
            )
        )
