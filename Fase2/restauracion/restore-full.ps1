# ============================================================
# restore-full.ps1
# Restaura un respaldo FULL fisico en el entorno aislado.
#
# Estrategia: Completo (XtraBackup 8.0)
# Base de datos: olimpiadas (instancia fase2_mysql_restore, puerto 3307)
#
# Uso:
#   .\restore-full.ps1 -Ciclo deportista
#   .\restore-full.ps1 -Ciclo deporte
#   .\restore-full.ps1 -Ciclo anio
#   .\restore-full.ps1 -BackupFull full_20261012_210023
#
# Integrante 3 — Proyecto Fase 2, Grupo 18
# ============================================================

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('deportista', 'deporte', 'anio')]
    [string]$Ciclo = 'deportista',

    [Parameter(Position = 1)]
    [string]$BackupFull = '',

    [switch]$SkipCleanup
)

. (Join-Path $PSScriptRoot '_common_restore.ps1')

try {
    Initialize-Fase2Restore

    # 1. Resolver nombre del backup full si no se especifico directamente
    if ([string]::IsNullOrWhiteSpace($BackupFull)) {
        if ($script:DefinitiveSets.ContainsKey($Ciclo)) {
            $BackupFull = $script:DefinitiveSets[$Ciclo]['full']
        } else {
            throw "Debe indicar un -Ciclo valido ('deportista', 'deporte', 'anio') o un -BackupFull."
        }
    }

    Assert-BackupExists -Name $BackupFull

    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host " INICIANDO RESTAURACION FULL (C0 - CATALOGOS)" -ForegroundColor Cyan
    Write-Host " Ciclo:       $Ciclo" -ForegroundColor Cyan
    Write-Host " Respaldo:    $BackupFull" -ForegroundColor Cyan
    Write-Host " Entorno:     Aislado ($($script:RestoreVolumeName))" -ForegroundColor Cyan
    Write-Host " Hora inicio: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan

    $logFile = Join-Path $script:LogRoot "restore_${BackupFull}.log"
    if (Test-Path -LiteralPath $logFile) { Remove-Item -LiteralPath $logFile -Force }

    # 2. Detener contenedores activos para aislar y liberar el puerto 3307
    Stop-AllFase2Containers

    # 3. Vaciar unicamente el volumen aislado
    Clear-RestoreVolume

    # 4. Iniciar cronometro de recuperacion
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

    # 5. Crear copia de trabajo en _restore_work (respalda los originales)
    New-WorkingCopy -BackupNames @($BackupFull)

    # 6. Preparar el backup full (--prepare in-place sobre la copia)
    Write-Host "  [2/5] Preparando respaldo full con XtraBackup (--prepare)..." -ForegroundColor Yellow
    Invoke-XBRestore -XBArgs @(
        '--prepare',
        '--target-dir', "/work/$BackupFull"
    ) -LogPath $logFile

    # 7. Copiar los datos al volumen aislado (--copy-back)
    Write-Host "  [3/5] Restaurando datos al volumen MySQL (--copy-back)..." -ForegroundColor Yellow
    Invoke-XBRestore -XBArgs @(
        '--copy-back',
        '--target-dir', "/work/$BackupFull",
        '--datadir', '/var/lib/mysql'
    ) -LogPath $logFile -MountDataVolume

    # 8. Ajustar permisos para usuario mysql (uid 999)
    Write-Host "  [4/5] Ajustando permisos de propiedad (chown 999:999)..." -ForegroundColor Yellow
    Set-RestoreOwnership

    # 9. Iniciar el contenedor aislado de MySQL y verificar salud
    Write-Host "  [5/5] Iniciando base de datos y esperando validacion de salud..." -ForegroundColor Yellow
    Start-RestoreMySQLAndWait

    $stopwatch.Stop()
    $duration = $stopwatch.Elapsed.TotalSeconds

    # 10. Registrar en la bitacora oficial
    Add-RestoreRecord `
        -Ciclo $Ciclo `
        -Carga 'c0' `
        -Estrategia 'full' `
        -BackupFull $BackupFull `
        -DuracionSegundos $duration `
        -Resultado 'OK'

    # 11. Limpieza del directorio temporal
    if (-not $SkipCleanup) {
        Remove-WorkingCopy
    }

    Write-Host "============================================================" -ForegroundColor Green
    Write-Host " RESTAURACION FULL COMPLETADA CON EXITO" -ForegroundColor Green
    Write-Host " Duracion total: $([math]::Round($duration, 2)) segundos ($($stopwatch.Elapsed.ToString('mm\:ss\.fff')))" -ForegroundColor Green
    Write-Host " Log generado:   $logFile" -ForegroundColor Green
    Write-Host " Para validar y verificar alertas de integridad, ejecute:" -ForegroundColor White
    Write-Host "   .\validar-restauracion.ps1 -Ciclo $Ciclo -Carga c0" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host " ERROR EN RESTAURACION FULL: $_" -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Red
    if ($stopwatch -and $stopwatch.IsRunning) { $stopwatch.Stop() }
    Add-RestoreRecord `
        -Ciclo $Ciclo `
        -Carga 'c0' `
        -Estrategia 'full' `
        -BackupFull $BackupFull `
        -DuracionSegundos ($stopwatch.Elapsed.TotalSeconds) `
        -Resultado "ERROR: $_"
    exit 1
}
