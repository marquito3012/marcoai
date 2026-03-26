import sqlite3
import sqlite_utils
import json
import numpy as np
import io
from app.config import settings
from app.rag.embeddings import generate_embedding
import os

DB_PATH = os.path.abspath(settings.DATABASE_URL.replace("sqlite:///", ""))
print(f"📡 DB_PATH: {DB_PATH}")

# Necesitamos adaptador para arrays numpy en SQLite
def adapt_array(arr):
    out = io.BytesIO()
    np.save(out, arr)
    out.seek(0)
    return sqlite3.Binary(out.read())

def convert_array(text):
    out = io.BytesIO(text)
    out.seek(0)
    return np.load(out)

# Registra los adaptadores para SQLite
sqlite3.register_adapter(np.ndarray, adapt_array)
sqlite3.register_converter("array", convert_array)

def get_connection():
    # Detectamos extensiones VSS si están instaladas por el Dockerfile
    # print(f"🔌 CONNECTING TO: {DB_PATH}") # Descomentar para mega-debug
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.enable_load_extension(True)
    try:
        # En el container de producción con sqlite-vss
        import sqlite_vss
        sqlite_vss.load(conn)
    except Exception as e:
        print(f"sqlite-vss no cargado (ok para dev nativo sin compilar VSS): {e}")
    return conn

