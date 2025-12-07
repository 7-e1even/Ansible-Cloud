from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from app.core.config import settings
from app.core.database import Database
from app.api.v1.routers import auth, hosts, ansible, sftp, logs, ws, files, templates, tencent, workflow, cloud_credentials
from app.utils.crypto import derive_key_from_credentials, set_crypto_keys
import time
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(settings.LOG_DIR, "app.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Crypto Keys from Config
try:
    key, salt = derive_key_from_credentials(settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD)
    set_crypto_keys(key, salt)
    logger.info("Crypto keys initialized successfully from config")
except Exception as e:
    logger.error(f"Failed to initialize crypto keys: {str(e)}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Access Log Middleware
@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Log only API requests to DB
    if request.url.path.startswith("/api"):
        # We need a DB instance. 
        # Creating a new one per request here is one way, or using dependency injection.
        # Middleware doesn't support dependency injection easily.
        # We'll instantiate Database directly as it's lightweight (sqlite connection per call).
        try:
            db = Database()
            # Get real IP
            client_ip = request.client.host
            if "x-forwarded-for" in request.headers:
                client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
            elif "x-real-ip" in request.headers:
                client_ip = request.headers["x-real-ip"]
                
            status = 'success' if response.status_code < 400 else 'failed'
            db.add_access_log(client_ip, request.url.path, status, response.status_code)
        except Exception as e:
            logger.error(f"Failed to log access: {e}")
            
    return response

# Include Routers
app.include_router(auth.router, prefix="/api") # /api/login
app.include_router(hosts.router, prefix="/api/hosts", tags=["hosts"])
app.include_router(ansible.router, prefix="/api", tags=["ansible"]) # /api/execute, /api/playbook
app.include_router(sftp.router, prefix="/api/sftp", tags=["sftp"])
app.include_router(logs.router, prefix="/api", tags=["logs"]) # /api/logs, /api/access-logs
app.include_router(ws.router, prefix="/ws", tags=["websocket"]) # /ws/terminal
app.include_router(files.router, prefix="/api", tags=["files"]) # /api/upload
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])
app.include_router(tencent.router, prefix="/api/tencent", tags=["tencent"])
app.include_router(workflow.router, prefix="/api/workflows", tags=["workflows"])
app.include_router(cloud_credentials.router, prefix="/api", tags=["cloud-credentials"])

@app.on_event("startup")
async def startup_event():
    logger.info(f"Server started. Access the UI at http://localhost:3000")
    logger.info(f"API documentation available at http://localhost:3000{settings.API_V1_STR}/docs")

# Add the /api/ws-token endpoint (it was defined in ws router but with /ws-token path)
# We need to ensure it's mounted correctly. 
# ws.router has @router.get("/ws-token/{host_id}")
# Mounted at /ws, so it becomes /ws/ws-token/{host_id}.
# But the frontend expects /api/ws-token/{host_id}.
# So we need to include the ws router again with /api prefix, but exclude the websocket endpoint to avoid conflict?
# Or just include it with /api prefix and ignore the websocket endpoint duplication (or handled by path).
# Actually, FastAPI allows mounting the same router with different prefixes.
# The websocket endpoint is at /terminal/{host_id}.
# If mounted at /api, it becomes /api/terminal/{host_id} (not used).
# If mounted at /ws, it becomes /ws/terminal/{host_id} (used).
# The token endpoint is at /ws-token/{host_id}.
# If mounted at /api, it becomes /api/ws-token/{host_id} (used).
# So we can mount ws.router at /api as well.
app.include_router(ws.router, prefix="/api", tags=["websocket-token"])

# Static Files & Frontend Fallback
# Serve 'public' directory
static_dir = "public"
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# SPA Fallback
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    # Check if file exists in public
    file_path = os.path.join(static_dir, full_path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # If not, serve index.html
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    return JSONResponse({"error": "Frontend not built or index.html missing"}, status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=3000, reload=True)
