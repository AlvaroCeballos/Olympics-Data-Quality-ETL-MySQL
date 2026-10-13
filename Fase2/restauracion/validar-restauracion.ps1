# ============================================================
# validar-restauracion.ps1
# Script de validacion de datos y alertas de integridad post-restauracion.
#
# Comprueba:
#   1. Censo de conteos (COUNT) de las 12 tablas vs valores esperados
#   2. Integridad referencial (deteccion de claves foraneas huerfanas)
#   3. Integridad fisica del motor InnoDB (CHECK TABLE)
#   4. Metricas de fragmentacion (information_schema.TABLES)
#
# Uso:
#   .\validar-restauracion.ps1 -Ciclo deportista -Carga c0
#   .\validar-restauracion.ps1 -Ciclo deportista -Carga c1
#   .\validar-restauracion.ps1 -Ciclo deporte    -Carga c3
#   .\validar-restauracion.ps1 -Ciclo anio       -Carga c2 -SaveReport
#
# Integrante 3 — Proyecto Fase 2, Grupo 18
# ============================================================

[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet('deportista', 'deporte', 'anio')]
    [string]$Ciclo,

    [Parameter(Position = 1, Mandatory = $true)]
    [ValidateSet('c0', 'c1', 'c2', 'c3')]
    [string]$Carga,

    [switch]$SaveReport
)

. (Join-Path $PSScriptRoot '_common_restore.ps1')

$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$reportLines = [System.Collections.Generic.List[string]]::new()

function Write-Both {
    param([string]$Text, [ConsoleColor]$Color = [ConsoleColor]::White)
    Write-Host $Text -ForegroundColor $Color
    $reportLines.Add($Text)
}

Write-Both "============================================================" [ConsoleColor]::Cyan
Write-Both " AUDITORIA DE VALIDACION Y ALERTAS DE INTEGRIDAD" [ConsoleColor]::Cyan
Write-Both " Fecha y Hora:  $timestamp" [ConsoleColor]::Cyan
Write-Both " Ciclo evaluado: $Ciclo" [ConsoleColor]::Cyan
Write-Both " Carga/Ronda:    $Carga" [ConsoleColor]::Cyan
Write-Both " Base objetivo:  olimpiadas (MySQL 8.0 / Puerto 3307)" [ConsoleColor]::Cyan
Write-Both "============================================================" [ConsoleColor]::Cyan

$totalAlerts = 0
$totalWarnings = 0

# ------------------------------------------------------------
# 1. CENSO DE CONTEOS (COUNT(*) en 12 tablas)
# ------------------------------------------------------------
Write-Both ""
Write-Both "--- [1/4] CENSO DE CONTEOS VS DATOS ESPERADOS ---" [ConsoleColor]::Yellow

# Construir diccionario de valores esperados para este ciclo y carga
$expectedCounts = @{}
foreach ($cat in $script:ExpectedCatalogs.Keys) {
    $expectedCounts[$cat] = $script:ExpectedCatalogs[$cat]
}
$expectedFactsForLoad = $script:ExpectedFacts[$Ciclo][$Carga]
$expectedCounts['atleta']        = $expectedFactsForLoad.atleta
$expectedCounts['participacion'] = $expectedFactsForLoad.participacion

$queryCenso = @"
SELECT 'pais' AS tabla, COUNT(*) AS total FROM pais
UNION ALL SELECT 'noc', COUNT(*) FROM noc
UNION ALL SELECT 'sede', COUNT(*) FROM sede
UNION ALL SELECT 'olimpiada', COUNT(*) FROM olimpiada
UNION ALL SELECT 'atleta', COUNT(*) FROM atleta
UNION ALL SELECT 'deporte', COUNT(*) FROM deporte
UNION ALL SELECT 'disciplina', COUNT(*) FROM disciplina
UNION ALL SELECT 'evento', COUNT(*) FROM evento
UNION ALL SELECT 'equipo', COUNT(*) FROM equipo
UNION ALL SELECT 'medalla', COUNT(*) FROM medalla
UNION ALL SELECT 'participacion', COUNT(*) FROM participacion
UNION ALL SELECT 'poblacion_pais', COUNT(*) FROM poblacion_pais;
"@

