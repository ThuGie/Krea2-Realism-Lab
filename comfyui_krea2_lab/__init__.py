import hashlib
import json
import math
import itertools
import os
import subprocess
import sys
from pathlib import Path
import threading
import time

from aiohttp import web
import comfy.model_management
import comfy.samplers
import comfy.sd
import comfy.utils
import folder_paths
import nodes
from server import PromptServer

LOCK = threading.Lock()
BACKEND_HASH = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
PAUSE = threading.Event()
DETECTOR_PROCESS = None
DEFAULT_STRENGTHS = '0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2'
DEFAULT_PROMPT = 'Candid photograph of an adult woman at a cafe window, natural skin texture, detailed hands holding a ceramic cup, soft daylight, unretouched photography.'


def krea_candidates(kind):
    return [name for name in folder_paths.get_filename_list(kind) if 'krea' in name.lower()]


def sweep_graph(model, encoder, vae, width, height, trial):
    return {
        '1': {'class_type': 'UNETLoader', 'inputs': {'unet_name': model, 'weight_dtype': 'default'}},
        '2': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': encoder, 'type': 'krea2', 'device': 'default'}},
        '3': {'class_type': 'VAELoader', 'inputs': {'vae_name': vae}},
        '4': {'class_type': 'EmptyLatentImage', 'inputs': {'width': width, 'height': height, 'batch_size': 1}},
        '5': {'class_type': 'Krea2LabTrial', 'inputs': {
            'model': ['1', 0], 'clip': ['2', 0], 'vae': ['3', 0], 'latent': ['4', 0], **trial}},
    }


def root():
    path = Path(folder_paths.get_output_directory()) / 'krea2_lab'
    path.mkdir(parents=True, exist_ok=True)
    return path


def record_path(key):
    if len(key) != 64 or any(c not in '0123456789abcdef' for c in key):
        raise web.HTTPBadRequest(text='Invalid trial ID')
    return root() / (key + '.json')


def write_record(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2), encoding='utf-8')
    temporary.replace(path)


def disabled_pairs():
    path = root() / 'disabled_pairs.json'
    with LOCK:
        data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    return {tuple(pair) for pair in data.get('disabled', [])}


def pending_enabled(state, disabled):
    remaining = max(0, state.get('total', 0) - state.get('index', 0))
    configuration = state.get('configuration')
    if not configuration or not disabled:
        return remaining
    samplers, schedulers = configuration['samplers'], configuration['schedulers']
    block = len(configuration['prompts']) * len(configuration['seeds']) * len(configuration.get('step_values', [8])) * len(configuration.get('cfg_values', [1]))
    cycle = len(samplers) * len(schedulers) * block
    cycles_before, offset = divmod(state['index'], cycle)
    repetitions = len(configuration['models']) * len(configuration.get('lora_pairs', [('NONE', 0)] + list(itertools.product(configuration['loras'], configuration['strengths']))))
    for sampler, scheduler in disabled:
        if sampler not in samplers or scheduler not in schedulers:
            continue
        start = (samplers.index(sampler) * len(schedulers) + schedulers.index(scheduler)) * block
        already_passed = cycles_before * block + min(block, max(0, offset - start))
        remaining -= repetitions * block - already_passed
    return max(0, remaining)


def detector_enabled():
    path = root() / 'detector_settings.json'
    with LOCK:
        return json.loads(path.read_text(encoding='utf-8')).get('enabled') is True if path.exists() else False


