from fastapi.responses import JSONResponse
from fastapi import HTTPException, status


def success_response_status(status: status, payload: dict) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=payload
    ) 
    

def error_response_status(status: status, message: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"message": message}
    )