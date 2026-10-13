$ErrorActionPreference = 'Stop'

$keyPath = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\backup-encryption.key'))
if (Test-Path -LiteralPath $keyPath) {
    throw "Ya existe la clave de cifrado: $keyPath. No se reemplazó para conservar la capacidad de restaurar backups existentes."
}

$randomBytes = New-Object byte[] 32
$randomGenerator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try {
    $randomGenerator.GetBytes($randomBytes)
    $key = ([BitConverter]::ToString($randomBytes)).Replace('-', '')
    [System.IO.File]::WriteAllText($keyPath, $key, [System.Text.Encoding]::ASCII)
}
finally {
    $randomGenerator.Dispose()
    [Array]::Clear($randomBytes, 0, $randomBytes.Length)
}

Write-Host "Clave AES-256 generada en: $keyPath"
Write-Host 'No la subas a Git ni la pierdas: Int3 la necesita para descifrar los backups.'
