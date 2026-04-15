"""
MarcoAI – Documents API Router (Fase 9)
══════════════════════════════════════════════════════════════════════════════
Endpoints para gestionar la Nube Privada y el inicio de RAG.
"""
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from app.api.deps import get_current_user
from app.db.base import get_db
from app.db.models import User
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Nube"])


@router.get("", summary="Listar documentos guardados")
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = DocumentService(db, current_user.id)
    docs = await service.get_documents()
    return [{
        "id": d.id,
        "filename": d.filename,
        "mime_type": d.mime_type,
        "size_bytes": d.size_bytes,
        "status": d.status,
        "created_at": d.created_at
    } for d in docs]


@router.post("/upload", summary="Subir y procesar un documento en la nube privada")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    if not file.filename.lower().endswith((".pdf", ".txt")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se soportan archivos PDF o de texto plano por el momento."
        )
        
    service = DocumentService(db, current_user.id)
    doc = await service.ingest_file(file)
    
    # Start vector processing in background task to not block the request
    # NOTE: Since the background task is run outside the request context (or rather runs parallel but could outlive session), 
    # DocumentService should instantiate its own safe DB session inside its background task if needed, but for simplicity here we just use the background task on a fresh AsyncSessionLocal.
    async def run_worker():
        from app.db.base import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            bg_service = DocumentService(session, current_user.id)
            await bg_service.process_document_background(doc.id)
            
    background_tasks.add_task(run_worker)
    
    return {"message": "Documento subido, procesamiento en segundo plano.", "id": doc.id}


@router.delete("/{doc_id}", summary="Eliminar un documento")
async def delete_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = DocumentService(db, current_user.id)
    deleted = await service.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado.")
    return {"message": "Documento y vectores eliminados."}
