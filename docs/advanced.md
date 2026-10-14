# Advanced setup and troubleshooting

[← Back to the README](../README.md)

## Performance

The tester reuses unchanged LoRA patches and the last prompt conditioning within each model's sweep. This avoids repeated LoRA loading and text encoding during sampler/scheduler comparisons. The cache is released when the model changes or the sweep ends; generation settings and sampler math are preserved.

ComfyUI handles GPU loading/offloading and uses its installed acceleration backends, including Comfy Kitchen where available. This project does not force global precision or attention changes. No specific speedup is guaranteed.

## Experimental AI detector — off by default

An optional CPU classifier can be enabled explicitly. **It is not a reliable judge of realistic humans** and may give obviously broken images high human-class scores. Scores and classifier sorting are hidden when disabled; human reviews determine the default ranking.

The optional model is [Ateeqq/ai-vs-human-image-detector](https://huggingface.co/Ateeqq/ai-vs-human-image-detector), pinned to revision `60e82406916921b823616bee33397baab38af3f0`. It requires approximately 354 MB of weights. Its author reports overfitting concerns; Krea2 realism performance has not been validated.

To install it, explicitly run the downloader with your ComfyUI Python:

```powershell
& "C:\AI\ComfyUI\.venv\Scripts\python.exe" .\setup_detector.py `
  --model-dir "C:\AI\Models\classifiers\krea2-ai-detector" `
  --plugin-dir "C:\AI\ComfyUI\custom_nodes\comfyui_krea2_lab"
```

This downloads only the required configuration, processor and safetensors files and verifies the weight checksum. Enable **Enable experimental AI detector** in the page afterward. Runtime scoring stays local and uses offline model loading. Model weights have their own upstream license.

## Advanced launch and manual installation

```powershell
# Choose a particular installation and Python environment.
.\Start-Krea2-Lab.ps1 -ComfyPath "C:\AI\ComfyUI" `
  -PythonPath "C:\AI\ComfyUI\.venv\Scripts\python.exe" -Port 8188

# Install without starting or stopping any backend.
.\Start-Krea2-Lab.ps1 -ComfyPath "C:\AI\ComfyUI" -PrepareOnly

# Install the extension and optional workflow files manually.
.\install.ps1 -ComfyPath "C:\AI\ComfyUI"
```

The BAT wrapper handles PowerShell execution policy for its own invocation. For manual PowerShell use on a machine that blocks scripts, invoke `powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File .\Start-Krea2-Lab.ps1` with your arguments.

Diagnostic flags: `-NoBrowser` skips opening a tab; `-Cpu` starts ComfyUI in CPU mode; `-Isolated` loads only this custom node and avoids reusing/restarting other backends. CPU mode is intended for startup checks, not practical Krea2 generation.

On other platforms, copy `comfyui_krea2_lab` into your ComfyUI `custom_nodes` directory, restart ComfyUI, and open `http://127.0.0.1:8188/krea2-lab`. The BAT launcher is Windows-only. Optional UI/API workflows are in `workflows/`.

## Troubleshooting

| Problem | What to check |
|---|---|
| No Krea2 files discovered | Verify model folders, naming and ComfyUI's shared-model configuration. |
| Python/dependencies missing | Finish the selected ComfyUI installation's setup; use `-PythonPath` for a custom environment. |
| Backend is busy | Pause the active sweep and wait for its current image before loading an update. |
| Startup fails or takes too long | Read `comfyui.stderr.log` and `comfyui.stdout.log` under `%LOCALAPPDATA%\Krea2RealismLab`. |
| A pair fails or produces broken output | Disable that sampler/scheduler pair; inspect `sweeps/*.errors.jsonl`. |
| LoRA has no effect | Zero matching model patches is an explicit failure. Partial matches may require inspecting ComfyUI logs. |
| Want to run an already completed configuration again | Use a new experiment name. |

## Development and validation

```powershell
python -m unittest discover -s tests -v
node tests/test_auto_page.cjs
node tests/test_help.cjs
powershell -NoProfile -ExecutionPolicy Bypass -File tests/test_launcher.ps1
```

The suite checks sweep coverage, selective modes, caching, resume, ETA, review persistence, incompatible-pair import/export, detector opt-in, option-help coverage, page rendering logic, installation selection and Windows argument quoting. Live PHP integration tests additionally check real SQLite vote persistence, vote updates, independent browser identities, CSRF rejection, admin authentication and result downloads. Export tests verify run scoping, path containment and private-review opt-in. PHP must be available for the live integration test; otherwise that test is skipped locally. GitHub Actions installs PHP with PDO_SQLITE so it runs there. GitHub Actions runs these tests on Windows. The launcher was also smoke-tested against a real ComfyUI installation in isolated CPU mode, including shared model discovery, backend reuse and shutdown. These checks do not validate every GPU/model/sampler combination or detector accuracy.

