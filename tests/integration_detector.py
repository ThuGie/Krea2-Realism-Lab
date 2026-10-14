import json
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image


with tempfile.TemporaryDirectory() as output:
    root = Path(output) / 'krea2_lab'
    root.mkdir()
    key = 'a' * 64
    gradient = np.linspace(0, 255, 224, dtype=np.uint8)
    pixels = np.tile(gradient[None, :, None], (224, 1, 3))
    Image.fromarray(pixels).save(root / 'test.png')
    record = dict(id=key, images=[dict(filename='test.png', subfolder='krea2_lab', type='output')])
    (root / (key + '.json')).write_text(json.dumps(record))
    rejected_key = 'b' * 64
    (root / (rejected_key + '.json')).write_text(json.dumps(dict(id=rejected_key,
        images=[dict(filename='outside.png', subfolder='..', type='output')])))
    subprocess.run([sys.executable, str(Path(__file__).parents[1] / 'comfyui_krea2_lab/detector_worker.py'),
                    '--output', output, '--once'], check=True)
    score = json.loads((root / 'scores' / (key + '.json')).read_text())
    assert 'error' not in score, score
    assert 0 <= score['ai'] <= 1 and 0 <= score['real'] <= 1
    assert abs(score['ai'] + score['real'] - 1) < 1e-5
    rejected = json.loads((root / 'scores' / (rejected_key + '.json')).read_text())
    assert 'inside Krea2 Lab' in rejected['error'], rejected
    print('PASS: real offline CPU inference, score persistence and path containment.')
