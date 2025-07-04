-- 1. Asegurarse de que la extensión esté activa
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Verificar o crear la tabla (ajusta nombres y tipos si es necesario)
CREATE TABLE IF NOT EXISTS personas_estudiantefoto (
    id SERIAL PRIMARY KEY,
    estudiante_id INTEGER NOT NULL,
    imagen BYTEA,
    es_base BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    embedding vector(512)
);
---- Ejecucion ---- docker compose exec db psql -U postgres -d SCOUT_DB -f /carga/setup_pgvector.sql


