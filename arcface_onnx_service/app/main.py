import os
import json
import uuid
import numpy as np
import psycopg2
from datetime import datetime
from collections import defaultdict
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from insightface.app import FaceAnalysis
from io import BytesIO
from pydantic import BaseModel
from PIL import Image

# ----------------------------
# Configuración desde ENV
# ----------------------------
PG_CONFIG = {
    'dbname':   os.getenv('PG_DB',       'SCOUT_DB'),
    'user':     os.getenv('PG_USER',     'postgres'),
    'password': os.getenv('PG_PASSWORD', '12345678'),
    'host': os.getenv('PG_HOST', 'db'),
    'port':     int(os.getenv('PG_PORT', '5432')),
}
THRESHOLD = float(os.getenv('THRESHOLD', '0.5'))


IMAGE_SAVE_PATH = os.getenv(
    "IMAGE_SAVE_PATH",
    "media/estudiantes/fotos_extra"
)
os.makedirs(IMAGE_SAVE_PATH, exist_ok=True)

# ----------------------------
# FastAPI & CORS
# ----------------------------
app = FastAPI(title="ArcFace ONNX Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"],  allow_headers=["*"],
)

# ----------------------------
# Modelo ArcFace
# ----------------------------
print("🧠 Inicializando modelo ArcFace...")
face_app = FaceAnalysis(providers=['CPUExecutionProvider'])
face_app.prepare(ctx_id=0, det_size=(640, 640))
print("✅ Modelo listo.")



# ----------------------------
# Pydantic schema for incremental embedding
# ----------------------------
class EmbeddingIn(BaseModel):
    estudiante_id: int
    embedding: list[float]




# ----------------------------
# Embeddings cache
# ----------------------------
embeddings_dict: dict[int, list[np.ndarray]] = {}

def load_embeddings() -> dict[int, list[np.ndarray]]:
    print("📥 Iniciando carga de embeddings desde la base de datos...")
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT estudiante_id, embedding FROM personas_estudiantefoto WHERE embedding IS NOT NULL")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    embs = defaultdict(list)
    for est_id, emb_val in rows:
        if isinstance(emb_val, (bytes, bytearray, memoryview)):
            raw = emb_val.tobytes() if isinstance(emb_val, memoryview) else emb_val
            emb = np.frombuffer(raw, dtype=np.float32)
        else:
            print(f"⚠️ El embedding del estudiante {est_id} es str, convirtiendo desde JSON...")
            arr = json.loads(emb_val)
            emb = np.array(arr, dtype=np.float32)
        embs[est_id].append(emb)

    print("📦 Embeddings cargados por estudiante:")
    for eid, e in embs.items():
        print(f"  👤 Estudiante ID={eid}: {len(e)} embedding(s)")
    print(f"✅ Total embeddings: {sum(len(v) for v in embs.values())}, estudiantes únicos: {len(embs)}")
    return embs

@app.on_event("startup")
def startup_event():
    global embeddings_dict
    try:
        embeddings_dict = load_embeddings()
    except Exception as e:
        print(f"⚠️ No se pudieron cargar embeddings: {e}")
        embeddings_dict = {}
    print(f"▶ Conectado a {PG_CONFIG['host']}:{PG_CONFIG['port']} DB={PG_CONFIG['dbname']}, THRESHOLD={THRESHOLD}")

# ----------------------------
# Guardar imagen dinámica con política FIFO
# ----------------------------
def guardar_imagen_dinamica(estudiante_id: int, image: Image.Image, embedding: np.ndarray):
    # ✅ Ruta real al media/ de Django
    IMAGE_SAVE_PATH = os.getenv("IMAGE_SAVE_PATH", "/app/media/estudiantes/fotos_extra")
    os.makedirs(IMAGE_SAVE_PATH, exist_ok=True)

    # 📝 Nombre de archivo con timestamp
    filename = f"{estudiante_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpeg"
    filepath = os.path.join(IMAGE_SAVE_PATH, filename)

    # 💾 Guardar imagen
    image.save(filepath, "JPEG")
    print(f"🖼️ Imagen dinámica guardada: {filepath}")

    # 📦 Insertar en PostgreSQL
    emb_bytes = embedding.astype(np.float32).tobytes()
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    # 📜 Verificar dinámicas anteriores
    cur.execute("""
        SELECT id FROM personas_estudiantefoto
        WHERE estudiante_id = %s AND NOT es_base
        ORDER BY created_at ASC
    """, (estudiante_id,))
    dinamicas = cur.fetchall()
    print(f"📸 Dinámicas actuales para estudiante {estudiante_id}: {[d[0] for d in dinamicas]}")

    # ♻️ Eliminar la más antigua si hay más de 3
    dinamicas = cur.fetchall()
    if dinamicas:
        tupla = dinamicas[0]
        if len(tupla) == 2:
            id_antiguo, img_rel = tupla
             # … eliminar archivo y registro …
        else:
            print(f"⚠️ Tupla inesperada: {tupla!r}")
    else:
        print("⚠️ No hay imágenes dinámicas que procesar.")
    # 📤 Insertar nueva
        embedding_list = embedding.astype(np.float32).tolist()
    cur.execute("""
        INSERT INTO personas_estudiantefoto (imagen, es_base, created_at, estudiante_id, embedding)
        VALUES (%s, FALSE, %s, %s, %s)
    """, (f"estudiantes/fotos_extra/{filename}", datetime.now(), estudiante_id, embedding_list))

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Nueva dinámica insertada.")




