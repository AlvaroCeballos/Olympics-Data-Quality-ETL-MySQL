@echo off
setlocal
title Fase 2 - Iniciar MySQL
pushd "%~dp0"

if not exist ".env" (
    echo No existe Fase2\.env.
    echo Desde la raiz del repositorio, en PowerShell, ejecute:
    echo   Copy-Item Fase2/.env.example Fase2/.env
    echo   Copy-Item Fase2/backup/xtrabackup.cnf.example Fase2/backup/xtrabackup.cnf
    echo Edite ambos archivos y use la misma contrasena.
    goto :fail
)

where docker >nul 2>&1
if errorlevel 1 (
    echo No se encontro Docker. Instale o inicie Docker Desktop.
    goto :fail
)

docker info >nul 2>&1
if errorlevel 1 (
    echo Docker Desktop no parece estar iniciado. Inicielo e intente de nuevo.
    goto :fail
)

echo Iniciando MySQL de Fase 2...
docker compose --project-directory "%CD%" --env-file "%CD%\.env" -f "%CD%\docker-compose.yml" up -d mysql
if errorlevel 1 goto :fail

docker compose --project-directory "%CD%" --env-file "%CD%\.env" -f "%CD%\docker-compose.yml" ps
if errorlevel 1 goto :fail

if not exist "backup\xtrabackup.cnf" (
    echo AVISO: MySQL esta iniciado, pero falta backup\xtrabackup.cnf para ejecutar respaldos.
    echo Copie y configure backup\xtrabackup.cnf.example antes del primer backup.
)
echo.
echo Fase 2 esta iniciada. MySQL se conecta en 127.0.0.1:3307.
echo El volumen persistente se conserva al detener con stop.bat.
goto :success

:success
popd
echo.
pause
exit /b 0

:fail
popd
echo.
pause
exit /b 1
