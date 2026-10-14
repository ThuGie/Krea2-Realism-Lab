import hashlib
import itertools
import json
from pathlib import Path
import secrets
import shutil
import sqlite3
import tempfile
import time
import zipfile


def run_contains(trial, run):
    settings, configuration = trial['settings'], run['configuration']
    graph = settings.get('graph') or {}
    model = graph.get('1', {}).get('inputs', {}).get('unet_name')
    encoder = graph.get('2', {}).get('inputs', {}).get('clip_name')
    vae = graph.get('3', {}).get('inputs', {}).get('vae_name')
    latent = graph.get('4', {}).get('inputs', {})
    pairs = configuration.get('lora_pairs', [('NONE', 0)] + list(itertools.product(configuration['loras'], configuration['strengths'])))
    return (settings.get('experiment') == configuration['experiment'] and model in configuration['models']
        and encoder == configuration['encoder'] and vae == configuration['vae']
        and latent.get('width') == configuration['width'] and latent.get('height') == configuration['height']
        and [settings['lora'], settings['strength']] in [list(pair) for pair in pairs]
        and settings['prompt'] in configuration['prompts'] and settings['seed'] in configuration['seeds']
        and settings['sampler'] in configuration['samplers'] and settings['scheduler'] in configuration['schedulers']
        and settings['steps'] in configuration.get('step_values', [configuration['steps']])
        and settings['cfg'] in configuration.get('cfg_values', [configuration['cfg']])
        and settings.get('negative', '') == configuration.get('negative', '')
        and settings.get('trigger', '') == configuration.get('triggers', {}).get(settings['lora'], ''))


def build_voting_export(output_directory, run, disabled=(), include_disabled=False, include_reviews=False):
    output = Path(output_directory).resolve()
    lab = output / 'krea2_lab'
    destination = lab / 'exports'
    destination.mkdir(exist_ok=True)
    disabled = set(map(tuple, disabled))
    key = run['id']
    if len(key) != 64 or any(c not in '0123456789abcdef' for c in key):
        raise ValueError('Invalid run ID')
    template = Path(__file__).parent / 'voting_site'
    export_id = key[:12] + '-' + secrets.token_hex(4)
    archive = destination / ('krea2-voting-' + export_id + '.zip')
    with tempfile.TemporaryDirectory(prefix='krea2-voting-', dir=destination) as temporary:
        site = Path(temporary)
        shutil.copytree(template / 'public', site / 'public')
        private = site / 'private'
        private.mkdir()
        (private / 'run.json').write_text(json.dumps(run, indent=2), encoding='utf-8')
        (private / 'disabled_pairs.json').write_text(json.dumps(sorted(disabled)), encoding='utf-8')
        failures = lab / 'sweeps' / (key + '.errors.jsonl')
        if failures.exists():
            shutil.copyfile(failures, private / 'failures.jsonl')
        images_directory = site / 'public' / 'images'
        images_directory.mkdir()
        admin_key, secret = secrets.token_urlsafe(32), secrets.token_hex(32)
        config = dict(admin_key_hash=hashlib.sha256(admin_key.encode()).hexdigest(), secret=secret, run_id=key)
        (private / 'config.php').write_text("<?php\nreturn json_decode('" + json.dumps(config) + "', true);\n", encoding='utf-8')
        (private / '.htaccess').write_text('Require all denied\n', encoding='utf-8')
        db = sqlite3.connect(private / 'voting.sqlite')
        try:
            db.executescript('''
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE trials (id TEXT PRIMARY KEY, position INTEGER UNIQUE NOT NULL,
                    prompt TEXT NOT NULL, images TEXT NOT NULL, settings TEXT NOT NULL,
                    config_key TEXT NOT NULL, local_review TEXT);
                CREATE TABLE votes (trial_id TEXT NOT NULL REFERENCES trials(id), voter TEXT NOT NULL,
                    score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 5), updated_at INTEGER NOT NULL,
                    PRIMARY KEY(trial_id, voter));
                CREATE INDEX votes_updated ON votes(voter, updated_at);
                CREATE INDEX trials_configuration ON trials(config_key);
            ''')
            manifest = dict(run_id=key, title=run['configuration']['experiment'], exported_at=time.time(),
                run_status=run.get('status', 'unknown'), disabled_included=include_disabled,
                local_reviews_included=include_reviews, missing_images=0, trials=0)
            paths = list(lab.glob('*.json'))
            secrets.SystemRandom().shuffle(paths)
            for path in paths:
                if len(path.stem) != 64:
                    continue
                trial = json.loads(path.read_text(encoding='utf-8'))
                if not run_contains(trial, run):
                    continue
                settings = trial['settings']
                if not include_disabled and (settings['sampler'], settings['scheduler']) in disabled:
                    continue
                copied = []
                for index, image in enumerate(trial['images']):
                    source = (output / image['subfolder'] / image['filename']).resolve()
                    if not source.is_relative_to(lab) or source.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp'):
                        raise ValueError('Export images must stay inside Krea2 Lab output')
                    if not source.is_file():
                        manifest['missing_images'] += 1
                        continue
                    name = trial['id'] + '-' + str(index) + source.suffix.lower()
                    shutil.copyfile(source, images_directory / name)
                    copied.append('images/' + name)
                if not copied:
                    continue
                # Export generation settings, never local paths, executable graphs or detector confidence.
                public_settings = {field: settings[field] for field in ('lora','strength','seed','steps','cfg','sampler','scheduler','trigger','negative')}
                seconds = trial.get('seconds')
                public_settings['generation_seconds'] = seconds if isinstance(seconds, (int, float)) and not isinstance(seconds, bool) and 0 < seconds < float('inf') else None
                public_settings.update(model=settings['graph']['1']['inputs']['unet_name'],
                    width=run['configuration']['width'], height=run['configuration']['height'])
                group = {field: public_settings[field] for field in ('model','lora','strength','steps','cfg','sampler','scheduler','width','height')}
                config_key = hashlib.sha256(json.dumps(group, sort_keys=True).encode()).hexdigest()
                db.execute('INSERT INTO trials VALUES (?,?,?,?,?,?,?)', (trial['id'], manifest['trials'],
                    settings['prompt'], json.dumps(copied), json.dumps(public_settings), config_key,
                    json.dumps(trial.get('review', {})) if include_reviews else None))
                manifest['trials'] += 1
            if not manifest['trials']:
                raise ValueError('This run has no saved images matching the export options')
            db.execute('INSERT INTO metadata VALUES (?,?)', ('manifest', json.dumps(manifest)))
            db.execute('INSERT INTO metadata VALUES (?,?)', ('run', json.dumps(run)))
            db.commit()
        finally:
            db.close()
        (site / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        guide = (template / 'HOSTING.md').read_text(encoding='utf-8')
        (site / 'HOSTING.md').write_text(guide + '\n\n## This export\n\nAdmin access key: `' + admin_key + '`\n'
            + 'Run ID: `' + key + '`\nExported images: ' + str(manifest['trials']) + '\n', encoding='utf-8')
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as bundle:
            for path in site.rglob('*'):
                if path.is_file():
                    bundle.write(path, path.relative_to(site).as_posix())
    return archive