# ----------------------------
# Endpoint incremental para añadir embedding nuevo\ n# ----------------------------
@app.post("/add_embedding/")
async def add_embedding(data: EmbeddingIn):
    global embeddings_dict, face_app
    vec = np.array(data.embedding, dtype=np.float32)
    face_app.db.add(data.estudiante_id, vec)
    embeddings_dict.setdefault(data.estudiante_id, []).append(vec)
    print(f"➕ Embedding incremental agregado para estudiante {data.estudiante_id}")
    return {"ok": True, "msg": f"Embedding añadido para {data.estudiante_id}"}






# ----------------------------
# Endpoints HTTP
# ----------------------------
@app.post("/generar_embedding/")
async def generar_embedding(file: UploadFile = File(...)):
    try:
        content = await file.read()
        image = Image.open(BytesIO(content)).convert("RGB")
        print(f"📥 Imagen recibida: {file.filename}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al procesar imagen: {e}")

    faces = face_app.get(np.array(image))
    print(f"🔍 Rostros detectados: {len(faces)}")

    if not faces:
        return {"ok": False, "msg": "No se detectó rostro"}

    embedding = faces[0].embedding.tolist()
    return {"ok": True, "embedding": embedding}


@app.post("/match_faces/")
async def match_faces(file: UploadFile = File(...)):
    try:
        image = Image.open(BytesIO(await file.read())).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error leyendo imagen: {e}")

    faces = face_app.get(np.array(image))
    if not faces:
        return {"ok": False, "msg": "No se detectaron rostros"}

    results = []
    for f in faces:
        q = f.embedding.astype(np.float32)
        best_id, best_score = None, -1.0
        for est_id, emb_list in embeddings_dict.items():
            for emb in emb_list:
                sim = float(np.dot(q, emb) / (np.linalg.norm(q) * np.linalg.norm(emb) + 1e-8))
                if sim > best_score:
                    best_score, best_id = sim, est_id

        matched = best_score > THRESHOLD
        if matched:
            guardar_imagen_dinamica(best_id, image, f.embedding)

        results.append({
            "face_box": f.bbox.tolist(),
            "estudiante_id": best_id if matched else None,
            "similarity": best_score,
            "match": matched
        })

    return {"ok": True, "results": results}

# ----------------------------
# WebSocket para video en vivo
# ----------------------------
@app.websocket("/stream/")
async def stream_ws(ws: WebSocket):
    await ws.accept()
    print("✅ WebSocket conectado")
    try:
        while True:
            data = await ws.receive_bytes()
            image = Image.open(BytesIO(data)).convert("RGB")
            faces = face_app.get(np.array(image))
            print(f"🔍 {len(faces)} rostro(s) detectado(s)")
            matches = []

            for f in faces:
                q = f.embedding.astype(np.float32)
                best_id, best_score = None, -1.0
                for est_id, emb_list in embeddings_dict.items():
                    for emb in emb_list:
                        sim = float(np.dot(q, emb) / (np.linalg.norm(q) * np.linalg.norm(emb) + 1e-8))
                        if sim > best_score:
                            best_score, best_id = sim, est_id
                matched = best_score > THRESHOLD
                if matched:
                    guardar_imagen_dinamica(best_id, image, f.embedding)

                matches.append({
                    "match_id": best_id if matched else None,
                    "similarity": best_score
                })

            await ws.send_json({"matches": matches})
    except WebSocketDisconnect:
        print("❌ WebSocket desconectado")

# ----------------------------
# Reload embeddings
# ----------------------------
@app.get("/reload_embeddings/")
def reload_embeddings():
    global embeddings_dict
    embeddings_dict = load_embeddings()
    print("🔁 Embeddings recargados exitosamente")
    return {"ok": True, "msg": "Embeddings recargados"}
