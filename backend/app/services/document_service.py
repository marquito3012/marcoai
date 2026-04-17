"""
MarcoAI – Document Service (Fase 9)
══════════════════════════════════════════════════════════════════════════════

Servicio para procesar documentos subidos, extraer el texto, dividirlo en
chunks, pasarlo por el modelo de embeddings, y guardar los vectores en
SQLite-vec de manera asíncrona pero ligera.
"""
from __future__ import annotations

import logging
import os
import sqlite3
from typing import Any
import asyncio

import fitz  # PyMuPDF
from fastapi import UploadFile
from langchain_text_splitters import RecursiveCharacterTextSplitter
from google.oauth2.credentials import Credentials

# Para embeddings usamos Gemini API directo o vía LangChain
# Dado que ya tenemos langchain-google-genai, lo usamos acá
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import AsyncSessionLocal
from app.db.models import Document, User

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class DocumentService:
    def __init__(self, db: AsyncSession, user_id: str):
        self.db = db
        self.user_id = user_id
        # We will use Gemini embeddings (embedding-001 is stable and compatible)
        self.embeddings_model = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001", 
            google_api_key=settings.google_api_key
        )
        self._vec_loaded = False

    async def _ensure_vec_loaded(self):
        if self._vec_loaded:
            return
        import sqlite_vec
        try:
            # We get the underlying aiosqlite connection from the AsyncSession
            conn = await self.db.connection()
            # In SQLAlchemy 2.0+ async, we can access the driver connection
            raw_conn = await conn.engine.raw_connection()
            # aiosqlite connection is at ._connection
            await raw_conn._connection.load_extension(sqlite_vec.loadable_path())
        except Exception as e:
            logger.warning(f"Failed to load sqlite_vec extension dynamically: {e}")
        self._vec_loaded = True
        
    async def ingest_file(self, file: UploadFile) -> Document:
        """Guarda archivo local y encula el procesamiento en base de datos."""
        content = await file.read()
        file_path = os.path.join(UPLOAD_DIR, f"{self.user_id}_{file.filename}")
        
        with open(file_path, "wb") as f:
            f.write(content)

        doc = Document(
            user_id=self.user_id,
            filename=file.filename,
            mime_type=file.content_type,
            size_bytes=len(content),
            status="pending"
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        
        return doc

    async def get_documents(self) -> list[Document]:
        """Lista los documentos del usuario."""
        from sqlalchemy import select
        res = await self.db.execute(select(Document).where(Document.user_id == self.user_id))
        return list(res.scalars().all())
    
    async def process_document_background(self, doc_id: str):
        """Tarea pesada en segundo plano para procesar y vectorializar el documento."""
        await self._ensure_vec_loaded()
        try:
            doc = await self.db.get(Document, doc_id)
            if not doc:
                return
            
            doc.status = "processing"
            await self.db.commit()

            file_path = os.path.join(UPLOAD_DIR, f"{self.user_id}_{doc.filename}")
            
            text_content = ""
            if doc.filename.endswith(".pdf"):
                # Para ahorrar memoria, abrir y parsear rápido
                with fitz.open(file_path) as pdf_doc:
                    for page in pdf_doc:
                        text_content += page.get_text() + "\n"
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    text_content = f.read()

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
                is_separator_regex=False,
            )
            chunks = text_splitter.split_text(text_content)

            # Insert vectors in batch
            for idx, chunk in enumerate(chunks):
                # Request embedding
                embedding = await asyncio.to_thread(self.embeddings_model.embed_query, chunk)

                # sqlite-vec expects raw python list of floats (already provided by embed_query)
                # and serialised via json.dumps(embedding).
                # Actually, sqlalchemy parameterized inputs into sqlite-vec must use JSON or specifically formatted blobs.
                import json
                await self.db.execute(
                    text("""
                        INSERT INTO vec_document_chunks (embedding, document_id, chunk_index, content)
                        VALUES (:emb, :doc_id, :c_index, :c_content)
                    """),
                    {
                        "emb": json.dumps(embedding),
                        "doc_id": doc.id,
                        "c_index": idx,
                        "c_content": chunk
                    }
                )

            doc.status = "completed"
            await self.db.commit()
            logger.info("Procesamiento RAG completado para doc_id=%s", doc.id)

        except Exception as exc:
            logger.error("Error al vectorizar doc_id=%s: %s", doc_id, exc)
            if doc:
                doc.status = "error"
                await self.db.commit()
            raise

    async def search_similar(self, query: str, top_k: int = 3) -> list[str]:
        """Realiza la búsqueda de los N chunks más similares en base al Query."""
        await self._ensure_vec_loaded()
        # Embed query
        query_embedding = await asyncio.to_thread(self.embeddings_model.embed_query, query)
        import json
        
        # We need to filter by user's documents. To do this, we join with documents table.
        # sqlite-vec uses `vec_distance_l2` in ORDER BY
        stmt = text("""
            SELECT v.content, d.filename 
            FROM vec_document_chunks v
            JOIN documents d ON v.document_id = d.id
            WHERE d.user_id = :uid
            ORDER BY vec_distance_L2(v.embedding, :q_emb)
            LIMIT :k
        """)
        
        res = await self.db.execute(stmt, {
            "uid": self.user_id, 
            "q_emb": json.dumps(query_embedding), 
            "k": top_k
        })
        
        results = []
        for row in res.fetchall():
            results.append(f"[Documento: {row[1]}] {row[0]}")
            
        return results

    async def delete_document(self, doc_id: str) -> bool:
        doc = await self.db.get(Document, doc_id)
        if not doc or doc.user_id != self.user_id:
            return False
            
        file_path = os.path.join(UPLOAD_DIR, f"{self.user_id}_{doc.filename}")
        if os.path.exists(file_path):
            os.remove(file_path)

        # Delete embeddings
        await self.db.execute(text("DELETE FROM vec_document_chunks WHERE document_id = :did"), {"did": doc_id})
        
        # Delete document record
        await self.db.delete(doc)
        await self.db.commit()
        return True
