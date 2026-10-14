import json
from pathlib import Path
inputs = {
 'encoder': 'qwen3vl_4b_fp8_scaled.safetensors', 'vae_name': 'qwen_image_vae.safetensors',
 'strengths': '0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2',
 'prompts': 'Candid photograph of an adult woman at a cafe window, natural skin texture, detailed hands holding a ceramic cup, soft daylight, unretouched photography.',
 'seeds': '42', 'steps': 8, 'cfg': 1.0, 'width': 1024, 'height': 1024,
 'experiment': 'Krea2 automatic sweep', 'trigger_map': '{}', 'negative': '',
 'test_models': True, 'test_loras': True, 'test_strengths': True,
 'test_samplers': True, 'test_schedulers': True, 'fixed_model': 'AUTO',
 'fixed_lora': 'NONE', 'fixed_strength': 0.75, 'fixed_sampler': 'AUTO',
 'fixed_scheduler': 'AUTO', 'include_baseline': True, 'step_values': '', 'cfg_values': '',
}
graph = {'1': {'class_type': 'Krea2LabSweep', 'inputs': inputs}}
workflow = dict(last_node_id=1, last_link_id=0, nodes=[dict(
 id=1, type='Krea2LabSweep', pos=[50,50], size=[680,1100], flags={}, order=0, mode=0,
 inputs=[], outputs=[dict(name='summary',type='STRING',links=None)],
 properties={'Node name for S&R': 'Krea2LabSweep'}, widgets_values=list(inputs.values()))],
 links=[], groups=[], config={}, extra={'ds': {'scale': 0.9, 'offset': [50, 50]}}, version=0.4)
Path('workflows/Krea2_Realism_Lab.api.json').write_text(json.dumps(graph, indent=2))
Path('workflows/Krea2_Realism_Lab.json').write_text(json.dumps(workflow, indent=2))
