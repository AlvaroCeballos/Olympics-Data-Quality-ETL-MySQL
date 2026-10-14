# ============================================================
# _common_restore.ps1
# Funciones compartidas para restauracion de respaldos XtraBackup
# en un entorno aislado (fase2_restore_mysql_data).
#
# Estrategia: DIFERENCIAL (Percona XtraBackup 8.0)
# Base de datos objetivo: olimpiadas (puerto 3307)
#
# Integrante 3 — Proyecto Fase 2, Grupo 18
# ============================================================

$ErrorActionPreference = 'Stop'

# ---- Rutas del proyecto ----
$script:Phase2Root         = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$script:MainComposeFile    = Join-Path $script:Phase2Root 'docker-compose.yml'
$script:RestoreComposeFile = Join-Path $PSScriptRoot 'docker-compose.restore.yml'
$script:EnvFile            = Join-Path $script:Phase2Root '.env'
$script:BackupRoot         = Join-Path $script:Phase2Root 'backup\archivos'
$script:LogRoot            = Join-Path $script:Phase2Root 'logs'
$script:WorkDir            = Join-Path $script:BackupRoot '_restore_work'

# ---- Volumenes e Imagenes Docker ----
# AISLAMIENTO: Usamos un volumen dedicado para restauracion (fase2_restore_mysql_data).
# El volumen del equipo (fase2_olimpiadas_mysql_data) permanece 100% intacto y protegido.
$script:RestoreVolumeName  = 'fase2_restore_mysql_data'
$script:MainVolumeName     = 'fase2_olimpiadas_mysql_data'
$script:RestoreContainer   = 'fase2_mysql_restore'
$script:XBImage            = 'percona/percona-xtrabackup:8.0'
$script:AlpineImage        = 'alpine:3.19'

# ---- Mapeo de Respaldos Definitivos (3 Ciclos × 1 Full + 3 Diferenciales) ----
$script:DefinitiveSets = @{
    'deportista' = @{
        'full' = 'full_20261012_211829'
        'c0'   = 'full_20261012_211829'
        'c1'   = 'diff_20261012_212322'
        'c2'   = 'diff_20261012_212404'
        'c3'   = 'diff_20261012_212457'
    }
    'deporte' = @{
        'full' = 'full_20261012_213152'
        'c0'   = 'full_20261012_213152'
        'c1'   = 'diff_20261012_213250'
        'c2'   = 'diff_20261012_213408'
        'c3'   = 'diff_20261012_213758'
    }
    'anio' = @{
        'full' = 'full_20261012_213911'
        'c0'   = 'full_20261012_213911'
        'c1'   = 'diff_20261012_214241'
        'c2'   = 'diff_20261012_214542'
        'c3'   = 'diff_20261012_214706'
    }
}

# ---- Valores esperados de censo para alertas de integridad ----
$script:ExpectedCatalogs = @{
    'pais'           = 487
    'noc'            = 236
    'sede'           = 45
    'olimpiada'      = 63
    'deporte'        = 148
    'disciplina'     = 149
    'evento'         = 3152
    'equipo'         = 20845
    'medalla'        = 4
    'poblacion_pais' = 16930
}

$script:ExpectedFacts = @{
    'deportista' = @{
        'c0' = @{ atleta = 0;     participacion = 0 }
        'c1' = @{ atleta = 1;     participacion = 1 }
        'c2' = @{ atleta = 1;     participacion = 4 }
        'c3' = @{ atleta = 1;     participacion = 7 }
    }
    'deporte' = @{
        'c0' = @{ atleta = 0;     participacion = 0 }
        'c1' = @{ atleta = 91;    participacion = 91 }
        'c2' = @{ atleta = 150;   participacion = 172 }
        'c3' = @{ atleta = 219;   participacion = 263 }
    }
    'anio' = @{
        'c0' = @{ atleta = 0;     participacion = 0 }
        'c1' = @{ atleta = 14464; participacion = 17015 }
        'c2' = @{ atleta = 24001; participacion = 33198 }
        'c3' = @{ atleta = 30648; participacion = 44581 }
    }
}

# ============================================================
# Validacion inicial
# ============================================================
function Initialize-Fase2Restore {
    if (-not (Test-Path -LiteralPath $script:EnvFile -PathType Leaf)) {
        throw 'Falta Fase2/.env. Copia .env.example a .env antes de continuar.'
    }
    New-Item -ItemType Directory -Force -Path $script:LogRoot | Out-Null
    New-Item -ItemType Directory -Force -Path $script:BackupRoot | Out-Null
}

# ============================================================
# Obtener contrasena root desde .env
# ============================================================
function Get-MySQLRootPassword {
    $envContent = Get-Content -LiteralPath $script:EnvFile
    foreach ($line in $envContent) {
        $trimmed = $line.Trim()
        if ($trimmed.StartsWith('MYSQL_ROOT_PASSWORD=')) {
            return $trimmed.Substring('MYSQL_ROOT_PASSWORD='.Length).Trim()
        }
    }
    return 'Cambiar_Esta_Clave_Local_2026'
}

