. (Join-Path $PSScriptRoot '_common.ps1')

try {
    Initialize-Fase2Backup

    $baseBackup = Get-ChildItem -LiteralPath $script:BackupRoot -Directory |
        Where-Object {
            $_.Name -like 'full_*' -and
            (Test-Path -LiteralPath (Join-Path $_.FullName 'xtrabackup_checkpoints'))
        } |
        Sort-Object -Property LastWriteTime -Descending |
        Select-Object -First 1

    if ($null -eq $baseBackup) {
        throw 'No hay un respaldo full válido. Ejecuta primero backup-full.ps1.'
    }

    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $backupName = "diff_$timestamp"
    $hostTarget = Join-Path $script:BackupRoot $backupName
    $containerTarget = "/backups/$backupName"
    $containerBase = "/backups/$($baseBackup.Name)"
    $logPath = Join-Path $script:LogRoot "backup_$backupName.log"

    if (Test-Path -LiteralPath $hostTarget) {
        throw "Ya existe el directorio de respaldo: $hostTarget"
    }

    Write-Host "Iniciando diferencial $backupName basado en el full $($baseBackup.Name)"
    Invoke-XtraBackup -XtraBackupArguments @(
        '--backup',
        '--target-dir',
        $containerTarget,
        '--incremental-basedir',
        $containerBase
    ) -LogPath $logPath

    $sizeBytes = Get-BackupSizeBytes -Path $hostTarget
    Add-BackupManifestRecord -Strategy 'differential' -BackupName $backupName -BaseName $baseBackup.Name -SizeBytes $sizeBytes
    Write-Host "Diferencial terminado. Tamaño: $sizeBytes bytes. Log: $logPath"
}
catch {
    Write-Error $_
    exit 1
}