def start_detector():
    global DETECTOR_PROCESS
    if not detector_enabled():
        return False
    configuration = Path(__file__).parent / 'detector_config.json'
    if not configuration.exists():
        return False
    with LOCK:
        if DETECTOR_PROCESS is None or DETECTOR_PROCESS.poll() is not None:
            log = root() / 'detector.log'
            with log.open('a', encoding='utf-8') as output:
                DETECTOR_PROCESS = subprocess.Popen([
                    sys.executable, str(Path(__file__).parent / 'detector_worker.py'),
                    '--output', folder_paths.get_output_directory(), '--parent', str(os.getpid())],
                    stdout=output, stderr=output,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    return True


def eta_fields(state, now=None):
    now = time.time() if now is None else now
    samples = state.get('recent_seconds', [])
    remaining = state.get('remaining_enabled', max(0, state.get('total', 0) - state.get('index', 0)))
    if not remaining:
        return dict(remaining_seconds=0, estimated_finish_at=None, timing_samples=len(samples))
    if len(samples) < 3:
        return dict(remaining_seconds=None, estimated_finish_at=None, timing_samples=len(samples))
    average = sum(samples) / len(samples)
    current_elapsed = max(0, now - state.get('current_started_at', now)) if state.get('status') == 'running' else 0
    remaining_seconds = max(0, remaining * average - current_elapsed)
    return dict(remaining_seconds=round(remaining_seconds), seconds_per_image=round(average, 2),
                estimated_finish_at=now + remaining_seconds if state.get('status') == 'running' else None,
                timing_samples=len(samples), active_seconds=round(state.get('active_seconds', 0)))


class Krea2LabTrial:
    @staticmethod
    def identity(latent, api_prompt, lora_name, strength, prompt, trigger, negative, seed,
                 steps, cfg, sampler_name, scheduler, experiment):
        settings = dict(lora=lora_name, strength=strength, prompt=prompt, trigger=trigger,
                        negative=negative, seed=seed, steps=steps, cfg=cfg, sampler=sampler_name,
                        scheduler=scheduler, experiment=experiment,
                        latent_shape=list(latent['samples'].shape), graph=api_prompt)
        return settings, hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'model': ('MODEL',), 'clip': ('CLIP',), 'vae': ('VAE',), 'latent': ('LATENT',),
            'lora_name': (['NONE'] + folder_paths.get_filename_list('loras'),),
            'strength': ('FLOAT', {'default': 0.75, 'min': -20, 'max': 20, 'step': 0.05}),
            'prompt': ('STRING', {'multiline': True}),
            'trigger': ('STRING', {'default': ''}),
            'negative': ('STRING', {'multiline': True, 'default': ''}),
            'seed': ('INT', {'default': 42, 'min': 0, 'max': 0xffffffffffffffff}),
            'steps': ('INT', {'default': 8, 'min': 1, 'max': 10000}),
            'cfg': ('FLOAT', {'default': 1.0, 'min': 0, 'max': 100}),
            'sampler_name': (comfy.samplers.KSampler.SAMPLERS,),
            'scheduler': (comfy.samplers.KSampler.SCHEDULERS,),
            'experiment': ('STRING', {'default': 'Krea2 realism'}),
        }, 'hidden': {'api_prompt': 'PROMPT'}}

    RETURN_TYPES = ('STRING',)
    RETURN_NAMES = ('trial_id',)
    FUNCTION = 'run'
    CATEGORY = 'Krea2 Lab'
    OUTPUT_NODE = True

    def run(self, model, clip, vae, latent, lora_name, strength, prompt, trigger,
            negative, seed, steps, cfg, sampler_name, scheduler, experiment, api_prompt=None,
            execution_cache=None):
        if not math.isfinite(strength) or not math.isfinite(cfg):
            raise ValueError('Strength and CFG must be finite')
        start_detector()
        started = time.monotonic()
        cache = execution_cache if execution_cache is not None else {}
        base_model = model
        lora_key = (lora_name, strength)
        if cache.get('base_model') is base_model and cache.get('lora_key') == lora_key:
            model = cache['patched_model']
        elif lora_name != 'NONE' and strength != 0:
            if lora_name not in folder_paths.get_filename_list('loras'):
                raise ValueError('Select an installed LoRA')
            weights = comfy.utils.load_torch_file(folder_paths.get_full_path_or_raise('loras', lora_name), safe_load=True)
            patched, _ = comfy.sd.load_lora_for_models(model, None, weights, strength, 0)
            if sum(map(len, patched.patches.values())) <= sum(map(len, model.patches.values())):
                raise ValueError('No LoRA weights matched this model; trial was not generated')
            model = patched
            del weights
        cache.update(base_model=base_model, lora_key=lora_key, patched_model=model)
        text = prompt + (', ' + trigger if trigger and lora_name != 'NONE' else '')
        same_clip = cache.get('clip') is clip
        if same_clip and cache.get('positive_text') == text:
            positive = cache['positive']
        else:
            positive = nodes.CLIPTextEncode().encode(clip, text)[0]
        if same_clip and cache.get('negative_text') == negative:
            neg = cache['negative']
        else:
            neg = nodes.CLIPTextEncode().encode(clip, negative)[0]
        cache.update(clip=clip, positive_text=text, positive=positive, negative_text=negative, negative=neg)
        samples = nodes.common_ksampler(model, seed, steps, cfg, sampler_name, scheduler, positive, neg, latent)[0]
        images = nodes.VAEDecode().decode(vae, samples)[0]
        settings, key = self.identity(latent, api_prompt, lora_name, strength, prompt, trigger,
                                     negative, seed, steps, cfg, sampler_name, scheduler, experiment)
        saved = nodes.SaveImage().save_images(images, 'krea2_lab/' + key, prompt=api_prompt)
        with LOCK:
            path = record_path(key)
            previous = json.loads(path.read_text()) if path.exists() else {}
            write_record(path, dict(id=key, settings=settings, images=saved['ui']['images'],
                                    seconds=round(time.monotonic() - started, 2),
                                    review=previous.get('review', {})))
        return {'ui': saved['ui'], 'result': (key,)}


