@echo off
setlocal
title Fase 2 - Detener MySQL
pushd "%~dp0"

if not exist ".env" (
    echo No existe Fase2\.env. Se necesita para ejecutar Docker Compose.
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

echo Deteniendo los servicios de Fase 2 sin borrar el volumen...
docker compose --project-directory "%CD%" --env-file "%CD%\.env" -f "%CD%\docker-compose.yml" down
if errorlevel 1 goto :fail

echo.
echo Fase 2 esta detenida. La base de datos y los respaldos se conservaron.
echo No se uso el parametro -v; el volumen sigue disponible.
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
