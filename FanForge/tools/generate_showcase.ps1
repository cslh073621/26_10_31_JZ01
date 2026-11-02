$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$configs = Get-ChildItem -LiteralPath (Join-Path $root "configs") -Filter "*.json" |
    Sort-Object Name

Push-Location $root
try {
    foreach ($config in $configs) {
        $name = $config.BaseName
        python -m fanforge generate $config.FullName --out "examples/$name" --force
        if ($LASTEXITCODE -ne 0) {
            throw "FanForge failed for $name"
        }
    }
}
finally {
    Pop-Location
}
