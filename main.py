import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import UPLOAD_DIR
from database import engine, Base
from seed_demo import init_system_defaults
from services.state_service import offline_checker_task

# Import routers
from routers.auth import router as auth_router
from routers.gateway_api import router as gateway_router
from routers.dashboard import router as dashboard_router
from routers.alerts import router as alerts_router
from routers.admin import router as admin_router
from routers.ws import router as ws_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema & default seeds
    init_system_defaults()
    # Start offline checker task
    checker_task = asyncio.create_task(offline_checker_task())
    print("[System] Background offline checker started (15s interval)")
    yield
    # Shutdown
    checker_task.cancel()
    try:
        await checker_task
    except asyncio.CancelledError:
        pass
    print("[System] Application shut down gracefully")

app = FastAPI(
    title="Airport Restroom Paper Monitoring System",
    description="Hệ thống giám sát giấy vệ sinh thông minh cho sân bay",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploads folder (PDF maps)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Serve static folder (JS, CSS, images)
static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include API Routers
app.include_router(auth_router)
app.include_router(gateway_router)
app.include_router(dashboard_router)
app.include_router(alerts_router)
app.include_router(admin_router)
app.include_router(ws_router)

@app.get("/")
def serve_index():
    return FileResponse(
        static_dir / "index.html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
