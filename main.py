# Backend FastAPI para procesamiento de audios
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import io

load_dotenv()

# Configuración
app = FastAPI(title="Soporte Oportunidades API", version="1.0.0")

# CORS configuration
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
ALLOWED_ORIGINS = [
    FRONTEND_URL,
    "http://localhost:3000",
    "http://localhost:8501",
    "https://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL y SUPABASE_KEY son requeridos")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# Modelos
class TicketUpdate(BaseModel):
    id: int
    status: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


class RecordingMetadata(BaseModel):
    filename: str
    duration: Optional[float] = None
    size: int
    mime_type: str = "audio/mpeg"


# Rutas de Health Check
@app.get("/health")
async def health_check():
    """Verificar que el API está activo"""
    try:
        response = supabase.table("opportunities").select("count", count="exact").execute()
        return {
            "status": "ok",
            "database": "connected",
            "timestamp": str(__import__('datetime').datetime.now())
        }
    except Exception as e:
        return {
            "status": "error",
            "database": "disconnected",
            "error": str(e)
        }


# Rutas de Tickets
@app.get("/api/tickets")
async def get_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None
):
    """Obtener tickets con filtros opcionales"""
    try:
        query = supabase.table("opportunities").select("*")
        
        if status:
            query = query.eq("status", status)
        if priority:
            query = query.eq("priority", priority)
        
        response = query.execute()
        
        if search:
            data = response.data
            search_lower = search.lower()
            data = [
                t for t in data if (
                    search_lower in str(t.get("id", "")).lower() or
                    search_lower in str(t.get("title", "")).lower() or
                    search_lower in str(t.get("description", "")).lower()
                )
            ]
            return data
        
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/tickets/{ticket_id}")
async def update_ticket(ticket_id: int, update: TicketUpdate):
    """Actualizar un ticket"""
    try:
        update_data = update.model_dump(exclude_none=True)
        update_data.pop("id", None)
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No hay datos para actualizar")
        
        response = supabase.table("opportunities").update(update_data).eq("id", ticket_id).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Rutas de Grabaciones
@app.post("/api/recordings/upload")
async def upload_recording(
    file: UploadFile = File(...),
    ticket_id: Optional[int] = None,
    background_tasks: BackgroundTasks = None
):
    """
    Subir una grabación de audio a Supabase Storage
    
    - **file**: Archivo de audio (mp3, wav, m4a, etc.)
    - **ticket_id**: ID del ticket (opcional, para asociar la grabación)
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="El archivo debe tener nombre")
        
        # Validar extensión
        allowed_extensions = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Extensión no permitida. Use: {', '.join(allowed_extensions)}"
            )
        
        # Leer contenido del archivo
        contents = await file.read()
        
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="El archivo está vacío")
        
        # Crear ruta en Supabase Storage
        file_path = f"recordings/{ticket_id}/{file.filename}" if ticket_id else f"recordings/{file.filename}"
        
        # Subir a Supabase Storage
        response = supabase.storage.from_("tickets").upload(
            path=file_path,
            file=contents,
            file_options={"content-type": file.content_type}
        )
        
        # Guardar metadata en tabla
        recording_data = {
            "filename": file.filename,
            "size": len(contents),
            "mime_type": file.content_type or "audio/mpeg",
            "storage_path": file_path,
            "ticket_id": ticket_id
        }
        
        db_response = supabase.table("recordings").insert(recording_data).execute()
        
        return {
            "success": True,
            "filename": file.filename,
            "storage_path": file_path,
            "size": len(contents),
            "recording_id": db_response.data[0]["id"] if db_response.data else None
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/recordings")
async def get_recordings(ticket_id: Optional[int] = None):
    """Obtener grabaciones, opcionalmente filtradas por ticket"""
    try:
        query = supabase.table("recordings").select("*").order("created_at", desc=True)
        
        if ticket_id:
            query = query.eq("ticket_id", ticket_id)
        
        response = query.execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/recordings/{recording_id}/download")
async def download_recording(recording_id: int):
    """Obtener URL de descarga de una grabación"""
    try:
        response = supabase.table("recordings").select("storage_path").eq("id", recording_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Grabación no encontrada")
        
        storage_path = response.data[0]["storage_path"]
        download_url = supabase.storage.from_("tickets").get_public_url(storage_path)
        
        return {
            "download_url": download_url,
            "storage_path": storage_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Ruta raíz
@app.get("/")
async def root():
    """Información del API"""
    return {
        "name": "Soporte Oportunidades API",
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "tickets": "/api/tickets",
            "recordings": "/api/recordings"
        }
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