class Krea2LabSweep:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'encoder': (folder_paths.get_filename_list('text_encoders'), {'default': 'qwen3vl_4b_fp8_scaled.safetensors'}),
            'vae_name': (folder_paths.get_filename_list('vae'), {'default': 'qwen_image_vae.safetensors'}),
            'strengths': ('STRING', {'default': DEFAULT_STRENGTHS}),
            'prompts': ('STRING', {'default': DEFAULT_PROMPT, 'multiline': True}),
            'seeds': ('STRING', {'default': '42'}),
            'steps': ('INT', {'default': 8, 'min': 1, 'max': 10000}),
            'cfg': ('FLOAT', {'default': 1.0, 'min': 0, 'max': 100}),
            'width': ('INT', {'default': 1024, 'min': 64, 'step': 8}),
            'height': ('INT', {'default': 1024, 'min': 64, 'step': 8}),
            'experiment': ('STRING', {'default': 'Krea2 automatic sweep'}),
            'trigger_map': ('STRING', {'default': '{}', 'multiline': True}),
            'negative': ('STRING', {'default': '', 'multiline': True}),
        }, 'optional': {
            'test_models': ('BOOLEAN', {'default': True}),
            'test_loras': ('BOOLEAN', {'default': True}),
            'test_strengths': ('BOOLEAN', {'default': True}),
            'test_samplers': ('BOOLEAN', {'default': True}),
            'test_schedulers': ('BOOLEAN', {'default': True}),
            'fixed_model': (['AUTO'] + krea_candidates('diffusion_models'),),
            'fixed_lora': (['NONE'] + krea_candidates('loras'),),
            'fixed_strength': ('FLOAT', {'default': 0.75, 'min': -20, 'max': 20}),
            'fixed_sampler': (['AUTO'] + list(comfy.samplers.KSampler.SAMPLERS),),
            'fixed_scheduler': (['AUTO'] + list(comfy.samplers.KSampler.SCHEDULERS),),
            'include_baseline': ('BOOLEAN', {'default': True}),
            'step_values': ('STRING', {'default': ''}),
            'cfg_values': ('STRING', {'default': ''}),
        }}

    RETURN_TYPES = ('STRING',)
    RETURN_NAMES = ('summary',)
    FUNCTION = 'run'
    CATEGORY = 'Krea2 Lab'
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float('nan')

    def run(self, encoder, vae_name, strengths, prompts, seeds, steps, cfg, width, height,
            experiment, trigger_map, negative, test_models=True, test_loras=True,
            test_strengths=True, test_samplers=True, test_schedulers=True,
            fixed_model='AUTO', fixed_lora='NONE', fixed_strength=0.75,
            fixed_sampler='AUTO', fixed_scheduler='AUTO', include_baseline=True,
            step_values='', cfg_values=''):
        models = krea_candidates('diffusion_models')
        loras = krea_candidates('loras')
        if not test_models:
            fixed_model = models[0] if fixed_model == 'AUTO' and models else fixed_model
            if fixed_model not in models:
                raise ValueError('Choose an installed Krea2 model')
            models = [fixed_model]
        if not test_loras:
            if fixed_lora != 'NONE' and fixed_lora not in loras:
                raise ValueError('Choose an installed Krea2 LoRA or NONE')
            loras = [] if fixed_lora == 'NONE' else [fixed_lora]
        strength_values = list(dict.fromkeys(float(s.strip()) for s in strengths.split(','))) if test_strengths else [fixed_strength]
        seed_values = list(dict.fromkeys(int(s.strip()) for s in seeds.split(',')))
        prompt_values = list(dict.fromkeys(s.strip() for s in prompts.splitlines() if s.strip()))
        triggers = json.loads(trigger_map)
        if not models or (test_loras and not loras) or not prompt_values:
            raise ValueError('No installed Krea2 models/LoRAs or no prompts found')
        if any(not math.isfinite(s) for s in strength_values):
            raise ValueError('Strengths must be finite')
        if not isinstance(triggers, dict) or any(not isinstance(v, str) for v in triggers.values()):
            raise ValueError('Trigger map must contain filename: text pairs')
        samplers = list(comfy.samplers.KSampler.SAMPLERS)
        schedulers = list(comfy.samplers.KSampler.SCHEDULERS)
        if not test_samplers:
            fixed_sampler = ('res_2m_ode' if 'res_2m_ode' in samplers else 'euler') if fixed_sampler == 'AUTO' else fixed_sampler
            if fixed_sampler not in samplers:
                raise ValueError('Choose an installed sampler')
            samplers = [fixed_sampler]
        if not test_schedulers:
            fixed_scheduler = ('bong_tangent' if 'bong_tangent' in schedulers else schedulers[0]) if fixed_scheduler == 'AUTO' else fixed_scheduler
            if fixed_scheduler not in schedulers:
                raise ValueError('Choose an installed scheduler')
            schedulers = [fixed_scheduler]
        original_pairs = [('NONE', 0)] + list(itertools.product(loras, strength_values))
        pairs = ([('NONE', 0)] if include_baseline or not loras else []) + list(itertools.product(loras, strength_values))
        step_grid = list(dict.fromkeys(int(s.strip()) for s in step_values.split(','))) if step_values.strip() else [steps]
        cfg_grid = list(dict.fromkeys(float(s.strip()) for s in cfg_values.split(','))) if cfg_values.strip() else [cfg]
        if any(s < 1 for s in step_grid) or any(not math.isfinite(v) or v < 0 for v in cfg_grid):
            raise ValueError('Steps must be positive integers and CFG values finite and non-negative')
        dimensions = [pairs, samplers, schedulers, prompt_values, seed_values, step_grid, cfg_grid]
        per_model = math.prod(map(len, dimensions))
        configuration = dict(models=models, loras=loras, strengths=strength_values, samplers=samplers,
            schedulers=schedulers, prompts=prompt_values, seeds=seed_values, encoder=encoder,
            vae=vae_name, steps=steps, cfg=cfg, width=width, height=height,
            experiment=experiment, triggers=triggers, negative=negative)
        if pairs != original_pairs:
            configuration['lora_pairs'] = pairs
        if step_grid != [steps]:
            configuration['step_values'] = step_grid
        if cfg_grid != [cfg]:
            configuration['cfg_values'] = cfg_grid
        key = hashlib.sha256(json.dumps(configuration, sort_keys=True).encode()).hexdigest()
        directory = root() / 'sweeps'
        directory.mkdir(exist_ok=True)
        path = directory / (key + '.json')
        state = json.loads(path.read_text(encoding='utf-8')) if path.exists() else dict(
            id=key, index=0, total=per_model * len(models), succeeded=0, failed=0, configuration=configuration)
        PAUSE.clear()
        state['status'] = 'running'
        active_before = state.get('active_seconds', 0)
        session_started = time.monotonic()
        def checkpoint():
            state['updated'] = time.time()
            state['active_seconds'] = active_before + time.monotonic() - session_started
            with LOCK:
                write_record(path, state)
        def failure(error, trial):
            with (directory / (key + '.errors.jsonl')).open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(dict(index=state['index'], trial=trial, error=str(error))) + '\n')
            state['failed'] += 1
        checkpoint()
        start_detector()
        if state['index'] >= state['total']:
            state['status'] = 'complete'
            checkpoint()
            return (f"Already complete: {state['total']} combinations. Review at /krea2-lab",)
        clip = nodes.CLIPLoader().load_clip(encoder, type='krea2', device='default')[0]
        vae = nodes.VAELoader().load_vae(vae_name)[0]
        latent = nodes.EmptyLatentImage().generate(width, height, 1)[0]
        for model_index, model_name in enumerate(models):
            if state['index'] >= (model_index + 1) * per_model:
                continue
            if PAUSE.is_set():
                break
            comfy.model_management.throw_exception_if_processing_interrupted()
            try:
                model = nodes.UNETLoader().load_unet(model_name, 'default')[0]
            except Exception as error:
                failure(error, {'model': model_name, 'stage': 'model loading'})
                state['failed'] += (model_index + 1) * per_model - state['index'] - 1
                state['index'] = (model_index + 1) * per_model
                checkpoint()
                continue
            execution_cache = {}
            for offset, ((lora, strength), sampler, scheduler, prompt, seed, trial_steps, trial_cfg) in enumerate(itertools.product(*dimensions)):
                index = model_index * per_model + offset
                if index < state['index']:
                    continue
                if PAUSE.is_set():
                    break
                if (sampler, scheduler) in disabled_pairs():
                    state['skipped'] = state.get('skipped', 0) + 1
                    state['index'] = index + 1
                    checkpoint()
                    continue
                comfy.model_management.throw_exception_if_processing_interrupted()
                trial = dict(lora_name=lora, strength=strength, prompt=prompt,
                    trigger=triggers.get(lora, ''), negative=negative, seed=seed, steps=trial_steps, cfg=trial_cfg,
                    sampler_name=sampler, scheduler=scheduler, experiment=experiment)
                state['current'] = dict(model=model_name, **trial)
                state['current_started_at'] = time.time()
                checkpoint()
                graph = sweep_graph(model_name, encoder, vae_name, width, height, trial)
                trial_started = time.monotonic()
                try:
                    _, trial_key = Krea2LabTrial.identity(latent, graph, **trial)
                    if not record_path(trial_key).exists():
                        Krea2LabTrial().run(model=model, clip=clip, vae=vae, latent=latent, api_prompt=graph,
                                           execution_cache=execution_cache, **trial)
                        state['recent_seconds'] = (state.get('recent_seconds', []) + [time.monotonic() - trial_started])[-100:]
                    state['succeeded'] += 1
                except Exception as error:
                    failure(error, state['current'])
                state['index'] = index + 1
                checkpoint()
            del execution_cache, model
        state['status'] = 'paused' if PAUSE.is_set() else 'complete'
        checkpoint()
        return (f"{state['status']}: {state['index']}/{state['total']} combinations, "
                f"{state['succeeded']} generated, {state['failed']} failures. Review at /krea2-lab",)


