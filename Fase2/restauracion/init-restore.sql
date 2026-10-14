-- ============================================================
-- init-restore.sql
-- Sincroniza la clave de root al iniciar la instancia restaurada.
-- Configurado con la clave local 'admin' del usuario.
-- ============================================================
CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY 'admin';
CREATE USER IF NOT EXISTS 'root'@'localhost' IDENTIFIED BY 'admin';
ALTER USER 'root'@'%' IDENTIFIED BY 'admin';
ALTER USER 'root'@'localhost' IDENTIFIED BY 'admin';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' WITH GRANT OPTION;
FLUSH PRIVILEGES;
