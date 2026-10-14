import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

MODEL_ID = 'Ateeqq/ai-vs-human-image-detector'
REVISION = '60e82406916921b823616bee33397baab38af3f0'


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


parser = argparse.ArgumentParser(description='Explicitly download the optional experimental detector')
parser.add_argument('--model-dir', type=Path, required=True)
parser.add_argument('--plugin-dir', type=Path, default=Path(__file__).parent / 'comfyui_krea2_lab')
args = parser.parse_args()
target = args.model_dir.resolve()
target.mkdir(parents=True, exist_ok=True)
base = f'https://huggingface.co/{MODEL_ID}/resolve/{REVISION}/'
with urllib.request.urlopen(f'https://huggingface.co/api/models/{MODEL_ID}/tree/{REVISION}') as response:
    files = {entry['path']: entry for entry in json.load(response)}
for name in ('config.json', 'preprocessor_config.json', 'model.safetensors'):
    path = target / name
    entry = files[name]
    digest = entry.get('lfs', {}).get('oid')
    if path.exists() and path.stat().st_size == entry['size']:
        if not digest or file_sha256(path) == digest:
            print(f'Already installed: {name}', flush=True)
            continue
    print(f'Downloading {name} ({entry["size"] / 1024**2:.1f} MB)', flush=True)
    temporary = path.with_suffix('.download')
    with urllib.request.urlopen(base + name, timeout=120) as response, temporary.open('wb') as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    if digest:
        if file_sha256(temporary) != digest:
            raise RuntimeError('Model checksum mismatch')
    temporary.replace(path)
config = dict(model_directory=str(target), model_id=MODEL_ID, revision=REVISION)
(args.plugin_dir / 'detector_config.json').write_text(json.dumps(config, indent=2))
print('Local detector installed. Images are never uploaded.', flush=True)
