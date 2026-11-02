# install-hermes.ps1 — Instalador del bundle Hermes de 4Dsentinel-suite
# Uso: powershell -NoProfile -ExecutionPolicy Bypass -File install-hermes.ps1
#       o copiar/pegar en una terminal PowerShell

param(
    [string]$Target = "$env:USERPROFILE\AppData\Local\hermes\skills\productivity"
)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  4Dsentinel-suite — Instalador para Hermes" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$src = Split-Path -Parent $MyInvocation.MyCommand.Path
$skillSrc = Join-Path $src "skills"

if (-not (Test-Path $skillSrc)) {
    Write-Host "ERROR: No se encontró skills/ en $src" -ForegroundColor Red
    Write-Host "Ejecutá este script desde dist/hermes/" -ForegroundColor Red
    exit 1
}

# Contar skills
$skillDirs = Get-ChildItem -Path $skillSrc -Directory
$fluencyCount = ($skillDirs | Where-Object { $_.Name -like "fluency-*" }).Count
$sentinelCount = ($skillDirs | Where-Object { $_.Name -like "sentinel-*" }).Count
$total = $fluencyCount + $sentinelCount

Write-Host "Skills a instalar:" -ForegroundColor White
Write-Host "  fluency-4d: $fluencyCount skills" -ForegroundColor Green
Write-Host "  sentinel-agents: $sentinelCount skills" -ForegroundColor Green
Write-Host "  Total: $total skills" -ForegroundColor Green
Write-Host "  Destino: $Target" -ForegroundColor Gray
Write-Host ""

$confirm = Read-Host "¿Instalar? (s/N)"
if ($confirm -ne "s" -and $confirm -ne "S") {
    Write-Host "Cancelado." -ForegroundColor Yellow
    exit 0
}

# Crear directorio destino
New-Item -ItemType Directory -Force -Path $Target | Out-Null

$installed = 0
$skipped = 0
$failed = 0

foreach ($dir in $skillDirs) {
    $dstDir = Join-Path $Target $dir.Name
    try {
        # Si ya existe, preguntar (solo en modo interactivo)
        if (Test-Path $dstDir) {
            Write-Host "  ~ $($dir.Name) (pisa existente)" -ForegroundColor Yellow
        } else {
            Write-Host "  + $($dir.Name)" -ForegroundColor Green
        }
        Copy-Item -Recurse -Force -Path $dir.FullName -Destination $dstDir
        $installed++
    } catch {
        Write-Host "  ✕ $($dir.Name): $_" -ForegroundColor Red
        $failed++
    }
}

# Copiar .hermes.md a la raíz del proyecto actual (si estamos en un repo)
$hermesMd = Join-Path $src ".hermes.md"
if (Test-Path $hermesMd) {
    $cwd = Get-Location
    $dstHermes = Join-Path $cwd ".hermes.md"
    if (-not (Test-Path $dstHermes)) {
        Copy-Item -Path $hermesMd -Destination $dstHermes
        Write-Host "  + .hermes.md → $cwd" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Instalados: $installed  |  Fallidos: $failed" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Skills disponibles en tu próxima sesión de Hermes." -ForegroundColor White
Write-Host "Probá: /4d, /sentinel-audit tipo=advisor, /handoff" -ForegroundColor Gray
