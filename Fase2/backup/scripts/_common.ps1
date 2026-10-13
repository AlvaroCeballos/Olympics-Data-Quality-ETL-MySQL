$ErrorActionPreference = 'Stop'

$script:Phase2Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$script:ComposeFile = Join-Path $script:Phase2Root 'docker-compose.yml'
$script:EnvFile = Join-Path $script:Phase2Root '.env'
$script:CredentialsFile = Join-Path $script:Phase2Root 'backup\xtrabackup.cnf'
$script:EncryptionKeyFile = Join-Path $script:Phase2Root 'backup\backup-encryption.key'
$script:BackupRoot = Join-Path $script:Phase2Root 'backup\archivos'
$script:LogRoot = Join-Path $script:Phase2Root 'logs'

function Get-ComposePrefix {
    return @(
        'compose',
        '--project-directory', $script:Phase2Root,
        '--env-file', $script:EnvFile,
        '-f', $script:ComposeFile
    )
}

function Initialize-Fase2Backup {
    if (-not (Test-Path -LiteralPath $script:EnvFile -PathType Leaf)) {
        throw 'Falta Fase2/.env. Copia .env.example a .env y configura la clave local.'
    }
    if (-not (Test-Path -LiteralPath $script:CredentialsFile -PathType Leaf)) {
        throw 'Falta Fase2/backup/xtrabackup.cnf. Copia xtrabackup.cnf.example y configura la misma clave de .env.'
    }
    if (-not (Test-Path -LiteralPath $script:EncryptionKeyFile -PathType Leaf)) {
        throw 'Falta Fase2/backup/backup-encryption.key. Genera la clave con generate-backup-encryption-key.ps1.'
    }
    if ((Get-Item -LiteralPath $script:EncryptionKeyFile).Length -lt 32) {
        throw 'La clave de cifrado está vacía o es demasiado corta. No ejecutes el respaldo.'
    }

    New-Item -ItemType Directory -Force -Path $script:BackupRoot, $script:LogRoot | Out-Null

    $composeArgs = (Get-ComposePrefix) + @('config', '--quiet')
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & docker @composeArgs
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($exitCode -ne 0) {
        throw 'La configuración de Docker Compose no es válida o Docker no está disponible.'
    }
}

function Invoke-XtraBackup {
    param(
        [Parameter(Mandatory = $true)][string[]]$XtraBackupArguments,
        [Parameter(Mandatory = $true)][string]$LogPath
    )

    $composeArgs = (Get-ComposePrefix) + @('run', '--rm', 'xtrabackup') + $XtraBackupArguments
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & docker @composeArgs 2>&1 | Tee-Object -FilePath $LogPath -Append
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($exitCode -ne 0) {
        throw "XtraBackup terminó con código $exitCode. Revisa el log: $LogPath"
    }
}

function Get-BackupSizeBytes {
    param([Parameter(Mandatory = $true)][string]$Path)

    $measure = Get-ChildItem -LiteralPath $Path -Force -File -Recurse | Measure-Object -Property Length -Sum
    if ($null -eq $measure.Sum) {
        return [long]0
    }
    return [long]$measure.Sum
}

function Add-BackupManifestRecord {
    param(
        [Parameter(Mandatory = $true)][string]$Strategy,
        [Parameter(Mandatory = $true)][string]$BackupName,
        [string]$BaseName = '',
        [Parameter(Mandatory = $true)][long]$SizeBytes
    )

    $manifestPath = Join-Path $script:LogRoot 'backup_manifest.csv'
    $records = @()

    if (Test-Path -LiteralPath $manifestPath -PathType Leaf) {
        foreach ($record in (Import-Csv -LiteralPath $manifestPath)) {
            $properties = $record.PSObject.Properties.Name
            $compression = if ($properties -contains 'compresion') { $record.compresion } else { 'none (historico)' }
            $encryption = if ($properties -contains 'cifrado') { $record.cifrado } else { 'none (historico)' }
            $records += [pscustomobject]@{
                fecha_hora = $record.fecha_hora
                estrategia = $record.estrategia
                respaldo = $record.respaldo
                basado_en = $record.basado_en
                tamano_bytes = $record.tamano_bytes
                compresion = $compression
                cifrado = $encryption
                resultado = $record.resultado
            }
        }
    }

    $records += [pscustomobject]@{
        fecha_hora = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')
        estrategia = $Strategy
        respaldo = $BackupName
        basado_en = $BaseName
        tamano_bytes = $SizeBytes
        compresion = 'ZSTD'
        cifrado = 'AES256'
        resultado = 'OK'
    }

    $temporaryPath = "$manifestPath.tmp"
    $records | Export-Csv -LiteralPath $temporaryPath -NoTypeInformation -Encoding UTF8
    Move-Item -LiteralPath $temporaryPath -Destination $manifestPath -Force
}
