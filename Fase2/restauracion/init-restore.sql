-- ============================================================
-- init-restore.sql
-- Sincroniza la clave de root al iniciar la instancia restaurada,
-- garantizando acceso con la clave local definida en .env.
-- ============================================================
CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY 'Cambiar_Esta_Clave_Local_2026';
CREATE USER IF NOT EXISTS 'root'@'localhost' IDENTIFIED BY 'Cambiar_Esta_Clave_Local_2026';
ALTER USER 'root'@'%' IDENTIFIED BY 'Cambiar_Esta_Clave_Local_2026';
ALTER USER 'root'@'localhost' IDENTIFIED BY 'Cambiar_Esta_Clave_Local_2026';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' WITH GRANT OPTION;
FLUSH PRIVILEGES;
