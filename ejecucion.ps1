$ErrorActionPreference = "Stop"

echo "=== 1. Ejecutando Fase 0 (Inicialización de Base de Datos y DDL) ==="
python -m etl.fase0_ddl

echo "=== 2. Ejecutando Pipeline ETL (Fases 1 a 7) ==="
python -m etl.fase1_dimensionales
python -m etl.fase2_atletas
python -m etl.fase3_contexto
python -m etl.fase4_participacion_base
python -m etl.fase5_enriquecimiento
python -m etl.fase6_actualizacion
python -m etl.fase7_validacion

echo "=== 3. Cargando Stored Procedures ==="
python -m etl.stored_procedures

echo "=== ¡Proceso completado con éxito! ==="