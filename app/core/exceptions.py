from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse


# excepción personalizada
class ErrorException(Exception):
    def __init__(self, message: str):
        self.message = message


# Handler excepción personalizada
async def error_exception_handler(request: Request, exc: ErrorException):
    return JSONResponse(
        status_code=400,
        content={
            "message": exc.message,
            "success": False
        }
    )


# handler global para errores de Pydantic
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0]
    return JSONResponse(
        status_code=400,
        content={
            "message": first_error["msg"].replace("Value error, ", ""),
            "success": False
        }
    )