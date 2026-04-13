from dotenv import load_dotenv, find_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastapi import FastAPI

from llmcasasbca.app.routers import prediccion
app = FastAPI(title="API LLM - ESTIMADOR DE CASAS")


app.include_router(prediccion.router, prefix="/casas", tags=["Casas"])