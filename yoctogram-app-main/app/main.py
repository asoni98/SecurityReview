from contextlib import asynccontextmanager
import time

from asgi_correlation_id import correlation_id
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import structlog
from uvicorn.protocols.utils import get_path_with_query_string

from app.api.v1.api import api_router
from app.core.config import settings
from app.db.session import session_manager
from app.log import setup_logging

setup_logging(
    json_logs=settings.PRODUCTION, log_level="DEBUG" if settings.DEBUG else "INFO"
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Function that handles startup and shutdown events.
    To understand more, read https://fastapi.tiangolo.com/advanced/events/
    """
    yield
    if session_manager._engine is not None:
        # Close the DB connection
        await session_manager.close()


app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_PREFIX}/openapi.json"
)

if settings.PRODUCTION:
    origins = [f"https://{settings.FORWARD_FACING_HOSTNAME}"]
else:
    origins = ["*"]

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

access_logger = structlog.stdlib.get_logger("app.access")


@app.middleware("http")
async def logging_middleware(request: Request, call_next) -> Response:
    structlog.contextvars.clear_contextvars()

    start_time = time.perf_counter_ns()
    # If the call_next raises an error, we still want to return our own 500 response,
    # so we can add headers to it (process time, request ID...)
    response = Response(status_code=500)
    try:
        response = await call_next(request)
    except Exception:
        # TODO: Validate that we don't swallow exceptions (unit test?)
        structlog.stdlib.get_logger("app.error").exception("Uncaught exception")
        raise
    finally:
        process_time = time.perf_counter_ns() - start_time
        status_code = response.status_code
        url = get_path_with_query_string(request.scope)
        client_host = request.client.host
        client_port = request.client.port
        http_method = request.method
        http_version = request.scope["http_version"]
        # Recreate the Uvicorn access log format, but add all parameters as structured information
        await access_logger.ainfo(
            f"""{client_host}:{client_port} - "{http_method} {url} HTTP/{http_version}" {status_code}""",
            http={
                "url": str(request.url),
                "status_code": status_code,
                "method": http_method,
                "version": http_version,
            },
            network={"client": {"ip": client_host, "port": client_port}},
            duration=process_time,
        )
        response.headers["X-Process-Time"] = str(process_time / 10**9)
        return response


app.include_router(api_router, prefix=settings.API_PREFIX)
