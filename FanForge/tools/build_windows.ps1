param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvDir = Join-Path $RepoRoot ".venv-build"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

Push-Location $RepoRoot
try {
    if (-not (Test-Path $VenvPython)) {
        $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
        if ($null -ne $PyLauncher) {
            & $PyLauncher.Source -3 -m venv $VenvDir
        }
        else {
            $Python = Get-Command python -ErrorAction Stop
            & $Python.Source -m venv $VenvDir
        }
    }

    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r requirements-build.txt

    if (-not $SkipTests) {
        & $VenvPython -m unittest discover -s tests -v
    }

    & $VenvPython -m PyInstaller --noconfirm --clean FanForgeGUI.spec

    $ExePath = Join-Path $RepoRoot "dist\FanForge.exe"
    if (-not (Test-Path $ExePath)) {
        throw "PyInstaller finished without creating $ExePath"
    }

    Write-Host ""
    Write-Host "FanForge Windows application created:" -ForegroundColor Green
    Write-Host $ExePath
}
finally {
    Pop-Location
}
