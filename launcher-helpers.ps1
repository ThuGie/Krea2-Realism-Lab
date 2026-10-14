function Resolve-ComfyRoot([string]$Path) {
    $resolved = (Resolve-Path -LiteralPath $Path -ErrorAction Stop).Path
    if (Test-Path -LiteralPath (Join-Path $resolved 'main.py')) { return $resolved }
    $nested = Join-Path $resolved 'ComfyUI'
    if (Test-Path -LiteralPath (Join-Path $nested 'main.py')) { return $nested }
    throw 'Select the ComfyUI folder containing main.py, or its installation/portable parent.'
}

function Find-ComfyPython([string]$Root, [string]$ExplicitPath) {
    if ($ExplicitPath) {
        if (!(Test-Path -LiteralPath $ExplicitPath -PathType Leaf)) { throw 'The selected python.exe does not exist.' }
        return (Resolve-Path -LiteralPath $ExplicitPath).Path
    }
    $parent = Split-Path -Parent $Root
    foreach ($candidate in @(
        (Join-Path $Root '.venv\Scripts\python.exe'),
        (Join-Path $Root 'venv\Scripts\python.exe'),
        (Join-Path $parent '.venv\Scripts\python.exe'),
        (Join-Path $parent 'python_embeded\python.exe'),
        (Join-Path $parent 'python_embedded\python.exe'),
        (Join-Path $parent 'standalone-env\python.exe')
    )) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    throw 'Python was not found. Run the launcher with -PythonPath pointing to this ComfyUI installation''s python.exe.'
}

function Install-Krea2Lab([string]$Root, [string]$Source) {
    $target = Join-Path $Root 'custom_nodes\comfyui_krea2_lab'
    New-Item -ItemType Directory -Force -Path $target | Out-Null
    foreach ($name in @('__init__.py', 'detector_worker.py')) {
        Copy-Item -LiteralPath (Join-Path $Source "comfyui_krea2_lab\$name") -Destination $target -Force
    }
    # Detector configuration belongs to the chosen installation, not this checkout.
    Copy-Item -LiteralPath (Join-Path $Source 'comfyui_krea2_lab\web') -Destination $target -Recurse -Force
    return $target
}

function Get-ComfyLaunchArguments([string]$Root, [string]$StateDirectory, [int]$Port, [switch]$Cpu, [switch]$Isolated) {
    $arguments = @('-s', (Join-Path $Root 'main.py'), '--listen', '127.0.0.1', '--port', "$Port", '--disable-auto-launch')
    $instance = Split-Path -Parent $Root
    $desktop = Split-Path -Parent (Split-Path -Parent $instance)
    $shared = Join-Path $desktop 'ComfyUI-Shared'
    if ((Test-Path -LiteralPath (Join-Path $instance 'manifest.json')) -and (Test-Path -LiteralPath (Join-Path $shared 'models'))) {
        $modelDirectory = (Join-Path $shared 'models').Replace("'", "''")
        $configPath = Join-Path $StateDirectory 'shared-models.yaml'
        $lines = @('krea2_lab_shared:', "  base_path: '$modelDirectory'", '  is_default: true')
        foreach ($category in @('checkpoints','diffusion_models','loras','text_encoders','vae','classifiers')) {
            $lines += "  ${category}: ${category}/"
        }
        [System.IO.File]::WriteAllLines($configPath, $lines, [System.Text.UTF8Encoding]::new($false))
        $arguments += @('--extra-model-paths-config', $configPath,
            '--input-directory', (Join-Path $shared 'input'), '--output-directory', (Join-Path $shared 'output'))
    }
    if ($Cpu) { $arguments += '--cpu' }
    if ($Isolated) { $arguments += @('--disable-all-custom-nodes', '--whitelist-custom-nodes', 'comfyui_krea2_lab') }
    return $arguments
}

function Quote-ProcessArgument([string]$Value) {
    $result = '"'
    $slashes = 0
    foreach ($character in $Value.ToCharArray()) {
        if ($character -eq '\') { $slashes++; continue }
        if ($character -eq '"') {
            $result += ('\' * (2 * $slashes + 1)) + '"'
        } else {
            $result += ('\' * $slashes) + $character
        }
        $slashes = 0
    }
    return $result + ('\' * (2 * $slashes)) + '"'
}

function Get-LocalJson([string]$Url) {
    try { return Invoke-RestMethod -Uri $Url -TimeoutSec 2 -ErrorAction Stop }
    catch { return $null }
}

function Get-ComfyServers([string]$PythonPath) {
    $processes = @(Get-CimInstance Win32_Process -Filter "name='python.exe'" | Where-Object {
        $_.CommandLine -and ($_.ExecutablePath -eq $PythonPath -or $_.CommandLine.Contains($PythonPath)) -and $_.CommandLine -match '(?:main\.py)' -and $_.CommandLine -notmatch 'detector_worker\.py'
    })
    if (!$processes.Count) { return @() }
    $ids = @($processes.ProcessId)
    return @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object {
        $_.OwningProcess -in $ids -and $_.LocalAddress -in @('127.0.0.1','0.0.0.0','::','::1')
    } | Sort-Object LocalPort -Unique)
}

function Stop-OwnedComfy([int]$ProcessId, [string]$PythonPath, [string]$Root, [int]$Port) {
    $owned = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId"
    $main = Join-Path $Root 'main.py'
    $portPattern = '--port"?\s+"?' + $Port + '(?:"|\s|$)'
    if (!$owned -or !$owned.CommandLine -or !$owned.CommandLine.Contains($main) -or
        !($owned.ExecutablePath -eq $PythonPath -or $owned.CommandLine.Contains($PythonPath)) -or
        $owned.CommandLine -notmatch $portPattern) { return $false }
    $children = @(Get-CimInstance Win32_Process | Where-Object {
        $_.ParentProcessId -eq $ProcessId -and $_.CommandLine -and $_.CommandLine.Contains($main)
    })
    foreach ($child in $children) { Stop-Process -Id $child.ProcessId -ErrorAction SilentlyContinue }
    Stop-Process -Id $ProcessId -ErrorAction SilentlyContinue
    return $true
}
