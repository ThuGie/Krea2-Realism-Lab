$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
. (Join-Path $project 'launcher-helpers.ps1')
function Assert-Equal($Actual, $Expected) {
    if ($Actual -ne $Expected) { throw "Expected [$Expected], got [$Actual]" }
}
$temporary = Join-Path ([System.IO.Path]::GetTempPath()) ('Krea2 Lab test (' + [guid]::NewGuid().ToString() + ')')
try {
    $root = Join-Path $temporary 'ComfyUI'
    $python = Join-Path $root '.venv\Scripts\python.exe'
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $python) | Out-Null
    [System.IO.File]::WriteAllText($python, '')
    [System.IO.File]::WriteAllText((Join-Path $root 'main.py'), '')
    Assert-Equal (Resolve-ComfyRoot $temporary) $root
    Assert-Equal (Resolve-ComfyRoot $root) $root
    Assert-Equal (Find-ComfyPython $root '') $python
    $target = Install-Krea2Lab $root $project
    [System.IO.File]::WriteAllText((Join-Path $target 'detector_config.json'), '{"keep":true}')
    Install-Krea2Lab $root $project | Out-Null
    Assert-Equal (Get-Content -LiteralPath (Join-Path $target 'detector_config.json') -Raw) '{"keep":true}'
    Assert-Equal (Test-Path -LiteralPath (Join-Path $target 'web\index.html')) $true
    Assert-Equal (Test-Path -LiteralPath (Join-Path $target 'web\web')) $false
    Assert-Equal (Quote-ProcessArgument 'C:\Test Folder\') '"C:\Test Folder\\"'
    Assert-Equal (Quote-ProcessArgument 'two "words"') '"two \"words\""'
    $arguments = @(Get-ComfyLaunchArguments $root $temporary 8199 -Cpu -Isolated)
    Assert-Equal ($arguments -contains '--cpu') $true
    Assert-Equal ($arguments -contains '--disable-all-custom-nodes') $true
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $project 'Start-Krea2-Lab.ps1') -ComfyPath $temporary -PrepareOnly
    Assert-Equal $LASTEXITCODE 0
    Write-Host 'PASS: installation selection, Python discovery, safe update, quoting and prepare-only launcher.'
} finally {
    $resolved = [System.IO.Path]::GetFullPath($temporary)
    $tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    if ($resolved.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase) -and (Split-Path -Leaf $resolved).StartsWith('Krea2 Lab test (')) {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
