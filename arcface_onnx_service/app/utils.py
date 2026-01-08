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

def guardar_foto_y_embedding_fifo(estudiante_id, image, embedding, pg_config, is_base=False):
    """
    Guarda imagen + embedding en PostgreSQL y disco, aplicando FIFO para dinámicas (>3).
    """
    try:
        # Obtener ruta desde ENV (ya dentro del contenedor)
        IMAGE_SAVE_PATH = os.getenv("IMAGE_SAVE_PATH", "/app/media/estudiantes/fotos_extra")
        os.makedirs(IMAGE_SAVE_PATH, exist_ok=True)

        # Nombre de archivo con timestamp
        filename = f"{estudiante_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpeg"
        filepath = os.path.join(IMAGE_SAVE_PATH, filename)

        # Guardar imagen en disco
        image.save(filepath, "JPEG")
        print(f"🖼️ Imagen dinámica guardada: {filepath}")

        # Conectar a PostgreSQL
        conn = psycopg2.connect(**pg_config)
        cur = conn.cursor()

        # Insertar nueva imagen
        cur.execute("""
            INSERT INTO personas_estudiantefoto (estudiante_id, imagen, es_base, created_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (estudiante_id, f"estudiantes/fotos_extra/{filename}", is_base, datetime.now()))
        foto_id = cur.fetchone()[0]

        # Insertar embedding
        cur.execute("""
            UPDATE personas_estudiantefoto
            SET embedding = %s
            WHERE id = %s
        """, (embedding.astype('float32').tolist(), foto_id))

        # FIFO: borrar más antiguas si hay >3 dinámicas (no base)
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
        print("✅ Nueva dinámica insertada.")

    except Exception as e:
        print(f"❌ Error al guardar imagen y aplicar FIFO: {e}")