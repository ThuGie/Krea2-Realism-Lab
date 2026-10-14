"""Read-only demo of the real UI for documentation screenshots.

Run: python tools/screenshot_demo.py, then open http://127.0.0.1:8198/krea2-lab
Uses synthetic records and illustrative SVG thumbnails. Never connects to ComfyUI.
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import json

WEB = Path(__file__).resolve().parents[1] / 'comfyui_krea2_lab' / 'web'
CATALOG = dict(krea_models=['krea2/base.safetensors', 'krea2/turbo.safetensors'],
    krea_loras=['krea2/natural-light.safetensors', 'krea2/texture.safetensors', 'krea2/candid.safetensors'],
    encoders=['qwen3vl_4b_fp8_scaled.safetensors'], vaes=['qwen_image_vae.safetensors'],
    samplers=['euler', 'heun', 'dpmpp_2m', 'res_2m_ode'], schedulers=['simple', 'normal', 'karras'])
TRIALS = [dict(id=f'{i:064x}', seconds=round(24.8+i*1.7, 1),
    settings=dict(experiment='Natural light study', lora=CATALOG['krea_loras'][i % 3],
        strength=[.5,.75,1][i % 3], sampler=CATALOG['samplers'][i % 4], scheduler='simple',
        seed=42, steps=8, cfg=1, prompt='Mountain lake at sunrise, natural light, clear reflections.',
        graph={'1': {'inputs': {'unet_name': 'krea2/base.safetensors'}}}),
    images=[dict(filename=f'demo-{i}.svg', subfolder='demo', type='output')],
    review=dict(score=[4,5,3,0][i % 4], notes='')) for i in range(12)]


def thumbnail(index):
    skies = [('#879ea6','#e9cba5','#516a71'),('#a7b8ba','#f4dfb5','#617b80'),
             ('#9babb9','#ead9c9','#596c80')]
    sky, glow, ridge = skies[index % 3]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 700">
    <defs><linearGradient id="sky" x2="0" y2="1"><stop stop-color="{sky}"/><stop offset="1" stop-color="{glow}"/></linearGradient>
    <linearGradient id="lake" x2="0" y2="1"><stop stop-color="{sky}"/><stop offset="1" stop-color="#263d4a"/></linearGradient></defs>
    <rect width="700" height="700" fill="url(#sky)"/><circle cx="470" cy="210" r="49" fill="#fff3d6" opacity=".8"/>
    <path d="M0 410L170 215L335 395L490 278L700 425V500H0Z" fill="{ridge}"/>
    <path d="M118 274L170 215L230 281L188 263L169 271L148 258Z" fill="#e6e9e4" opacity=".8"/>
    <path d="M0 425L90 360L250 440L420 370L700 442V520H0Z" fill="#334f59"/>
    <rect y="470" width="700" height="230" fill="url(#lake)"/>
    <path d="M0 470L170 625L335 485L490 595L700 480V470Z" fill="{ridge}" opacity=".35"/>
    <path d="M0 545Q110 520 185 565L120 700H0Z" fill="#1e333b"/>
    <g stroke="#d9d7c5" opacity=".3"><path d="M300 535H555M240 566H490M355 610H610M180 655H470"/></g>
    <text x="28" y="45" fill="#fff" font-family="sans-serif" font-size="15" letter-spacing="3">ILLUSTRATIVE DEMO</text></svg>'''.encode()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        route = url.path
        mime = 'application/json; charset=utf-8'
        data = {
            '/krea2-lab/catalog': CATALOG,
            '/krea2-lab/trials': TRIALS,
            '/krea2-lab/pairs': {'disabled': [['heun','karras']]},
            '/krea2-lab/detector-status': {'enabled': False},
            '/krea2-lab/runs': [dict(id='f'*64,experiment='Natural light study',status='paused',generated=12)],
            '/krea2-lab/sweep-status': dict(total=24,index=12,succeeded=12,failed=0,skipped=0,
                status='paused',remaining_seconds=None,timing_samples=12),
        }.get(route)
        if data is not None:
            body = json.dumps(data).encode()
        elif route in ('/krea2-lab', '/krea2-lab/'):
            body = (WEB/'index.html').read_text(encoding='utf-8').replace(
                'LOCAL EXPERIMENT STUDIO / KREA2', 'KREA2 REALISM LAB / DEMO WORKSPACE').encode()
            mime = 'text/html; charset=utf-8'
        elif route == '/krea2-lab/help.js':
            body = (WEB/'help.js').read_bytes()
            mime = 'text/javascript; charset=utf-8'
        elif route == '/view':
            name = parse_qs(url.query).get('filename',['demo-0.svg'])[0]
            body = thumbnail(int(name.removeprefix('demo-').removesuffix('.svg')))
            mime = 'image/svg+xml'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type',mime)
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    print('Read-only demo: http://127.0.0.1:8198/krea2-lab', flush=True)
    HTTPServer(('127.0.0.1',8198),Handler).serve_forever()
