# Krea2 Realism Lab

[![Tests](https://github.com/ThuGie/Krea2-Realism-Lab/actions/workflows/tests.yml/badge.svg)](https://github.com/ThuGie/Krea2-Realism-Lab/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Compare Krea2 models, LoRAs, strengths, samplers and schedulers from a local webpage.**

Double-click a BAT file, choose your ComfyUI installation, and start testing. **No workflow editing or manually placing a node is required.** The launcher installs a small ComfyUI extension and opens the experiment studio in your default browser.

## Quick start — Windows

1. [Download the latest release](https://github.com/ThuGie/Krea2-Realism-Lab/releases/latest) and extract the ZIP. Keep its files together.
2. Double-click **`Start-Krea2-Lab.bat`**.
3. Choose your ComfyUI installation folder. You can select the folder containing `main.py`, or its installation/portable parent.
4. The launcher installs the tester, starts ComfyUI or reuses a compatible running backend, and opens the review page.
5. Choose **Test mode**, check the combination count, and click **Start selected tests**.

Your installation choice is remembered. Next time, press Enter to reuse it or B to browse for another installation.

**Already running ComfyUI?** A compatible backend is reused. An idle backend can be restarted to load the extension/update. If there is queued or running work, the launcher refuses to restart it: pause the sweep, let the current trial finish, then launch again. Results and checkpoints stay saved.

**To stop a backend started by the launcher:** double-click `Stop-Krea2-Lab.bat`. This stops that backend, including a running generation. It does not stop an independently launched server that was merely reused.

## Requirements

- Windows 10/11 with Windows PowerShell 5.1 or newer.
- An existing, working ComfyUI installation with Krea2 support and its Python dependencies installed.
- Your own Krea2 diffusion models, LoRAs, compatible text encoder and VAE.
- A GPU suitable for running your chosen Krea2 model. This project does not reduce the model's basic VRAM requirements.

The launcher detects common `.venv`, `venv`, Windows portable `python_embeded`, and Comfy Desktop layouts. For Desktop installations with a neighboring `ComfyUI-Shared` directory, it connects shared models, input and output automatically. Other installations retain their normal ComfyUI model configuration.

No separate Python or Node.js installation is needed to **use** the launcher. No models, custom samplers, or acceleration packages are downloaded automatically.

## Choose what to test

| Mode | Changes between trials | Stays fixed |
|---|---|---|
| Everything | All discovered models, LoRAs, strengths, samplers and schedulers | Image size, steps and CFG unless their grids are enabled |
| LoRAs + strengths only | Every Krea2 LoRA at each strength | Selected model, sampler and scheduler |
| Strengths of one LoRA | Strength grid | Selected LoRA, model, sampler and scheduler |
| Samplers only | Every registered sampler | Selected model, LoRA/strength and scheduler |
| Schedulers only | Every registered scheduler | Selected model, LoRA/strength and sampler |
| Samplers + schedulers | Every sampler/scheduler pair | Selected model and LoRA/strength |
| Models only | Every discovered Krea2 model | Selected LoRA/strength, sampler and scheduler |
| Custom combination | The dimensions you check | Your fixed values for unchecked dimensions |

Step-count and CFG grids, multiple prompts, multiple seeds, no-LoRA baselines and per-LoRA trigger words are also available. **Everything is the initial default**; the image count can grow very large. Use a smaller mode when you only need to compare one dimension.

Discovery uses filenames/folders containing `krea`. Put files under `models/diffusion_models/krea2/` and `models/loras/krea2/` so Krea2 files with unrelated filenames are included. The page uses sampler/scheduler lists registered by your installation, including custom nodes.

Each selected combination runs once per prompt/seed. This tests individual LoRAs, not stacked LoRA combinations. Strengths are a finite grid, not every possible real number.

## Review and compare

- Full-resolution previews and complete generation settings.
- Human realism ratings from 1 to 5, with saved notes.
- Blind review that hides configuration labels.
- Workspace with separate setup and run controls, experiment and unreviewed filters, adjustable image size, 48-image pagination, and two-image comparison that respects blind review. Unsaved review notes survive automatic refreshes within the page session.
- Filterable gallery and a collapsed, scrollable configuration leaderboard. Sort fastest or slowest by recorded generation time; configurations use mean time, and missing timings appear last. Exported voting galleries also support whole-run speed sorting. Timing depends on hardware, warm-up, caching, image dimensions and batch size.
- JSON/CSV result exports.
- Per-run standalone PHP voting-site exports with images, SQLite, community ratings, leaderboards and administration.
- Accessible **?** buttons explaining every option and review/export control.
- Live progress and an estimated remaining duration/finish time after three successful generations.

ETA uses recent successful generation durations. It excludes future disabled pairs and fast failures, but remains approximate because model and sampler runtimes vary. Finish times are currently displayed in Europe/Amsterdam time.

### Incompatible sampler/scheduler pairs

Disable a pair from a result card or **Live sampler / scheduler controls**. The current image finishes normally; upcoming matches are skipped across models, LoRAs and strengths.

Disabled pairs move to their own section. Their results disappear from the active gallery and leaderboard, but images and reviews remain saved. Re-enabling restores those results and allows future trials; it does not rewind combinations already skipped.

Use **Export incompatible pairs** to save a portable JSON list. Import can **merge** with existing exclusions or **replace** them. Imports are validated before saving and duplicates are removed. Unknown names are retained for portability and marked as not currently installed.

```json
{
  "format": "krea2-lab-incompatible-pairs",
  "version": 1,
  "disabled": [["euler", "karras"]]
}
```

## Export a complete community voting website

Open **Export a standalone voting website**, select a saved run, and click **Build voting website ZIP**. Each export contains:

```text
public/
  index.html, app.js, style.css     Voting gallery and community leaderboards
  api.php                          PHP API for votes, sessions and administration
  admin.html, admin.js              Admin login and CSV/JSON downloads
  images/                          Copies of this run's saved images
private/
  voting.sqlite                    Initialized database; public votes start empty
  config.php                       Unique export secret and hashed admin key
  run.json                         Original run settings and checkpoint snapshot
  disabled_pairs.json              Exclusion snapshot
  failures.jsonl                   Failure log, when present
HOSTING.md                         Deployment instructions and private admin key
manifest.json                      Export summary
```

The export is independent of ComfyUI. Host it with **PHP 8.1+ and PDO_SQLITE**, with **public/** as the web root and **private/** outside it. On shared hosting, copy public/'s contents into public_html/ and place private/ beside public_html/. Give PHP write access to private/ and the database. Keep HOSTING.md private because it contains the admin key. For a local preview, extract the ZIP and run `php -S 127.0.0.1:8080 -t public` from its directory.

Visitors rate images from 1 to 5, can update their ratings, and can compare image/configuration leaderboards. Blind review is enabled initially. Voting identity is a random browser cookie, stored only as a keyed hash; the application does not store IP addresses. This limits accidental duplicate votes, not determined ballot manipulation: clearing cookies or changing browsers creates another identity. CSRF validation, prepared queries and basic rate limiting are included.

The admin key in HOSTING.md opens admin.html, where summaries can be downloaded as CSV and the whole voting dataset as JSON. Back up private/voting.sqlite to preserve public votes. Replacing it with a fresh export resets them.

Exports are **snapshots** of saved images, including partial/running sweeps. Disabled-pair images are omitted unless requested. Local reviews/notes are also excluded unless explicitly included; they never count as community votes. Prompts, images and generation settings are exported. Missing images are counted in manifest.json. Each run has its own dataset; matching saved trials can appear in multiple overlapping run snapshots. ZIP files remain in `krea2_lab/exports/` for download and backup.

## Pause, resume and storage

The sweep runs inside ComfyUI. Closing the browser does not stop it. **Pause after trial** saves progress after the current image; **Resume saved sweep** continues the saved browser plan. Alternatively, submit the same configuration again. Completed trial records are reused rather than regenerated.

Changing test settings creates a different sweep. Changing the experiment name deliberately creates a new experiment. Replacing model weights at the same filename is not detected as a new model version; use a new experiment name after replacing weights.

Everything is stored under the selected ComfyUI **output directory**:

```text
krea2_lab/
  <trial-id>.png / <trial-id>.json   Images, settings and reviews
  sweeps/                          Checkpoints and failure logs
  scores/                          Optional detector outputs
  disabled_pairs.json              Incompatible-pair list
  detector_settings.json           Detector opt-in preference
```

PNG filenames include ComfyUI's normal numeric suffix. Back up the whole `krea2_lab` directory to preserve results. The launcher stores its remembered installation and startup logs in `%LOCALAPPDATA%\Krea2RealismLab`.

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

## License

[MIT](LICENSE) for this project's code. ComfyUI, models and optional dependencies retain their respective licenses. This is an independent project, not an official Krea or ComfyUI product.
