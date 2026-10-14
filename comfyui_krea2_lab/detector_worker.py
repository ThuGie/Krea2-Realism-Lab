import argparse
import json
import os
from pathlib import Path
import time

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = ''

import psutil
from PIL import Image
import torch
from transformers import AutoImageProcessor, AutoModelForImageClassification


def atomic_json(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2), encoding='utf-8')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--parent', type=int)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    output = Path(args.output).resolve()
    directory = output / 'krea2_lab'
    scores = directory / 'scores'
    scores.mkdir(parents=True, exist_ok=True)
    config = json.loads((Path(__file__).parent / 'detector_config.json').read_text())
    status_path = scores / 'status.json'
    status = dict(status='loading', model=config['model_id'], revision=config['revision'], scored=0)
    def enabled():
        path = directory / 'detector_settings.json'
        return args.once or (path.exists() and json.loads(path.read_text(encoding='utf-8')).get('enabled') is True)
    if not enabled():
        atomic_json(status_path, dict(status, status='disabled'))
        return
    atomic_json(status_path, status)
    torch.set_num_threads(min(4, os.cpu_count() or 1))
    try:
        processor = AutoImageProcessor.from_pretrained(config['model_directory'], local_files_only=True)
        model = AutoModelForImageClassification.from_pretrained(config['model_directory'], local_files_only=True)
        label_ids = {str(label).lower(): int(index) for index, label in model.config.id2label.items()}
        if 'ai' not in label_ids or 'hum' not in label_ids:
            raise ValueError('Expected detector labels ai and hum')
        while True:
            if not enabled():
                status['status'] = 'disabled'
                atomic_json(status_path, status)
                return
            pending = [p for p in directory.glob('*.json') if len(p.stem) == 64 and not (scores / p.name).exists()]
            status.update(status='scoring' if pending else 'ready', pending=len(pending), updated=time.time())
            atomic_json(status_path, status)
            for path in pending:
                if not enabled():
                    status['status'] = 'disabled'
                    atomic_json(status_path, status)
                    return
                started = time.monotonic()
                record = json.loads(path.read_text(encoding='utf-8'))
                image_scores = []
                try:
                    for image in record['images']:
                        image_path = (output / image['subfolder'] / image['filename']).resolve()
                        if not image_path.is_relative_to(directory):
                            raise ValueError('Image path must stay inside Krea2 Lab output')
                        with Image.open(image_path) as source:
                            inputs = processor(images=source.convert('RGB'), return_tensors='pt')
                        probabilities = model(**inputs).logits.detach().softmax(dim=-1)[0]
                        image_scores.append(dict(filename=image['filename'],
                            ai=float(probabilities[label_ids['ai']]), real=float(probabilities[label_ids['hum']])))
                    result = dict(model=config['model_id'], revision=config['revision'],
                        ai=sum(s['ai'] for s in image_scores) / len(image_scores),
                        real=sum(s['real'] for s in image_scores) / len(image_scores), images=image_scores,
                        seconds=round(time.monotonic() - started, 3), scored_at=time.time())
                except Exception as error:
                    result = dict(error=str(error), model=config['model_id'])
                atomic_json(scores / path.name, result)
                status['scored'] += 1
                status.update(updated=time.time(), last_trial=path.stem)
                atomic_json(status_path, status)
            if args.once or (args.parent and not psutil.pid_exists(args.parent)):
                break
            time.sleep(3)
        status.update(status='finished', pending=0, updated=time.time())
        atomic_json(status_path, status)
    except Exception as error:
        status.update(status='error', error=str(error), updated=time.time())
        atomic_json(status_path, status)
        raise


if __name__ == '__main__':
    main()