def init_rag_db():
    """Inicializa la tabla vectorial"""
    conn = get_connection()
    c = conn.cursor()
    # Tabla base
    c.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content TEXT,
            metadata TEXT,
            embedding array,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Migración voluntaria: si la columna no existe, la añadimos
    try:
        c.execute("ALTER TABLE documents ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
    except:
        pass # Ya existe
    
    c.execute("CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id)")
    conn.commit()
    
    # Intentamos crear la tabla virtual vss0 si sqlite-vss está disponible
    try:
         c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS vss_documents USING vss0(embedding(768))")
         conn.commit()
    except Exception as e:
         print("Virtual table vss no creada - Fallback manual habilitado. Razón:", e)
         
    conn.close()

async def add_document(user_id: int, content: str, doc_metadata: dict = None):
    """Agrega un documento al RAG exclusivo para un usuario"""
    if doc_metadata is None:
        doc_metadata = {}
        
    vec = await generate_embedding(content)
    vec_np = np.array(vec, dtype=np.float32)
    
    conn = get_connection()
    c = conn.cursor()
    
    print(f"📁 DB_ACTION: add_document | user={user_id} | content='{content[:30]}...' | metadata={doc_metadata}")
    # Insertar en tabla normal
    c.execute("INSERT INTO documents (user_id, content, metadata, embedding) VALUES (?, ?, ?, ?)",
              (user_id, content, json.dumps(doc_metadata), vec_np))
    doc_id = c.lastrowid
    
    # Intentar insertar en VSS (si existe la tabla)
    try:
        # vss usa json arrays stringificados
        c.execute("INSERT INTO vss_documents(rowid, embedding) VALUES (?, ?)", (doc_id, json.dumps(vec)))
    except:
        pass # fallback ya guardó en `documents.embedding`
        
    conn.commit()
    conn.close()
    return doc_id

async def search(user_id: int, query: str, top_k: int = 3):
    """Busca en el RAG filtrando por user_id."""
    query_vec = await generate_embedding(query)
    query_np = np.array(query_vec, dtype=np.float32)
    
    conn = get_connection()
    c = conn.cursor()
    
    results = []
    try:
        # Usamos VSS si está
        c.execute(f"""
            SELECT d.id, d.content, d.metadata 
            FROM vss_documents v
            JOIN documents d ON v.rowid = d.id
            WHERE d.user_id = ? AND vss_search(v.embedding, ?)
            LIMIT ?
        """, (user_id, json.dumps(query_vec), top_k))
        
        rows = c.fetchall()
        for row in rows:
            results.append({
                "id": row[0],
                "content": row[1],
                "metadata": json.loads(row[2]),
                "score": 0.0 # sqlite-vss retorna distancias, pero podemos simular
            })
    except Exception as e:
        print(f"VSS search failed, using python cosine similarity fallback: {e}")
        # Fallback de Coseno en Python PURO + Numpy (Ultra ligero) -> Puesto que filtramos por user, no son muchos docs
        c.execute("SELECT id, content, metadata, embedding FROM documents WHERE user_id = ?", (user_id,))
        rows = c.fetchall()
        
        scored = []
        for row in rows:
            doc_id, content, meta_str, doc_emb = row
            # Calculo de similitud coseno
            dot = np.dot(query_np, doc_emb)
            norm_q = np.linalg.norm(query_np)
            norm_d = np.linalg.norm(doc_emb)
            if norm_q > 0 and norm_d > 0:
                score = dot / (norm_q * norm_d)
            else:
                score = 0.0
            scored.append((score, {
                "id": doc_id,
                "content": content,
                "metadata": json.loads(meta_str),
                "score": float(score)
            }))
            
        # Ordenamos
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [x[1] for x in scored[:top_k]]
        
    conn.close()
    return results

async def delete_documents(user_id: int, tipo: str | None = None, query: str | None = None):
    """Elimina documentos del RAG de un usuario por tipo o contenido literal."""
    print(f"📁 DB_ACTION: delete_documents | user={user_id} | tipo={tipo} | query={query}")
    conn = get_connection()
    c = conn.cursor()
    
    from typing import Any
    deleted_count = 0
    sql = "DELETE FROM documents WHERE user_id = ?"
    params: list[Any] = [user_id]
    
    if tipo:
        # Buscamos en metadata {"tipo": "..."} o {"type": "..."} usando JSON nativo
        sql += " AND (json_extract(metadata, '$.tipo') = ? OR json_extract(metadata, '$.type') = ?)"
        params.extend([tipo, tipo])
    
    if query:
        # Si es un hábito, buscamos por nombre exacto en el campo nombre de la metadata
        if tipo == "habito":
            sql += " AND (json_extract(metadata, '$.nombre') LIKE ? OR content LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])
        else:
            # Buscamos coincidencia literal en contenido o metadatos (fallback)
            sql += " AND (content LIKE ? OR metadata LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])
        
    if not tipo and not query:
        # Si no hay filtros, borrar todo el cerebro del usuario (Peligroso, pero intencional)
        pass # La query base ya tiene el user_id
        
    c.execute(sql, tuple(params))
    deleted_count = c.rowcount
        
    # Sincronizar VSS: Eliminar huérfanos si la tabla virtual existe
    try:
        c.execute("DELETE FROM vss_documents WHERE rowid NOT IN (SELECT id FROM documents)")
    except Exception as e:
        print(f"Error syncing VSS after delete: {e}")
        
    conn.commit()
    conn.close()
    return deleted_count

async def get_habitos(user_id: int):
    """Recupera la lista de hábitos de un usuario."""
    habitos = []
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, content, metadata FROM documents WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    for row in rows:
        meta = json.loads(row[2])
        if meta.get("tipo") == "habito" or meta.get("type") == "habito":
            nombre = meta.get("nombre") or meta.get("titulo", "Hábito sin título")
            habitos.append({
                "id": row[0],
                "nombre": nombre,
                "completado": meta.get("completado", False)
            })
    conn.close()
    return habitos

async def toggle_habit(user_id: int, habit_name: int | str):
    """Alterna el estado de completado de un hábito."""
    print(f"📁 DB_ACTION: toggle_habit | user={user_id} | name='{habit_name}'")
    conn = get_connection()
    c = conn.cursor()
    
    # Buscar el hábito por tipo (o type) Y nombre usando funciones JSON nativas
    c.execute("""
        SELECT id, metadata FROM documents 
        WHERE user_id = ? 
        AND (json_extract(metadata, '$.tipo') = 'habito' OR json_extract(metadata, '$.type') = 'habito')
        AND json_extract(metadata, '$.nombre') LIKE ?
    """, (user_id, f"%{habit_name}%"))
    row = c.fetchone()
    
    if not row:
        print(f"⚠️ toggle_habit: No se encontró el hábito '{habit_name}' para el usuario {user_id}")
        conn.close()
        return False
        
    doc_id, meta_str = row
    meta = json.loads(meta_str)
    
    # Alternar
    is_done = meta.get("completado", False)
    meta["completado"] = not is_done
    
    print(f"💾 DB_UPDATE: toggle_habit | doc_id={doc_id} | old_state={is_done} | new_state={meta['completado']}")
    c.execute("UPDATE documents SET metadata = ? WHERE id = ?", (json.dumps(meta), doc_id))
    if c.rowcount == 0:
        print(f"❌ ERROR: No se actualizó ninguna fila para doc_id={doc_id}")
    else:
        print(f"✅ SUCCESS: Hábito actualizado en DB. rowcount={c.rowcount}")
    
    conn.commit()
    conn.close()
    return meta["completado"]
