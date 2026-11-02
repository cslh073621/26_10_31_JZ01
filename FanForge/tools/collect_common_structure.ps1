param(
    [string]$Root = (Split-Path $PSScriptRoot -Parent)
)

$ErrorActionPreference = 'Stop'
$sourceList = Join-Path $Root 'evidence\source_projects.txt'
$orderOutput = Join-Path $Root 'evidence\source_function_order.csv'
$frequencyOutput = Join-Path $Root 'evidence\common_function_frequency.csv'

$definitionPattern = '(?m)^\s*(?:void\s+interrupt|void|u8|u16|unsigned char|unsigned int|bit)\s+([A-Za-z_]\w*)\s*\([^;\r\n]*\)\s*\{'
$frequency = @{}
$orders = @()

Get-Content -LiteralPath $sourceList -Encoding UTF8 |
    Where-Object { $_ -and -not $_.StartsWith('#') } |
    ForEach-Object {
        $path = $_
        if(-not (Test-Path -LiteralPath $path))
        {
            throw "Missing source: $path"
        }

        $text = [System.IO.File]::ReadAllText($path)
        $matches = [regex]::Matches($text, $definitionPattern)
        $names = @($matches | ForEach-Object { $_.Groups[1].Value })

        if($names.Count -lt 8)
        {
            throw "Unreadable or encrypted source: $path"
        }

        $orders += [pscustomobject]@{
            Path = $path
            FunctionCount = $names.Count
            FunctionOrder = ($names -join ' -> ')
        }

        $names | Select-Object -Unique | ForEach-Object {
            if(-not $frequency.ContainsKey($_))
            {
                $frequency[$_] = 0
            }
            $frequency[$_]++
        }
    }

$orders | Export-Csv -LiteralPath $orderOutput -NoTypeInformation -Encoding UTF8

$sourceCount = $orders.Count
$frequency.GetEnumerator() |
    Sort-Object @{ Expression = 'Value'; Descending = $true }, @{ Expression = 'Name'; Descending = $false } |
    ForEach-Object {
        [pscustomobject]@{
            Function = $_.Name
            Count = $_.Value
            SourceCount = $sourceCount
            Percent = [math]::Round($_.Value * 100 / $sourceCount, 1)
        }
    } |
    Export-Csv -LiteralPath $frequencyOutput -NoTypeInformation -Encoding UTF8

Write-Output "Analyzed $sourceCount readable sources."
Write-Output $orderOutput
Write-Output $frequencyOutput
