param(
    [string]$Root = (Split-Path $PSScriptRoot -Parent)
)

$ErrorActionPreference = 'Stop'
$manifestPath = Join-Path $Root 'core\hs2811_core_manifest.yaml'
$templatePath = Join-Path $Root 'core\hs2811_fan_core.c.in'
$sourceListPath = Join-Path $Root 'evidence\source_projects.txt'

$manifest = [System.IO.File]::ReadAllText($manifestPath)
$template = [System.IO.File]::ReadAllText($templatePath)

$expectedFunctions = @()
$inFunctionOrder = $false
foreach($line in [System.IO.File]::ReadAllLines($manifestPath))
{
    if($line -eq 'function_order:')
    {
        $inFunctionOrder = $true
        continue
    }

    if($inFunctionOrder)
    {
        if($line -match '^\s{2}-\s+([A-Za-z_]\w*)\s*$')
        {
            $expectedFunctions += $Matches[1]
            continue
        }

        if($line -match '^\S')
        {
            break
        }
    }
}
if($expectedFunctions.Count -eq 0)
{
    throw 'Cannot parse function_order from core manifest.'
}

$definitionPattern = '(?m)^\s*(?:void\s+interrupt|void|u8|u16)\s+([A-Za-z_]\w*)\s*\([^;\r\n]*\)\s*\{'
$actualFunctions = @(
    [regex]::Matches($template, $definitionPattern) |
        ForEach-Object { $_.Groups[1].Value }
)

if(($actualFunctions -join '|') -ne ($expectedFunctions -join '|'))
{
    throw @"
Template function order differs from manifest.
Expected: $($expectedFunctions -join ' -> ')
Actual:   $($actualFunctions -join ' -> ')
"@
}

$invalidPlaceholder = [regex]::Match($template, '@@(?![A-Z][A-Z0-9_]*@@).*?@@')
if($invalidPlaceholder.Success)
{
    throw "Invalid placeholder syntax: $($invalidPlaceholder.Value)"
}

$requiredRules = @(
    'deterministic: true',
    'template_selection_exposed: false',
    'flag_storage: native_bit',
    'require_native_bit_flags: true',
    'allow_free_form_function_generation: false',
    'allow_project_to_choose_template: false',
    'unsupported_combination_action: fail'
)
foreach($rule in $requiredRules)
{
    if(-not $manifest.Contains($rule))
    {
        throw "Missing deterministic rule: $rule"
    }
}

if($manifest -match '(?m)^\s*(baseline|template_choice|reference_project)\s*:')
{
    throw 'Manifest exposes a forbidden baseline or template-selection field.'
}

if($template -match '\bbit_flag\b|\.bits\.bit[0-7]\b')
{
    throw 'HS2811 core must use native bit flags, not simulated bit storage.'
}

if($template -match '\bKEY_Init\s*\(')
{
    throw 'HS2811 core must name the common port initializer GPIO_Init.'
}

if($template -notmatch '(?m)^\s*void\s+GPIO_Init\s*\(void\)\s*\{')
{
    throw 'Missing GPIO_Init function definition.'
}

$requiredTimeSlots = @(
    '@@TIME_FLAG_DECLARATIONS@@',
    '@@TIME_COUNTER_DECLARATIONS@@',
    '@@BASE_TIME_ISR_BODY@@',
    '@@TIME_FLAG_DERIVATION@@'
)
foreach($slot in $requiredTimeSlots)
{
    if(-not $template.Contains($slot))
    {
        throw "Missing generated time-resource slot: $slot"
    }
}

if($template -match '(?m)^\s*(?:bit|u8|u16)\s+time_[A-Za-z0-9_]+_(?:flag|cnt)\s*;')
{
    throw 'Time flags and counters must be generated from module requests.'
}

Get-Content -LiteralPath $sourceListPath -Encoding UTF8 |
    Where-Object { $_ -and -not $_.StartsWith('#') } |
    ForEach-Object {
        if(-not (Test-Path -LiteralPath $_))
        {
            throw "Missing evidence source: $_"
        }
    }

Write-Output "Core validation passed."
Write-Output "Functions: $($actualFunctions.Count)"
Write-Output "Placeholders: $([regex]::Matches($template, '@@[A-Z][A-Z0-9_]*@@').Count)"