try {
    $censoRaw = Invoke-RestoreSQL -Query $queryCenso
    $actualCounts = @{}
    foreach ($line in $censoRaw) {
        $parts = $line -split '\t'
        if ($parts.Count -ge 2 -and $parts[0] -ne 'tabla') {
            $tName = $parts[0].Trim()
            $tVal  = [long]$parts[1].Trim()
            $actualCounts[$tName] = $tVal
        }
    }

    Write-Both ("{0,-16} | {1,10} | {2,10} | {3,-12}" -f "TABLA", "ESPERADO", "ACTUAL", "ESTADO") [ConsoleColor]::White
    Write-Both ("-" * 56) [ConsoleColor]::Gray

    $tableOrder = @('pais', 'noc', 'sede', 'olimpiada', 'atleta', 'deporte', 'disciplina', 'evento', 'equipo', 'medalla', 'participacion', 'poblacion_pais')
    foreach ($tbl in $tableOrder) {
        $exp = $expectedCounts[$tbl]
        $act = if ($actualCounts.ContainsKey($tbl)) { $actualCounts[$tbl] } else { -1 }

        if ($act -eq $exp) {
            Write-Both ("{0,-16} | {1,10} | {2,10} | {3,-12}" -f $tbl, $exp, $act, "[OK COINCIDE]") [ConsoleColor]::Green
        } else {
            $totalAlerts++
            Write-Both ("{0,-16} | {1,10} | {2,10} | {3,-12}" -f $tbl, $exp, $act, "[ALERTA DISCREPANCIA]") [ConsoleColor]::Red
        }
    }
}
catch {
    $totalAlerts++
    Write-Both " [ALERTA CRITICA] Error al consultar censo en MySQL: $_" [ConsoleColor]::Red
}

# ------------------------------------------------------------
# 2. INTEGRIDAD REFERENCIAL (Claves foraneas huerfanas)
# ------------------------------------------------------------
Write-Both ""
Write-Both "--- [2/4] AUDITORIA DE INTEGRIDAD REFERENCIAL (HUERFANOS) ---" [ConsoleColor]::Yellow

$fkChecks = @(
    @{
        Relacion = "participacion -> atleta"
        Query = "SELECT COUNT(*) FROM participacion p LEFT JOIN atleta a ON p.id_atleta = a.id_atleta WHERE a.id_atleta IS NULL;"
    },
    @{
        Relacion = "participacion -> evento"
        Query = "SELECT COUNT(*) FROM participacion p LEFT JOIN evento e ON p.id_evento = e.id_evento WHERE e.id_evento IS NULL;"
    },
    @{
        Relacion = "participacion -> olimpiada"
        Query = "SELECT COUNT(*) FROM participacion p LEFT JOIN olimpiada o ON p.id_olimpiada = o.id_olimpiada WHERE o.id_olimpiada IS NULL;"
    },
    @{
        Relacion = "participacion -> equipo"
        Query = "SELECT COUNT(*) FROM participacion p LEFT JOIN equipo eq ON p.id_equipo = eq.id_equipo WHERE eq.id_equipo IS NULL;"
    },
    @{
        Relacion = "participacion -> medalla"
        Query = "SELECT COUNT(*) FROM participacion p LEFT JOIN medalla m ON p.id_medalla = m.id_medalla WHERE m.id_medalla IS NULL;"
    },
    @{
        Relacion = "evento -> disciplina"
        Query = "SELECT COUNT(*) FROM evento ev LEFT JOIN disciplina d ON ev.id_disciplina = d.id_disciplina WHERE d.id_disciplina IS NULL;"
    },
    @{
        Relacion = "disciplina -> deporte"
        Query = "SELECT COUNT(*) FROM disciplina d LEFT JOIN deporte dep ON d.id_deporte = dep.id_deporte WHERE dep.id_deporte IS NULL;"
    }
)

foreach ($check in $fkChecks) {
    try {
        $res = Invoke-RestoreSQL -Query $check.Query
        $orphanCount = [long]($res | Select-Object -Last 1).Trim()
        if ($orphanCount -eq 0) {
            Write-Both ("  [OK INTEGRIDAD] {0,-32} : 0 huerfanos detectados" -f $check.Relacion) [ConsoleColor]::Green
        } else {
            $totalAlerts++
            Write-Both ("  [ALERTA DE INTEGRIDAD] {0,-32} : {1} REGISTROS HUERFANOS DETECTADOS!" -f $check.Relacion, $orphanCount) [ConsoleColor]::Red
        }
    }
    catch {
        $totalAlerts++
        Write-Both ("  [ALERTA DE ERROR] Fallo al verificar {0}: $_" -f $check.Relacion) [ConsoleColor]::Red
    }
}

# ------------------------------------------------------------
# 3. INTEGRIDAD FISICA DE TABLAS (CHECK TABLE)
# ------------------------------------------------------------
Write-Both ""
Write-Both "--- [3/4] INTEGRIDAD FISICA DE TABLAS (CHECK TABLE) ---" [ConsoleColor]::Yellow

