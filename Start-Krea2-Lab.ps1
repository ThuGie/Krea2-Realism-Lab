param(
    [string]$ComfyPath,
    [string]$PythonPath,
    [ValidateRange(1024,65535)][int]$Port = 8188,
    [switch]$PrepareOnly,
    [switch]$NoBrowser,
    [switch]$Cpu,
    [switch]$Isolated,
    [switch]$Stop
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'launcher-helpers.ps1')

try {
    $stateDirectory = Join-Path $env:LOCALAPPDATA 'Krea2RealismLab'
    New-Item -ItemType Directory -Force -Path $stateDirectory | Out-Null
    $settingsPath = Join-Path $stateDirectory 'launcher.json'
    $saved = if (Test-Path -LiteralPath $settingsPath) { Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json } else { $null }
    if ($Stop) {
        if (!$saved -or !$saved.OwnedProcessId) { Write-Host 'No launcher-owned ComfyUI server to stop.'; exit 0 }
        if (Stop-OwnedComfy $saved.OwnedProcessId $saved.PythonPath $saved.ComfyPath $saved.Port) {
            Write-Host 'Stopped the ComfyUI server started by Krea2 Lab.'
        } else { Write-Host 'The saved server is no longer running. Nothing was stopped.' }
        exit 0
    }
    Write-Host "`nKrea2 Realism Lab - local launcher`n"
    if (!$ComfyPath) {
        if ($saved -and (Test-Path -LiteralPath $saved.ComfyPath)) {
            Write-Host "Last installation: $($saved.ComfyPath)"
            $choice = Read-Host 'Enter to use it, B to browse for another, or Q to quit'
            if ($choice -eq 'Q') { exit 0 }
            if ($choice -ne 'B') {
                $ComfyPath = $saved.ComfyPath
                if (!$PythonPath) { $PythonPath = $saved.PythonPath }
                if (!$PSBoundParameters.ContainsKey('Port')) { $Port = $saved.Port }
            }
        }
        if (!$ComfyPath) {
            Add-Type -AssemblyName System.Windows.Forms
            $picker = New-Object System.Windows.Forms.FolderBrowserDialog
            $picker.Description = 'Choose your ComfyUI installation (main.py folder or its parent)'
            $picker.ShowNewFolderButton = $false
            if ($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }
            $ComfyPath = $picker.SelectedPath
        }
    }
    $root = Resolve-ComfyRoot $ComfyPath
    $python = Find-ComfyPython $root $PythonPath
    $plugin = Install-Krea2Lab $root $PSScriptRoot
    $sourceHash = (Get-FileHash -LiteralPath (Join-Path $plugin '__init__.py') -Algorithm SHA256).Hash.ToLowerInvariant()
    $settings = [ordered]@{ ComfyPath=$root; PythonPath=$python; Port=$Port; OwnedProcessId=$null }
    if ($PrepareOnly) {
        Write-Host "Installed tester in $plugin. Prepare-only: no server started or stopped."
        exit 0
    }
    & $python -c 'import torch, aiohttp' 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'The selected Python is missing ComfyUI dependencies. Finish ComfyUI setup first, or select its correct Python with -PythonPath.' }

    $reuse = $false
    $servers = @()
    if (!$Isolated) { $servers = @(Get-ComfyServers $python) }
    $servers = @($servers | Sort-Object {
        $candidate = Get-LocalJson "http://127.0.0.1:$($_.LocalPort)/krea2-lab/installation"
        if ($candidate -and $candidate.comfy_root -eq $root -and $candidate.backend_hash -eq $sourceHash) { 0 } else { 1 }
    })
    foreach ($server in $servers) {
        $baseUrl = "http://127.0.0.1:$($server.LocalPort)"
        if (!(Get-LocalJson "$baseUrl/system_stats")) { continue }
        $info = Get-LocalJson "$baseUrl/krea2-lab/installation"
        if ($info -and $info.comfy_root -ne $root) { continue }
        if ($info -and $info.comfy_root -eq $root -and $info.backend_hash -eq $sourceHash) {
            $Port = $server.LocalPort
            $settings.Port = $Port
            $serverProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($server.OwningProcess)"
            if ($saved -and ($saved.OwnedProcessId -eq $server.OwningProcess -or $saved.OwnedProcessId -eq $serverProcess.ParentProcessId)) { $settings.OwnedProcessId = $saved.OwnedProcessId }
            $reuse = $true
            Write-Host 'Using the running ComfyUI backend.'
            break
        }
        $serverProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($server.OwningProcess)"
        if (!$info -and !$python.StartsWith($root.TrimEnd('\') + '\', [System.StringComparison]::OrdinalIgnoreCase) -and !$serverProcess.CommandLine.Contains((Join-Path $root 'main.py'))) {
            continue
        }
        $queue = Get-LocalJson "$baseUrl/queue"
        if (!$queue -or @($queue.queue_running).Count -gt 0 -or @($queue.queue_pending).Count -gt 0) {
            throw 'This installation has queued/running work. Pause the sweep and let the current trial finish, then run this launcher again to load the update.'
        }
        # The listener was matched to this installation's exact Python executable above.
        Write-Host 'Restarting the idle backend to load the installed tester.'
        Stop-Process -Id $server.OwningProcess -ErrorAction Stop
        Start-Sleep -Milliseconds 1000
    }
    if (!$reuse) {
        while (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
            $Port++
            if ($Port -gt 65535) { throw 'No free local port found.' }
        }
        $settings.Port = $Port
        $arguments = Get-ComfyLaunchArguments $root $stateDirectory $Port -Cpu:$Cpu -Isolated:$Isolated
        $stdout = Join-Path $stateDirectory 'comfyui.stdout.log'
        $stderr = Join-Path $stateDirectory 'comfyui.stderr.log'
        $argumentLine = ($arguments | ForEach-Object { Quote-ProcessArgument $_ }) -join ' '
        $process = Start-Process -FilePath $python -ArgumentList $argumentLine -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
        $settings.OwnedProcessId = $process.Id
        Write-Host "Starting ComfyUI on port $Port. Logs: $stateDirectory"
        $deadline = (Get-Date).AddMinutes(3)
        do {
            Start-Sleep -Milliseconds 750
            $info = Get-LocalJson "http://127.0.0.1:$Port/krea2-lab/installation"
            $process.Refresh()
            if ($process.HasExited) {
                if (Test-Path -LiteralPath $stderr) { Get-Content -LiteralPath $stderr -Tail 15 | Write-Host }
                throw "ComfyUI exited. See logs in $stateDirectory"
            }
        } until (($info -and $info.backend_hash -eq $sourceHash) -or (Get-Date) -gt $deadline)
        if (!$info -or $info.backend_hash -ne $sourceHash) {
            $settings | ConvertTo-Json | Set-Content -LiteralPath $settingsPath -Encoding UTF8
            throw "ComfyUI is taking longer than three minutes. Check $stderr; rerun the launcher once startup finishes. Stop-Krea2-Lab.bat can stop the owned backend."
        }
    }
    $settings | ConvertTo-Json | Set-Content -LiteralPath $settingsPath -Encoding UTF8
    $url = "http://127.0.0.1:$Port/krea2-lab"
    Write-Host "Ready: $url`nNo workflow required. Choose your tests in the webpage."
    if (!$NoBrowser) { Start-Process $url }
    exit 0
} catch {
    Write-Host "`n$($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