# ============================================================
# Verificar existencia e integridad basica de un respaldo
# ============================================================
function Assert-BackupExists {
    param([Parameter(Mandatory)][string]$Name)

    $path = Join-Path $script:BackupRoot $Name
    if (-not (Test-Path -LiteralPath $path -PathType Container)) {
        throw "No existe el respaldo '$Name' en $($script:BackupRoot)"
    }
    $cp = Join-Path $path 'xtrabackup_checkpoints'
    if (-not (Test-Path -LiteralPath $cp -PathType Leaf)) {
        throw "El respaldo '$Name' no contiene xtrabackup_checkpoints valido."
    }
}

# ============================================================
# Crear copia de trabajo temporal (Protege respaldos originales)
# XtraBackup --prepare modifica archivos in-place.
# Trabajamos sobre _restore_work para mantener los originales intactos.
# ============================================================
function New-WorkingCopy {
    param([Parameter(Mandatory)][string[]]$BackupNames)

    if (Test-Path -LiteralPath $script:WorkDir) {
        Write-Host "  [1/6] Limpiando area de trabajo anterior (_restore_work)..." -ForegroundColor Gray
        Remove-Item -LiteralPath $script:WorkDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    New-Item -ItemType Directory -Force -Path $script:WorkDir | Out-Null

    foreach ($name in $BackupNames) {
        $src = Join-Path $script:BackupRoot $name
        $dst = Join-Path $script:WorkDir    $name
        Write-Host "  Copiando $name hacia area de trabajo segura..." -ForegroundColor Cyan
        Copy-Item -LiteralPath $src -Destination $dst -Recurse
    }

    # Normalizar finales de linea en archivos .index (eliminar \r introducido por Git en Windows)
    Get-ChildItem -LiteralPath $script:WorkDir -Recurse -Filter '*.index' | ForEach-Object {
        $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
        $newBytes = $bytes | Where-Object { $_ -ne 13 }
        [System.IO.File]::WriteAllBytes($_.FullName, [byte[]]$newBytes)
    }

    Write-Host "  Copia de trabajo lista en _restore_work." -ForegroundColor Green
}

# ============================================================
# Limpiar copia de trabajo temporal
# ============================================================
function Remove-WorkingCopy {
    if (Test-Path -LiteralPath $script:WorkDir) {
        Write-Host "  Limpiando directorio temporal de trabajo..." -ForegroundColor Gray
        Remove-Item -LiteralPath $script:WorkDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# ============================================================
# Detener contenedores existentes (sin borrar volumenes de los companeros)
# Libera el puerto 3307 para la instancia de restauracion.
# ============================================================
function Stop-AllFase2Containers {
    Write-Host "  Deteniendo contenedores activos para liberar puerto 3307..." -ForegroundColor Gray
    
    # 1. Detener restore compose si estuviera arriba
    $prev = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        docker compose --project-directory $script:Phase2Root --env-file $script:EnvFile -f $script:RestoreComposeFile down 2>&1 | Out-Null
    }
    finally { $ErrorActionPreference = $prev }

    # 2. Detener main compose si estuviera arriba (sin -v, protege su volumen)
    try {
        $ErrorActionPreference = 'Continue'
        docker compose --project-directory $script:Phase2Root --env-file $script:EnvFile -f $script:MainComposeFile down 2>&1 | Out-Null
    }
    finally { $ErrorActionPreference = $prev }
}

# ============================================================
# Vaciar exclusivamente el volumen aislado de restauracion
# NUNCA toca fase2_olimpiadas_mysql_data.
# ============================================================
function Clear-RestoreVolume {
    Write-Host "  Vaciando volumen aislado de restauracion ($($script:RestoreVolumeName))..." -ForegroundColor Gray
    $prev = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & docker run --rm --user 0:0 `
            -v "$($script:RestoreVolumeName):/data" `
            $script:AlpineImage `
            sh -c 'rm -rf /data/* && chmod 777 /data'
        $exitCode = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $prev }
    if ($exitCode -ne 0) {
        throw "Error al vaciar el volumen de restauracion (codigo $exitCode)."
    }
    Write-Host "  Volumen aislado vaciado y preparado." -ForegroundColor Green
}

# ============================================================
# Ejecutar comando de XtraBackup (prepare / copy-back)
# ============================================================
function Invoke-XBRestore {
    param(
        [Parameter(Mandatory)][string[]]$XBArgs,
        [Parameter(Mandatory)][string]$LogPath,
        [switch]$MountDataVolume
    )

    $volumes = @('-v', "$($script:WorkDir):/work")
    if ($MountDataVolume) {
        $volumes += @('-v', "$($script:RestoreVolumeName):/var/lib/mysql")
    }

    $dockerArgs = @('run', '--rm', '--user', '0:0') + $volumes + @($script:XBImage, 'xtrabackup') + $XBArgs

    $prev = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $quotedArgs = $dockerArgs | ForEach-Object { if ($_ -match '\s') { "`"$_`"" } else { $_ } }
        $fullCmd = "docker " + ($quotedArgs -join " ")
        cmd.exe /c "$fullCmd 2>&1" | Tee-Object -FilePath $LogPath -Append
        $exitCode = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $prev }

    if ($exitCode -ne 0) {
        throw "XtraBackup termino con codigo $exitCode. Revisa el log: $LogPath"
    }
}

# ============================================================
# Ajustar permisos del volumen restaurado (mysql = uid 999)
# ============================================================
function Set-RestoreOwnership {
    Write-Host "  Ajustando permisos del volumen restaurado (chown 999:999)..." -ForegroundColor Gray
    $prev = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & docker run --rm --user 0:0 `
            -v "$($script:RestoreVolumeName):/var/lib/mysql" `
            $script:AlpineImage `
            chown -R 999:999 /var/lib/mysql
        $exitCode = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $prev }
    if ($exitCode -ne 0) {
        throw "Error al ajustar permisos (codigo $exitCode)."
    }
}

# ============================================================
# Iniciar MySQL en el contenedor aislado y esperar healthcheck
# ============================================================
function Start-RestoreMySQLAndWait {
    param([int]$TimeoutSeconds = 120)

    Write-Host "  Iniciando MySQL aislado (fase2_mysql_restore)..." -ForegroundColor Cyan
    $prev = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & docker compose --project-directory $script:Phase2Root --env-file $script:EnvFile -f $script:RestoreComposeFile up -d
        $exitCode = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $prev }

    if ($exitCode -ne 0) {
        throw "Error al iniciar el contenedor de restauracion."
    }

    Write-Host "  Esperando healthcheck de MySQL..." -ForegroundColor Gray
    $elapsed = 0
    while ($elapsed -lt $TimeoutSeconds) {
        Start-Sleep -Seconds 2
        $elapsed += 2

        $psOut = (& docker inspect --format="{{.State.Health.Status}}" $script:RestoreContainer 2>&1) | Out-String
        if ($psOut.Trim() -eq 'healthy') {
            Write-Host "  MySQL restaurado y saludable en puerto 3307 (${elapsed}s)." -ForegroundColor Green
            return
        }
    }
    throw "MySQL restaurado no alcanzo estado healthy tras ${TimeoutSeconds}s."
}

# ============================================================
# Detener MySQL restaurado
# ============================================================
function Stop-RestoreMySQL {
    Write-Host "  Deteniendo contenedor de restauracion..." -ForegroundColor Gray
    $prev = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & docker compose --project-directory $script:Phase2Root --env-file $script:EnvFile -f $script:RestoreComposeFile down 2>&1 | Out-Null
    }
    finally { $ErrorActionPreference = $prev }
}

# ============================================================
# Registrar restauracion en la bitacora CSV
# ============================================================
function Add-RestoreRecord {
    param(
        [Parameter(Mandatory)][string]$Ciclo,
        [Parameter(Mandatory)][string]$Carga,
        [Parameter(Mandatory)][string]$Estrategia,
        [Parameter(Mandatory)][string]$BackupFull,
        [string]$BackupDiff = '',
        [Parameter(Mandatory)][double]$DuracionSegundos,
        [Parameter(Mandatory)][string]$Resultado
    )

    $csvPath = Join-Path $script:LogRoot 'bitacora_restauracion.csv'
    $record = [pscustomobject]@{
        fecha_hora         = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')
        ciclo              = $Ciclo
        carga              = $Carga
        estrategia         = $Estrategia
        backup_full        = $BackupFull
        backup_diff        = $BackupDiff
        duracion_segundos  = [math]::Round($DuracionSegundos, 2)
        resultado          = $Resultado
    }
    $record | Export-Csv -LiteralPath $csvPath -NoTypeInformation -Append -Encoding UTF8
    Write-Host "  Bitacora actualizada: $csvPath" -ForegroundColor Gray
}

# ============================================================
# Ejecutar consulta SQL contra la instancia restaurada
# ============================================================
function Invoke-RestoreSQL {
    param([Parameter(Mandatory)][string]$Query)

    $password = Get-MySQLRootPassword
    $cmd = @(
        'exec',
        '-i',
        $script:RestoreContainer,
        'mysql',
        '-uroot',
        "-p$password",
        'olimpiadas',
        '-e',
        $Query
    )

    $prev = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $output = & docker @cmd 2>&1
        $exitCode = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $prev }

    if ($exitCode -ne 0) {
        throw "Error al ejecutar SQL en el contenedor: $output"
    }
    return $output
}
