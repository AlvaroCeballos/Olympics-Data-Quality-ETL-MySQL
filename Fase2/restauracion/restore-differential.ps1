# ============================================================
# restore-differential.ps1
# Restaura un respaldo DIFERENCIAL fisico en el entorno aislado.
#
# Estrategia: Diferencial (XtraBackup 8.0)
# Proceso:
#   1. Copia de trabajo limpia de Full + Diff a _restore_work
#   2. xtrabackup --prepare --apply-log-only sobre la copia del Full
#   3. xtrabackup --prepare --incremental-dir=<diff> sobre el Full
#   4. xtrabackup --prepare final (rollback de no confirmadas)
#   5. xtrabackup --copy-back hacia el volumen aislado
#   6. Ajuste de permisos (999:999) y arranque del servicio
#
# Uso:
#   .\restore-differential.ps1 -Ciclo deportista -Ronda c1
#   .\restore-differential.ps1 -Ciclo deporte -Ronda c2
#   .\restore-differential.ps1 -Ciclo anio -Ronda c3
#   .\restore-differential.ps1 -BackupFull full_... -BackupDiff diff_...
#
# Integrante 3 — Proyecto Fase 2, Grupo 18
# ============================================================

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('deportista', 'deporte', 'anio')]
    [string]$Ciclo = 'deportista',

    [Parameter(Position = 1)]
    [ValidateSet('c1', 'c2', 'c3')]
    [string]$Ronda = 'c1',

    [Parameter(Position = 2)]
    [string]$BackupDiff = '',

    [Parameter(Position = 3)]
    [string]$BackupFull = '',

    [switch]$SkipCleanup
)

. (Join-Path $PSScriptRoot '_common_restore.ps1')

try {
    Initialize-Fase2Restore

    # 1. Resolver nombres si no se indicaron directamente
    if ([string]::IsNullOrWhiteSpace($BackupFull)) {
        if ($script:DefinitiveSets.ContainsKey($Ciclo)) {
            $BackupFull = $script:DefinitiveSets[$Ciclo]['full']
        } else {
            throw "Debe indicar un -Ciclo valido ('deportista', 'deporte', 'anio')."
        }
    }

    if ([string]::IsNullOrWhiteSpace($BackupDiff)) {
        if ($script:DefinitiveSets.ContainsKey($Ciclo) -and $script:DefinitiveSets[$Ciclo].ContainsKey($Ronda)) {
            $BackupDiff = $script:DefinitiveSets[$Ciclo][$Ronda]
        } else {
            throw "Debe indicar una -Ronda valida ('c1', 'c2', 'c3') o un -BackupDiff."
        }
    }

    Assert-BackupExists -Name $BackupFull
    Assert-BackupExists -Name $BackupDiff

    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host " INICIANDO RESTAURACION DIFERENCIAL" -ForegroundColor Cyan
    Write-Host " Ciclo:       $Ciclo" -ForegroundColor Cyan
    Write-Host " Ronda/Carga: $Ronda" -ForegroundColor Cyan
    Write-Host " Base Full:   $BackupFull" -ForegroundColor Cyan
    Write-Host " Diferencial: $BackupDiff" -ForegroundColor Cyan
    Write-Host " Entorno:     Aislado ($($script:RestoreVolumeName))" -ForegroundColor Cyan
    Write-Host " Hora inicio: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan

    $logFile = Join-Path $script:LogRoot "restore_${BackupDiff}.log"
    if (Test-Path -LiteralPath $logFile) { Remove-Item -LiteralPath $logFile -Force }

    # 2. Detener contenedores activos para aislar y liberar el puerto 3307
    Stop-AllFase2Containers

    # 3. Vaciar unicamente el volumen aislado
    Clear-RestoreVolume

    # 4. Iniciar cronometro de recuperacion
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

    # 5. Crear copia de trabajo en _restore_work de AMBOS respaldos
    New-WorkingCopy -BackupNames @($BackupFull, $BackupDiff)

    # 6. Paso A: Prepare del Full con --apply-log-only
    Write-Host "  [2/6] Preparando Full base (--apply-log-only)..." -ForegroundColor Yellow
    Invoke-XBRestore -XBArgs @(
        '--prepare',
        '--apply-log-only',
        '--target-dir', "/work/$BackupFull"
    ) -LogPath $logFile

    # 7. Paso B: Aplicar delta diferencial sobre el Full
    Write-Host "  [3/6] Aplicando delta diferencial (--incremental-dir)..." -ForegroundColor Yellow
    Invoke-XBRestore -XBArgs @(
        '--prepare',
        '--target-dir', "/work/$BackupFull",
        '--incremental-dir', "/work/$BackupDiff"
    ) -LogPath $logFile

    # 8. Paso C: Prepare final del Full (rollback de transacciones no confirmadas)
    Write-Host "  [4/6] Finalizando preparacion de datos (prepare final)..." -ForegroundColor Yellow
    Invoke-XBRestore -XBArgs @(
        '--prepare',
        '--target-dir', "/work/$BackupFull"
    ) -LogPath $logFile

    # 9. Paso D: Copiar datos preparados al volumen MySQL (--copy-back)
    Write-Host "  [5/6] Restaurando datos al volumen MySQL (--copy-back)..." -ForegroundColor Yellow
    Invoke-XBRestore -XBArgs @(
        '--copy-back',
        '--target-dir', "/work/$BackupFull",
        '--datadir', '/var/lib/mysql'
    ) -LogPath $logFile -MountDataVolume

    # 10. Ajustar permisos para usuario mysql (uid 999)
    Write-Host "  [6/6] Ajustando permisos de propiedad (chown 999:999)..." -ForegroundColor Yellow
    Set-RestoreOwnership

    # 11. Iniciar el contenedor aislado de MySQL y verificar salud
    Start-RestoreMySQLAndWait

    $stopwatch.Stop()
    $duration = $stopwatch.Elapsed.TotalSeconds

    # 12. Registrar en la bitacora oficial
    Add-RestoreRecord `
        -Ciclo $Ciclo `
        -Carga $Ronda `
        -Estrategia 'differential' `
        -BackupFull $BackupFull `
        -BackupDiff $BackupDiff `
        -DuracionSegundos $duration `
        -Resultado 'OK'

    # 13. Limpieza de area de trabajo temporal
    if (-not $SkipCleanup) {
        Remove-WorkingCopy
    }

    Write-Host "============================================================" -ForegroundColor Green
    Write-Host " RESTAURACION DIFERENCIAL COMPLETADA CON EXITO" -ForegroundColor Green
    Write-Host " Duracion total: $([math]::Round($duration, 2)) segundos ($($stopwatch.Elapsed.ToString('mm\:ss\.fff')))" -ForegroundColor Green
    Write-Host " Log generado:   $logFile" -ForegroundColor Green
    Write-Host " Para validar y verificar alertas de integridad, ejecute:" -ForegroundColor White
    Write-Host "   .\validar-restauracion.ps1 -Ciclo $Ciclo -Carga $Ronda" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host " ERROR EN RESTAURACION DIFERENCIAL: $_" -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Red
    if ($stopwatch -and $stopwatch.IsRunning) { $stopwatch.Stop() }
    Add-RestoreRecord `
        -Ciclo $Ciclo `
        -Carga $Ronda `
        -Estrategia 'differential' `
        -BackupFull $BackupFull `
        -BackupDiff $BackupDiff `
        -DuracionSegundos ($stopwatch.Elapsed.TotalSeconds) `
        -Resultado "ERROR: $_"
    exit 1
}
