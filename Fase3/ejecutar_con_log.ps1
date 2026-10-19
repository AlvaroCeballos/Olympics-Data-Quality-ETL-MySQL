# ejecutar_con_log.ps1
param (
    [Parameter(Mandatory=$true)] [string]$Uri,
    [Parameter(Mandatory=$true)] [string]$ScriptJs
)

if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$basename = [System.IO.Path]::GetFileNameWithoutExtension($ScriptJs)
$logFile = "logs\${basename}_${timestamp}.log"

Write-Host "=================================================="
Write-Host "Ejecutando: $ScriptJs"
Write-Host "Log guardado en: $logFile"
Write-Host "=================================================="

mongosh $Uri --file $ScriptJs | Tee-Object -FilePath $logFile