routes = PromptServer.instance.routes


@routes.get('/krea2-lab')
async def page(request):
    return web.FileResponse(Path(__file__).parent / 'web' / 'index.html')


@routes.get('/krea2-lab/installation')
async def installation(request):
    return web.json_response({'comfy_root': str(Path(nodes.__file__).resolve().parent),
                              'backend_hash': BACKEND_HASH})


@routes.get('/krea2-lab/catalog')
async def catalog(request):
    return web.json_response(dict(loras=folder_paths.get_filename_list('loras'),
        krea_models=krea_candidates('diffusion_models'), krea_loras=krea_candidates('loras'),
        models=folder_paths.get_filename_list('diffusion_models'),
        encoders=folder_paths.get_filename_list('text_encoders'), vaes=folder_paths.get_filename_list('vae'),
        samplers=comfy.samplers.KSampler.SAMPLERS, schedulers=comfy.samplers.KSampler.SCHEDULERS))


@routes.get('/krea2-lab/sweep-status')
async def sweep_status(request):
    with LOCK:
        paths = list((root() / 'sweeps').glob('*.json'))
        state = json.loads(max(paths, key=lambda p: p.stat().st_mtime).read_text(encoding='utf-8')) if paths else {}
    state['remaining_enabled'] = pending_enabled(state, disabled_pairs())
    state.update(eta_fields(state))
    return web.json_response(state)


