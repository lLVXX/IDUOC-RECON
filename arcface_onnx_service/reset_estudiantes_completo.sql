BEGIN;

-- 1. Eliminar relaciones estudiante-asignatura-seccion
DELETE FROM personas_estudianteasignaturaseccion
WHERE estudiante_id IN (
    SELECT id FROM core_customuser WHERE user_type = 'estudiante'
);

-- 2. Eliminar todas las fotos de los estudiantes (base + dinámicas)
DELETE FROM personas_estudiantefoto
WHERE estudiante_id IN (
    SELECT id FROM core_customuser WHERE user_type = 'estudiante'
);

-- 3. Eliminar usuarios tipo estudiante
DELETE FROM core_customuser
WHERE user_type = 'estudiante';

COMMIT;