$queryCheck = "CHECK TABLE pais, noc, sede, olimpiada, atleta, deporte, disciplina, evento, equipo, medalla, participacion, poblacion_pais;"
try {
    $checkRaw = Invoke-RestoreSQL -Query $queryCheck
    $allTablesPhysicalOk = $true
    foreach ($line in $checkRaw) {
        if ($line -match 'Table\s+Op\s+Msg_type\s+Msg_text') { continue }
        $cols = $line -split '\t'
        if ($cols.Count -ge 4) {
            $tName = $cols[0].Replace('olimpiadas.', '')
            $mType = $cols[2]
            $mText = $cols[3]
            if ($mType -eq 'status' -and $mText -eq 'OK') {
                Write-Both ("  [OK FISICO] {0,-16} : Estado {1}" -f $tName, $mText) [ConsoleColor]::Green
            } else {
                $totalAlerts++
                $allTablesPhysicalOk = $false
                Write-Both ("  [ALERTA FISICA] {0,-16} : {1} - {2}" -f $tName, $mType, $mText) [ConsoleColor]::Red
            }
        }
    }
}
catch {
    $totalAlerts++
    Write-Both " [ALERTA] Error al ejecutar CHECK TABLE: $_" [ConsoleColor]::Red
}

# ------------------------------------------------------------
# 4. METRICAS DE FRAGMENTACION (InnoDB TABLES)
# ------------------------------------------------------------
Write-Both ""
Write-Both "--- [4/4] METRICAS DE FRAGMENTACION (information_schema) ---" [ConsoleColor]::Yellow

$queryFrag = @"
SELECT
    TABLE_NAME AS tabla,
    TABLE_ROWS AS filas,
    ROUND(DATA_LENGTH / 1024, 2) AS datos_kb,
    ROUND(INDEX_LENGTH / 1024, 2) AS indices_kb,
    ROUND(DATA_FREE / 1024, 2) AS espacio_libre_kb,
    CASE WHEN (DATA_LENGTH + INDEX_LENGTH) > 0
         THEN ROUND(DATA_FREE / (DATA_LENGTH + INDEX_LENGTH) * 100, 2)
         ELSE 0 END AS pct_fragmentacion
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'olimpiadas'
ORDER BY pct_fragmentacion DESC, tabla;
"@

try {
    # Refrescar estadisticas de InnoDB
    $null = Invoke-RestoreSQL -Query "ANALYZE TABLE pais, noc, sede, olimpiada, atleta, deporte, disciplina, evento, equipo, medalla, participacion, poblacion_pais;" 2>$null
    $fragRaw = Invoke-RestoreSQL -Query $queryFrag
    Write-Both ("{0,-16} | {1,8} | {2,10} | {3,10} | {4,12} | {5,10}" -f "TABLA", "FILAS", "DATOS_KB", "INDICE_KB", "LIBRE_KB", "%_FRAG") [ConsoleColor]::White
    Write-Both ("-" * 78) [ConsoleColor]::Gray
    foreach ($line in $fragRaw) {
        if ($line -match 'tabla\s+filas') { continue }
        $cols = $line -split '\t'
        if ($cols.Count -ge 6) {
            Write-Both ("{0,-16} | {1,8} | {2,10} | {3,10} | {4,12} | {5,10}%" -f $cols[0], $cols[1], $cols[2], $cols[3], $cols[4], $cols[5]) [ConsoleColor]::Cyan
        }
    }
}
catch {
    Write-Both "  [AVISO] No se pudo obtener la fragmentacion: $_" [ConsoleColor]::Yellow
}

# ------------------------------------------------------------
# 5. RESUMEN Y ALERTA FINAL
# ------------------------------------------------------------
Write-Both ""
Write-Both "============================================================" [ConsoleColor]::White
if ($totalAlerts -eq 0) {
    Write-Both " [VEREDICTO GLOBAL]: RESTAURACION 100% VALIDA E INTEGRA" [ConsoleColor]::Green
    Write-Both "  -> Conteos: Coinciden exactamente con la carga esperada." [ConsoleColor]::Green
    Write-Both "  -> Integridad Referencial: Cero registros huerfanos detectados." [ConsoleColor]::Green
    Write-Both "  -> Integridad Fisica: Tablas InnoDB consistentes y saludables." [ConsoleColor]::Green
    Write-Both "  -> Alertas detectadas: 0" [ConsoleColor]::Green
} else {
    Write-Both " [ALERTA CRITICA]: SE DETECTARON $totalAlerts DISCREPANCIAS O FALLAS" [ConsoleColor]::Red
    Write-Both "  -> Revise los bloques marcados con [ALERTA] para depuracion." [ConsoleColor]::Red
}
Write-Both "============================================================" [ConsoleColor]::White

if ($SaveReport) {
    $reportFileName = "validacion_${Ciclo}_${Carga}_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
    $reportFilePath = Join-Path $script:LogRoot $reportFileName
    $reportLines | Out-File -LiteralPath $reportFilePath -Encoding utf8
    Write-Host " Reporte de auditoria guardado en: $reportFilePath" -ForegroundColor Cyan
}

if ($totalAlerts -gt 0) {
    exit 1
} else {
    exit 0
}
