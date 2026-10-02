"""统一错误结构与全局异常处理。"""
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import Request


class ServiceError(Exception):
    """服务层内部错误，带业务错误码，由上层转换为任务 failed 或 HTTP 错误。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    """抛出统一格式的业务错误：{"error": {"code", "message"}}"""
    return HTTPException(status_code=status_code, detail={"error": {"code": code, "message": message}})


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """把业务错误去壳，直接返回 {"error": {...}}；其余 HTTP 错误也归一化。"""
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "HTTP_ERROR", "message": str(detail)}},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """参数校验失败也归一化为统一错误结构。"""
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": "请求参数不合法"}},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """兜底：任何未捕获异常都返回统一结构，不泄露堆栈。"""
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "服务器内部错误，请稍后重试"}},
    )