@routes.get('/krea2-lab/pairs')
async def get_pairs(request):
    return web.json_response({'disabled': sorted(disabled_pairs())})


@routes.post('/krea2-lab/pairs')
async def set_pair(request):
    data = await request.json()
    sampler, scheduler, disabled = data.get('sampler'), data.get('scheduler'), data.get('disabled')
    if not isinstance(sampler, str) or not isinstance(scheduler, str) or not isinstance(disabled, bool):
        raise web.HTTPBadRequest(text='Choose an installed sampler and scheduler, and a boolean disabled value')
    if disabled and (sampler not in comfy.samplers.KSampler.SAMPLERS or scheduler not in comfy.samplers.KSampler.SCHEDULERS):
        raise web.HTTPBadRequest(text='Choose an installed sampler and scheduler')
    path = root() / 'disabled_pairs.json'
    with LOCK:
        current = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        pairs = {tuple(pair) for pair in current.get('disabled', [])}
        if disabled:
            pairs.add((sampler, scheduler))
        else:
            pairs.discard((sampler, scheduler))
        write_record(path, {'disabled': sorted(pairs)})
    return web.json_response({'disabled': sorted(pairs)})


@routes.post('/krea2-lab/pairs/import')
async def import_pairs(request):
    data = await request.json()
    if not isinstance(data, dict):
        raise web.HTTPBadRequest(text='Import a JSON object containing a disabled pairs list')
    incoming = data.get('disabled')
    mode = data.get('mode', 'merge')
    if mode not in ('merge', 'replace') or data.get('version', 1) != 1 or not isinstance(incoming, list) or len(incoming) > 10000:
        raise web.HTTPBadRequest(text='Use a version 1 disabled-pairs JSON list and merge or replace mode')
    if any(not isinstance(pair, list) or len(pair) != 2 or
           any(not isinstance(name, str) or not name.strip() or len(name) > 256 for name in pair)
           for pair in incoming):
        raise web.HTTPBadRequest(text='Each disabled pair must contain a sampler name and scheduler name')
    path = root() / 'disabled_pairs.json'
    with LOCK:
        current = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        pairs = {tuple(pair) for pair in current.get('disabled', [])} if mode == 'merge' else set()
        pairs.update(tuple(pair) for pair in incoming)
        write_record(path, {'disabled': sorted(pairs)})
    return web.json_response({'disabled': sorted(pairs)})


