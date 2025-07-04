BEGIN;

-- Eliminar solo imágenes dinámicas (no base) de todos los estudiantes
DELETE FROM personas_estudiantefoto
WHERE es_base = false;

COMMIT;
