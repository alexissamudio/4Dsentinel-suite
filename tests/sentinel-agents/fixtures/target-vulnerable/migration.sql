-- FIXTURE: cambio PLANTADO de alto riesgo para el risk-assessor.
-- [PLANTADO] migración destructiva e IRREVERSIBLE sobre datos de producción:
-- borra una tabla de auditoría y elimina una columna sin backup ni rollback.
-- No hay `IF EXISTS`, no hay copia previa, no hay paso de reversión.

DROP TABLE audit_log;

ALTER TABLE users DROP COLUMN legacy_password_hash;
