const OPTION_HELP = {
  loadMore: ['Load more images','Adds the next 48 matching images to the gallery. Sorting applies to all matching results before pagination, so fastest or highest-rated images appear first across the entire collection. Filters reset the gallery to its first page.'],
  experimentFilter: ['Experiment filter','Show saved images from one named experiment, or choose the empty first entry for all experiments. Combines with text search and unreviewed filtering. The leaderboard and summary follow these filters; the website export run is selected separately.'],
  onlyUnrated: ['Unreviewed images','Show only images without your local realism rating. Use this to work through a large run. Rated images disappear from this view after saving; turn the filter off to see them again.'],
  gallerySize: ['Gallery image size','Choose compact cards for scanning, comfortable cards for normal reviewing, or large images for detail. This preference is remembered in this browser. Click any image to view it at full size.'],
  compareOpen: ['Compare two images','Use Compare image on two gallery cards, then Compare selected to view them side by side. Blind review hides their generation labels here too. Selection stays while filtering; clear it to start another comparison.'],
  compareClear: ['Clear comparison','Deselect both comparison images without changing their scores, notes or generated files. You can then select a different pair of images.'],
  compareClose: ['Close comparison','Return to the gallery. Your selected images remain selected so you can reopen the same comparison or clear them and choose another pair.'],

  reviewScore: ['Realism rating','Your own score from 1 to 5. Judge believable anatomy, skin, materials and lighting rather than liking the subject. Ratings are saved locally and form the human-review leaderboard. They are never treated as public votes in an exported site.'],
  reviewNotes: ['Review notes','Optional private observations about this trial, such as malformed hands or plastic-looking skin. Save notes after editing. They stay out of a voting export unless Include my local reviews and notes is explicitly checked.'],
  reviewSave: ['Save notes','Saves the text beside this image with its existing human rating. Choose a rating first. It does not start generation or change the configuration.'],
  reEnablePair: ['Re-enable a pair','Removes this sampler/scheduler match from exclusions. Its saved images return to the active gallery and leaderboard, and future occurrences may generate again. Already skipped combinations are not rewound.'],
  testMode: ['Test mode','Choose a preset for which dimensions vary. LoRAs + strengths tests every candidate LoRA on one fixed model/sampler/scheduler. Samplers only and Schedulers only vary that single dimension. Everything tests the full product. Custom lets you choose the checkboxes yourself.'],
  testModels: ['Test every Krea2 model','When checked, every discovered Krea2 diffusion model is tested. When unchecked, only Fixed model is used. Discovery uses filenames or folders containing krea.'],
  fixedModel: ['Fixed model','The diffusion model used when Test every Krea2 model is unchecked. The control is disabled while models are being swept. Different model sizes and precision formats can have very different speed and memory requirements.'],
  testLoras: ['Test every Krea2 LoRA','Tests each discovered Krea2 LoRA individually. This does not stack LoRAs. Uncheck it to use one Fixed LoRA, or NONE for a sampler/model comparison without a LoRA.'],
  fixedLora: ['Fixed LoRA','Used when the LoRA sweep is off. NONE uses the base model without a LoRA. For a strength-only comparison, select the LoRA whose strength should vary.'],
  testStrengths: ['Test strength grid','Vary the LoRA weight using the comma-separated Strengths list. If unchecked, Fixed LoRA strength is used. Strength has no effect when Fixed LoRA is NONE.'],
  fixedStrength: ['Fixed LoRA strength','The LoRA multiplier when the strength grid is off. 0 disables its weight contribution, 1 uses its nominal training strength, and values above 1 amplify it. Negative values can reverse slider effects, depending on the LoRA.'],
  testSamplers: ['Test every sampler','A sampler determines how each denoising step is calculated. Check to compare all registered samplers; uncheck to keep one Fixed sampler. Some samplers may be incompatible with particular schedulers.'],
  fixedSampler: ['Fixed sampler','Used when the sampler sweep is off. For a scheduler-only comparison, hold this value fixed. Live incompatible-pair exclusions still apply.'],
  testSchedulers: ['Test every scheduler','A scheduler chooses the noise levels used across denoising steps. Check to compare every registered scheduler; uncheck to use one Fixed scheduler. It interacts with the sampler.'],
  fixedScheduler: ['Fixed scheduler','Used when the scheduler sweep is off. Keep it fixed for a sampler-only comparison. A disabled sampler/scheduler match will still be skipped.'],
  includeBaseline: ['No-LoRA baseline','Adds a base-model image without a LoRA for every tested model/sampler/scheduler/step/CFG/prompt/seed setting. This helps distinguish a LoRA improvement from a strong base model. NONE comparisons always need a base-model image, even with this unchecked.'],
  testSteps: ['Test step grid','Enable to compare the step counts in Step grid instead of the fixed Steps value. More steps take longer and do not always improve a distilled model.'],
  stepGrid: ['Step grid','Comma-separated positive integers, for example 8, 12, 16. Each is crossed with all other tested dimensions. Used only when Test step grid is enabled.'],
  testCfg: ['Test CFG grid','Enable to compare the CFG values in CFG grid instead of the fixed CFG value. This multiplies the number of images by the number of CFG values.'],
  cfgGrid: ['CFG grid','Comma-separated non-negative numbers, for example 1, 1.5, 2. Krea2 Turbo normally starts at CFG 1. Larger guidance is not automatically better and can introduce artifacts.'],
  experiment: ['Experiment name','A label for this set of tests. The configuration and name identify a saved sweep. Reusing an identical configuration resumes it; changing this name deliberately creates a new experiment, including after replacing model weights at the same filename.'],
  encoder: ['Text encoder','Converts prompt text into conditioning. Select a text encoder compatible with Krea2; the page prefers qwen3vl_4b_fp8_scaled.safetensors when installed. The encoder remains fixed across the sweep.'],
  vae: ['VAE','Decodes sampled latents into visible images. Choose a compatible Krea2 VAE; qwen_image_vae.safetensors is the initial preference. Changing the VAE can change colors, texture and memory use.'],
  strengths: ['Strengths','Comma-separated LoRA weights, such as 0.25, 0.5, 0.75, 1. Duplicate values are removed. Used only when the strength grid is enabled. Every value is tested against every selected LoRA and sampling configuration.'],
  prompts: ['Prompts','One prompt per line. Every configuration receives the same prompts, making comparisons fairer. A single prompt is faster; several diverse prompts help reveal configurations that work only for one scene.'],
  seeds: ['Seeds','Comma-separated non-negative integer seeds. Seeds control the starting noise. Reusing each seed across configurations makes comparisons more controlled; several seeds reduce dependence on a lucky result.'],
  steps: ['Steps','Fixed denoising step count when Test step grid is off. The default is 8 for Krea2 Turbo. Other models or samplers can need different values.'],
  cfg: ['CFG','Fixed classifier-free guidance value when the CFG grid is off. It controls prompt guidance relative to the negative conditioning. The default is 1 for Krea2 Turbo; high values can hurt distilled models.'],
  width: ['Image width','Output width in pixels. Larger images increase memory use, generation time and exported website size. Use dimensions supported by your model and VAE.'],
  height: ['Image height','Output height in pixels. Hold size constant when comparing models or LoRAs. Changing the aspect ratio can also affect composition and anatomy.'],
  triggers: ['LoRA trigger map','A JSON object mapping exact installed LoRA filenames to trigger text, for example {"krea2\\\\example.safetensors":"trigger words"}. The matching trigger is appended to the positive prompt for that LoRA. Baselines do not receive it.'],
  negative: ['Negative prompt','Shared negative conditioning for every trial. Its visible effect depends on CFG and the model. Keep it consistent when evaluating configurations.'],
  pairSampler: ['Sampler for exclusion','Choose the sampler half of a pair you want to stop testing. This is independent of the Fixed sampler used to design a sweep.'],
  pairScheduler: ['Scheduler for exclusion','Choose the scheduler half of an incompatible pair. Already disabled matches are removed from this selector and managed in Disabled pairs.'],
  disablePair: ['Disable this pair','Skip future trials with this sampler/scheduler match across all models and LoRA strengths. Existing results are hidden from the active gallery and leaderboard but kept on disk. The currently generating image is allowed to finish.'],
  disableCurrent: ['Disable currently running pair','Adds the current sweep sampler/scheduler match to the exclusion list. It affects future occurrences, not the current image.'],
  start: ['Start selected tests','Queues the chosen configuration as a sweep inside ComfyUI. Inspect the estimated combination count first. The browser can close after submission; generation continues in ComfyUI.'],
  pause: ['Pause after trial','Stops the sweep after its current image finishes and saves the checkpoint. It does not cancel unrelated ComfyUI work.'],
  resume: ['Resume saved sweep','Resubmits the saved browser plan and continues from the server checkpoint. Finished images are reused. If there is no saved browser plan, the current test form is used instead.'],
  refresh: ['Refresh results','Reloads saved images, ratings, detector state, exclusions, exportable runs and sweep progress. Results also refresh periodically.'],
  export: ['Export JSON','Downloads local trial settings, reviews, optional detector scores and the browser sweep plan. This is data only; use Build voting website ZIP for a complete hostable website with images and SQLite.'],
  csv: ['Export CSV','Downloads a spreadsheet-friendly summary of local trial settings and ratings. Images are not embedded. Human ratings and experimental classifier scores are separate columns.'],
  score: ['Score saved images','Starts the optional local CPU classifier for saved images. It works only after the experimental detector is explicitly enabled. It does not assess believable anatomy reliably.'],
  enableDetector: ['Experimental AI detector','Off by default. Enabling starts a local CPU classifier, not a validated human-realism judge. It can label broken images as human-class with high confidence. Disable it to stop scoring and hide its scores/sort.'],
  search: ['Filter results','Searches saved generation settings, including experiment, model, LoRA and prompt. The gallery and leaderboard follow the filter. It does not change the sweep or the selected run used for website export.'],
  sort: ['Sort results','Fastest/slowest generation sorts images by recorded generation seconds and configurations by their mean time. Missing timings always appear last. Times reflect your hardware, caching and warm-up; compare similar image sizes and batches. Newest shows recent saved results first. Highest score sorts by your human review rating. Unreviewed first helps you finish scoring. The experimental classifier sort is available only after explicitly enabling the detector.'],
  blind: ['Blind review','Hides generation labels and detector scores so you can judge images without those hints. Prompts remain available. This changes the review display, not generation or saved settings.'],
  exportPairs: ['Export incompatible pairs','Downloads the disabled sampler/scheduler matches as portable JSON. Images and votes are not included.'],
  importMode: ['Incompatible-pair import mode','Merge adds imported exclusions to your current list. Replace removes the current exclusions and uses only the imported list. Imports are validated before changes are saved.'],
  importPairs: ['Import incompatible pairs','Choose an exported JSON list. Duplicates are removed. Names not installed here remain recorded for portability. Changes apply to upcoming trials while a sweep runs.'],
  exportRun: ['Run to export','Choose the exact saved sweep for the standalone voting website. The ID distinguishes different configurations with the same experiment name. Export includes currently saved matching images, even if that run is paused or still running.'],
  votingIncludeDisabled: ['Include disabled images','Unchecked: omit images belonging to currently disabled sampler/scheduler pairs. Checked: include their matching saved images in the voting dataset too. No local images are deleted.'],
  votingIncludeReviews: ['Include local reviews and notes','Unchecked by default to keep your private notes out of the shared package. Checked: store them in the exported database for the administrator. They never count as public votes. Prompts and generation settings are exported regardless.'],
  votingExport: ['Build voting website ZIP','Creates a self-contained snapshot with PHP, HTML, JavaScript, CSS, images, SQLite, administration and hosting instructions. Requires PHP 8.1+ and PDO_SQLITE on the host. Keep private/ outside the web root. Public votes start empty, and later generated images are not automatically added.']
};

document.addEventListener('click', event => {
  const button = event.target.closest('[data-help]');
  if (!button) return;
  event.preventDefault();
  event.stopPropagation();
  const help = OPTION_HELP[button.dataset.help];
  if (!help) return;
  document.getElementById('helpTitle').textContent = help[0];
  document.getElementById('helpText').textContent = help[1];
  document.getElementById('helpDialog').showModal();
});
document.getElementById('closeHelp').onclick = () => document.getElementById('helpDialog').close();
