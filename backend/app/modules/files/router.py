import os
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import PyPDF2
from sqlalchemy.orm import Session
from app.database import get_db, User, DocumentFile
from app.auth.dependencies import get_current_user
from app.rag.engine import add_document
from typing import List
from datetime import datetime

router = APIRouter(prefix="/files", tags=["files"])

# Carpeta de subida (asegurarse de que existe)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "data/files")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Sube un archivo, lo guarda y lo indexa si es compatible"""
    # Generamos un nombre único para evitar colisiones
    file_path = os.path.join(UPLOAD_DIR, f"{current_user.id}_{file.filename}")
    
    # Guardar físicamente
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error guardando archivo: {str(e)}")

    # Registrar en DB
    db_file = DocumentFile(
        user_id=current_user.id,
        filename=file.filename,
        filepath=file_path,
        file_size=os.path.getsize(file_path),
        file_type=file.content_type
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    # Indexación RAG (soporte inicial TXT)
    if file.filename.lower().endswith(".txt"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Chunking básico por párrafos
                chunks = [c.strip() for c in content.split("\n\n") if len(c.strip()) > 10]
                for i, chunk in enumerate(chunks):
                    await add_document(
                        user_id=current_user.id,
                        content=chunk,
                        doc_metadata={
                            "source": "vault",
                            "filename": file.filename,
                            "file_id": db_file.id,
                            "chunk": i
                        }
                    )
                db_file.processed = {"status": "indexed", "chunks": len(chunks)}
                db.commit()
        except Exception as e:
            print(f"Error indexando TXT: {e}")

    # Indexación RAG (soporte PDF)
    elif file.filename.lower().endswith(".pdf"):
        try:
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                full_text = ""
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n\n"
                
                # Chunking básico por párrafos
                chunks = [c.strip() for c in full_text.split("\n\n") if len(c.strip()) > 20]
                for i, chunk in enumerate(chunks):
                    await add_document(
                        user_id=current_user.id,
                        content=chunk,
                        doc_metadata={
                            "source": "vault",
                            "filename": file.filename,
                            "file_id": db_file.id,
                            "chunk": i
                        }
                    )
                db_file.processed = {"status": "indexed", "chunks": len(chunks)}
                db.commit()
        except Exception as e:
            print(f"Error indexando PDF: {e}")

    return {"message": "Archivo subido e indexado correctamente", "id": db_file.id}

@router.get("/")
async def list_files(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Lista los archivos del usuario"""
    return db.query(DocumentFile).filter(DocumentFile.user_id == current_user.id).all()

@router.delete("/{file_id}")
async def delete_file(
    file_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Elimina un archivo y sus metadatos"""
    db_file = db.query(DocumentFile).filter(
        DocumentFile.id == file_id, 
        DocumentFile.user_id == current_user.id
    ).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    # Borrar físico
    if os.path.exists(db_file.filepath):
        try:
            os.remove(db_file.filepath)
        except Exception as e:
            print(f"Error deleting physical file: {e}")
        
    # Borrar del RAG (si tenía trozos indexados)
    try:
        from app.rag.engine import delete_documents
        # Buscamos por el ID del archivo en la metadata
        await delete_documents(current_user.id, query=f'"file_id": {db_file.id}')
    except Exception as e:
        print(f"Error deleting RAG chunks for file {file_id}: {e}")

    db.delete(db_file)
    db.commit()
    return {"message": "Archivo y su contenido en memoria eliminados correctamente"}

@router.get("/download/{file_id}")
async def download_file(
    file_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Descarga un archivo físico"""
    db_file = db.query(DocumentFile).filter(
        DocumentFile.id == file_id, 
        DocumentFile.user_id == current_user.id
    ).first()
    
    if not db_file or not os.path.exists(db_file.filepath):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    return FileResponse(
        path=db_file.filepath, 
        filename=db_file.filename,
        media_type=db_file.file_type
    )
