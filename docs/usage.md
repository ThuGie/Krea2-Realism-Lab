# Using Krea2 Realism Lab

[← Back to the README](../README.md)

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
- Display preferences: locally bundled OpenDyslexic font, larger text, extra reading space, six color palettes, and dark/light/high-contrast appearances. Preferences stay in your browser. OpenDyslexic is by Abelardo Gonzalez, distributed under the [SIL Open Font License](../comfyui_krea2_lab/web/OpenDyslexic-OFL.txt); [upstream source](https://github.com/antijingoist/opendyslexic).
- Minimum-rating filtering and a one-click gallery filter reset.
- Workspace with separate setup and run controls, experiment and unreviewed filters, adjustable image size, 48-image pagination, and comparison for 2–8 images with adjustable columns and zoom that respects blind review. Unsaved review notes survive automatic refreshes within the page session.
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

