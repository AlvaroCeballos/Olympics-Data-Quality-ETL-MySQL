. (Join-Path $PSScriptRoot '_common.ps1')

try {
    Initialize-Fase2Backup

    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $backupName = "full_$timestamp"
    $hostTarget = Join-Path $script:BackupRoot $backupName
    $containerTarget = "/backups/$backupName"
    $logPath = Join-Path $script:LogRoot "backup_$backupName.log"

    if (Test-Path -LiteralPath $hostTarget) {
        throw "Ya existe el directorio de respaldo: $hostTarget"
    }

    Write-Host "Iniciando respaldo completo: $backupName"
    Invoke-XtraBackup -XtraBackupArguments @(
        '--defaults-extra-file=/etc/xtrabackup.cnf',
        '--backup',
        '--target-dir=' + $containerTarget
    ) -LogPath $logPath

    $sizeBytes = Get-BackupSizeBytes -Path $hostTarget
    Add-BackupManifestRecord -Strategy 'full' -BackupName $backupName -SizeBytes $sizeBytes
    Write-Host "Respaldo completo terminado. Tamaño: $sizeBytes bytes. Log: $logPath"
}
catch {
    Write-Error $_
    exit 1
}
