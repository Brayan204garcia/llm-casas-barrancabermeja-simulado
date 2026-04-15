from fastapi import FastAPI

from app.routers import prediccion

app = FastAPI(title="API LLM - ESTIMADOR DE CASAS")


app.include_router(prediccion.router, prefix="/casas", tags=["Casas"])