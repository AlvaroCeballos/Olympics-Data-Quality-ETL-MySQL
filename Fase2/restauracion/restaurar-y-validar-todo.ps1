# ============================================================
# restaurar-y-validar-todo.ps1
# Script maestro para orquestar la restauracion y validacion
# de los ciclos de respaldo en el entorno aislado.
#
# Uso:
#   .\restaurar-y-validar-todo.ps1 -Ciclo deportista
#   .\restaurar-y-validar-todo.ps1 -Ciclo deporte
#   .\restaurar-y-validar-todo.ps1 -Ciclo anio
#   .\restaurar-y-validar-todo.ps1 -Todos
#   .\restaurar-y-validar-todo.ps1 -Ciclo deportista -PausarParaCapturas
#
# Integrante 3 — Proyecto Fase 2, Grupo 18
# ============================================================

[CmdletBinding()]
param(
    [ValidateSet('deportista', 'deporte', 'anio')]
    [string]$Ciclo = 'deportista',

    [switch]$Todos,

    [switch]$PausarParaCapturas
)

. (Join-Path $PSScriptRoot '_common_restore.ps1')

$ciclosAEjecutar = if ($Todos) { @('deportista', 'deporte', 'anio') } else { @($Ciclo) }

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " ORQUESTADOR MAESTRO DE RESTAURACION Y VALIDACION" -ForegroundColor Cyan
Write-Host " Ciclos a procesar: $($ciclosAEjecutar -join ', ')" -ForegroundColor Cyan
Write-Host " Pausa para capturas: $($PausarParaCapturas.IsPresent)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

foreach ($c in $ciclosAEjecutar) {
    Write-Host ""
    Write-Host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>" -ForegroundColor Magenta
    Write-Host " PROCESANDO CICLO: $($c.ToUpper())" -ForegroundColor Magenta
    Write-Host ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>" -ForegroundColor Magenta

    # Paso 1: C0 - Full (Catalogos)
    Write-Host "`n--- PASO 1/4: C0 - Full ($c) ---" -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot 'restore-full.ps1') -Ciclo $c
    & (Join-Path $PSScriptRoot 'validar-restauracion.ps1') -Ciclo $c -Carga 'c0' -SaveReport
    if ($PausarParaCapturas) {
        Write-Host ">>> Presione ENTER para continuar tras tomar las capturas de c0 ($c)..." -ForegroundColor White
        Read-Host
    }

    # Paso 2: C1 - Ronda 1 (Diferencial 1)
    Write-Host "`n--- PASO 2/4: C1 - Ronda 1 ($c) ---" -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot 'restore-differential.ps1') -Ciclo $c -Ronda 'c1'
    & (Join-Path $PSScriptRoot 'validar-restauracion.ps1') -Ciclo $c -Carga 'c1' -SaveReport
    if ($PausarParaCapturas) {
        Write-Host ">>> Presione ENTER para continuar tras tomar las capturas de c1 ($c)..." -ForegroundColor White
        Read-Host
    }

    # Paso 3: C2 - Ronda 2 (Diferencial 2)
    Write-Host "`n--- PASO 3/4: C2 - Ronda 2 ($c) ---" -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot 'restore-differential.ps1') -Ciclo $c -Ronda 'c2'
    & (Join-Path $PSScriptRoot 'validar-restauracion.ps1') -Ciclo $c -Carga 'c2' -SaveReport
    if ($PausarParaCapturas) {
        Write-Host ">>> Presione ENTER para continuar tras tomar las capturas de c2 ($c)..." -ForegroundColor White
        Read-Host
    }

    # Paso 4: C3 - Ronda 3 (Diferencial 3)
    Write-Host "`n--- PASO 4/4: C3 - Ronda 3 ($c) ---" -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot 'restore-differential.ps1') -Ciclo $c -Ronda 'c3'
    & (Join-Path $PSScriptRoot 'validar-restauracion.ps1') -Ciclo $c -Carga 'c3' -SaveReport
    if ($PausarParaCapturas) {
        Write-Host ">>> Presione ENTER para continuar tras tomar las capturas de c3 ($c)..." -ForegroundColor White
        Read-Host
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " ORQUESTACION DE CICLOS FINALIZADA CON EXITO" -ForegroundColor Green
Write-Host " Revise Fase2/logs/bitacora_restauracion.csv para los tiempos." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
