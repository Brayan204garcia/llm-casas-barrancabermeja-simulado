from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware

from app.core.exceptions import validation_exception_handler
from app.routers import prediccion

app = FastAPI(title="API LLM - ESTIMADOR DE CASAS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prediccion.router, prefix="/casas", tags=["Casas"])
# Esto sobreescribe el handler default de FastAPI
app.add_exception_handler(RequestValidationError, validation_exception_handler)