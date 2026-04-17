from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.routers import prediccion

app = FastAPI(title="API LLM - ESTIMADOR DE CASAS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prediccion.router, prefix="/casas", tags=["Casas"])
