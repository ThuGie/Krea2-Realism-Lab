param([Parameter(Mandatory=$true)][string]$ComfyPath)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'launcher-helpers.ps1')
$root = Resolve-ComfyRoot $ComfyPath
$target = Install-Krea2Lab $root $PSScriptRoot
$workflowTarget = Join-Path $root 'user\default\workflows'
New-Item -ItemType Directory -Force -Path $workflowTarget | Out-Null
foreach ($name in @('Krea2_Realism_Lab.json', 'Krea2_Realism_Lab.api.json')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot "workflows\$name") -Destination $workflowTarget -Force
}
Write-Output "Installed in $target. Use Start-Krea2-Lab.bat to open the webpage."
