from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
import psycopg2

from app.config import settings, BASE_DIR
from app.db import init_connection_pool, close_connection_pool, get_connection_string, is_using_memory_fallback
from app.errors import AppException, explain, translate_pg_error
from app.routers import (
    properties_router,
    guests_router,
    bookings_router,
    payments_router,
    reviews_router
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database pool
    init_connection_pool()
    yield
    # Shutdown: clean up pool
    close_connection_pool()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-grade REST API for Kaveri Stays hotel reservation system enforcing robust database constraints.",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files mount
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# --- Exception Handlers ---
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status_code": exc.status_code,
            "error": "Conflict" if exc.status_code == 409 else (
                "Unprocessable Entity" if exc.status_code == 422 else (
                    "Not Found" if exc.status_code == 404 else "Error"
                )
            ),
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
        }
    )

@app.exception_handler(psycopg2.Error)
async def pg_exception_handler(request: Request, exc: psycopg2.Error):
    app_exc = translate_pg_error(exc)
    return await app_exception_handler(request, app_exc)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err["loc"])
        errors.append({"field": loc, "issue": err["msg"]})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status_code": 422,
            "error": "Unprocessable Entity",
            "code": "VALIDATION_ERROR",
            "message": "The request body failed schema validation.",
            "details": {"validation_errors": errors}
        }
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status_code": 422,
            "error": "Unprocessable Entity",
            "code": "VALUE_ERROR",
            "message": str(exc),
            "details": None
        }
    )

# --- Include Routers ---
app.include_router(properties_router)
app.include_router(guests_router)
app.include_router(bookings_router)
app.include_router(payments_router)
app.include_router(reviews_router)

# --- Base Endpoints ---
@app.get("/", tags=["System"])
def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept and not accept.startswith("*/*"):
        index_file = BASE_DIR / "static" / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "docs_url": "/docs",
        "website_url": "/portal",
        "database_backend": "in_memory_verified_store" if is_using_memory_fallback() else "postgresql"
    }

@app.get("/portal", tags=["System"], include_in_schema=False)
@app.get("/dashboard", tags=["System"], include_in_schema=False)
@app.get("/ui", tags=["System"], include_in_schema=False)
@app.get("/website", tags=["System"], include_in_schema=False)
def serve_website():
    index_file = BASE_DIR / "static" / "index.html"
    return FileResponse(index_file)

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "database": {
            "backend": "in_memory_verified_store" if is_using_memory_fallback() else "postgresql",
            "url_configured": bool(settings.DATABASE_URL),
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("Database URL:", get_connection_string())
    print("Sample error explanation (409):", explain(409))
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)