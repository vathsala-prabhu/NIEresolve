import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.database import engine, Base
from backend.app.database_migrations import run_migrations
from backend.app.scheduler import escalation_scheduler
from backend.app.seeds.seed_data import seed_database
from backend.app.ml.train_model import train_priority_model

# Routers
from backend.app.routers import (
    auth,
    complaints,
    evidence,
    escalations,
    scholarships,
    chatbot,
    notifications,
    analytics,
    admin,
    announcements,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure DB schema & seed data
    Base.metadata.create_all(bind=engine)
    run_migrations()
    seed_database()

    # Train or load ML model if model artifact missing
    if not os.path.exists(settings.MODEL_STORAGE_PATH):
        print("[Startup] Training priority prediction model...")
        train_priority_model()

    # Start background escalation scheduler if not in test suite
    if not os.environ.get("TESTING"):
        escalation_scheduler.start()
        print("[Startup] NIEresolve platform ready.")

    yield

    # Shutdown
    if not os.environ.get("TESTING"):
        escalation_scheduler.stop()

app = FastAPI(
    title=settings.APP_NAME,
    description="NIEresolve — Every Concern Deserves a Response. AI-Powered College Grievance Redressal and Student Support Platform for The National Institute of Engineering (NIE), Mysuru.",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure uploads directory exists and mount as static
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Mount frontend static directories
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(os.path.join(frontend_dir, "css")):
    app.mount("/css", StaticFiles(directory=os.path.join(frontend_dir, "css")), name="css")
if os.path.exists(os.path.join(frontend_dir, "js")):
    app.mount("/js", StaticFiles(directory=os.path.join(frontend_dir, "js")), name="js")

# Include Routers
app.include_router(auth.router)
app.include_router(complaints.router)
app.include_router(evidence.router)
app.include_router(escalations.router)
app.include_router(scholarships.router)
app.include_router(chatbot.router)
app.include_router(notifications.router)
app.include_router(analytics.router)
app.include_router(admin.router)
app.include_router(announcements.router)

# Health & Info Endpoint
@app.get("/api/info")
def get_app_info():
    return {
        "app_name": settings.APP_NAME,
        "tagline": settings.TAGLINE,
        "institution": settings.INSTITUTION,
        "version": "2.0.0",
        "status": "operational",
    }

# Serve Frontend SPA
@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    """Serves the institutional Single Page Application."""
    # Prevent capturing API or uploads routes
    if full_path.startswith("api/") or full_path.startswith("uploads/"):
        return HTMLResponse(status_code=404, content="Endpoint not found")

    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h1>NIEresolve Backend Running</h1><p>Frontend assets building...</p>")
