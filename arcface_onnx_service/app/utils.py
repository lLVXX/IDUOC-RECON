# app/utils.py
from collections import defaultdict
import numpy as np
import psycopg2
from datetime import datetime
# Estructura en memoria: {estudiante_id: [emb1, emb2, emb3]}
embeddings_dict = defaultdict(list)

def compare_embeddings(embedding, threshold=0.5):
    """
    Devuelve coincidencias por estudiante_id con su menor distancia.
    """
    coincidencias = []
    for estudiante_id, emb_list in embeddings_dict.items():
        distancias = [cosine_distance(embedding, emb) for emb in emb_list]
        if not distancias:
            continue
        min_dist = min(distancias)
        if min_dist < threshold:
            coincidencias.append({
                "estudiante_id": estudiante_id,
                "distancia": float(min_dist),  # ✅ conversión segura
            })
    coincidencias.sort(key=lambda x: x["distancia"])
    return coincidencias

def cosine_distance(a, b):
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    return 1 - np.dot(a, b)







# -----------------------------------------
# Conexión básica a PostgreSQL
# -----------------------------------------
def conectar_db(pg_config):
    return psycopg2.connect(**pg_config)

# -----------------------------------------
# Leer todos los embeddings desde la BD
# -----------------------------------------
def obtener_embeddings_pg(pg_config):
    embeddings_dict = {}
    try:
        conn = conectar_db(pg_config)
        cur = conn.cursor()
        cur.execute("""
            SELECT estudiante_id, embedding
            FROM personas_estudiantefoto
            WHERE es_base = TRUE OR es_base = FALSE
        """)
        for est_id, emb_json in cur.fetchall():
            emb = np.array(emb_json, dtype=np.float32)
            embeddings_dict.setdefault(est_id, []).append(emb)
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error al cargar embeddings desde PostgreSQL: {e}")
    return embeddings_dict

# -----------------------------------------
# Comparar contra todos los embeddings
# -----------------------------------------
def comparar_embeddings(query_embedding, embeddings_dict):
    best_id = None
    best_score = -1.0

    for est_id, emb_list in embeddings_dict.items():
        for emb in emb_list:
            sim = float(np.dot(query_embedding, emb) /
                        (np.linalg.norm(query_embedding) * np.linalg.norm(emb) + 1e-8))
            if sim > best_score:
                best_score = sim
                best_id = est_id
    return best_id, best_score

# -----------------------------------------
# Guardar foto + embedding + aplicar FIFO
# -----------------------------------------
def guardar_foto_y_embedding_fifo(estudiante_id, img_bytes, is_base, pg_config, embedding):
    try:
        conn = conectar_db(pg_config)
        cur = conn.cursor()

        # Insertar nueva imagen
        cur.execute("""
            INSERT INTO personas_estudiantefoto (estudiante_id, imagen, es_base, created_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (estudiante_id, psycopg2.Binary(img_bytes), is_base, datetime.now()))
        foto_id = cur.fetchone()[0]

        # Insertar nuevo embedding
        cur.execute("""
            UPDATE personas_estudiantefoto
            SET embedding = %s
            WHERE id = %s
        """, (embedding, foto_id))

        # FIFO: borrar más antiguas si hay > 3 dinámicas (no base)
        cur.execute("""
            SELECT id FROM personas_estudiantefoto
            WHERE estudiante_id = %s AND es_base = FALSE
            ORDER BY created_at ASC
        """, (estudiante_id,))
        rows = cur.fetchall()

        if len(rows) > 3:
            ids_a_borrar = [r[0] for r in rows[:-3]]
            print(f"🗑️ Eliminando {len(ids_a_borrar)} imagen(es) antiguas del estudiante {estudiante_id}")
            cur.execute("""
                DELETE FROM personas_estudiantefoto
                WHERE id = ANY(%s)
            """, (ids_a_borrar,))

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error al guardar imagen y aplicar FIFO: {e}")