@routes.get('/krea2-lab/detector-status')
async def detector_status(request):
    path = root() / 'scores' / 'status.json'
    data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'status': 'not started'}
    data['installed'] = (Path(__file__).parent / 'detector_config.json').exists()
    data['enabled'] = detector_enabled()
    if not data['enabled']:
        data['status'] = 'disabled'
    return web.json_response(data)


@routes.post('/krea2-lab/detector-settings')
async def detector_settings(request):
    data = await request.json()
    if not isinstance(data, dict) or not isinstance(data.get('enabled'), bool):
        raise web.HTTPBadRequest(text='Specify enabled as true or false')
    with LOCK:
        write_record(root() / 'detector_settings.json', {'enabled': data['enabled']})
    if data['enabled']:
        start_detector()
    elif DETECTOR_PROCESS is not None and DETECTOR_PROCESS.poll() is None:
        DETECTOR_PROCESS.terminate()
    return web.json_response({'enabled': data['enabled']})


@routes.post('/krea2-lab/score')
async def score(request):
    return web.json_response({'started': start_detector()})


@routes.post('/krea2-lab/pause')
async def pause(request):
    PAUSE.set()
    return web.json_response({'ok': True})


@routes.get('/krea2-lab/trials')
async def trials(request):
    with LOCK:
        data = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(root().glob('*.json'), key=lambda p: p.stat().st_mtime) if len(p.stem) == 64]
    for trial in data:
        score = root() / 'scores' / (trial['id'] + '.json')
        trial['detector'] = json.loads(score.read_text(encoding='utf-8')) if score.exists() else {}
    return web.json_response(data)


@routes.post('/krea2-lab/review/{key}')
async def review(request):
    path = record_path(request.match_info['key'])
    data = await request.json()
    score = data.get('score')
    if not isinstance(score, int) or not 1 <= score <= 5 or len(str(data.get('notes', ''))) > 10000:
        raise web.HTTPBadRequest(text='Use a score from 1 to 5 and notes under 10000 characters')
    with LOCK:
        if not path.exists():
            raise web.HTTPNotFound()
        trial = json.loads(path.read_text(encoding='utf-8'))
        trial['review'] = dict(score=score, notes=str(data.get('notes', '')))
        write_record(path, trial)
    return web.json_response({'ok': True})


NODE_CLASS_MAPPINGS = {'Krea2LabTrial': Krea2LabTrial, 'Krea2LabSweep': Krea2LabSweep}
NODE_DISPLAY_NAME_MAPPINGS = {'Krea2LabTrial': 'Krea2 Lab • Generate & Record Trial',
                            'Krea2LabSweep': 'Krea2 Lab • Selective / Full Sweep'}
