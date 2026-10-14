import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch


class LabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        class BadRequest(ValueError):
            def __init__(self, text):super().__init__(text)
        fake_web = types.SimpleNamespace(HTTPBadRequest=BadRequest, HTTPNotFound=FileNotFoundError,
                                         json_response=lambda v:v)
        modules = {'aiohttp': types.SimpleNamespace(web=fake_web)}
        comfy = types.ModuleType('comfy')
        for name in ['model_management', 'samplers', 'sd', 'utils']:
            module = types.ModuleType('comfy.'+name)
            setattr(comfy,name,module)
            modules['comfy.'+name]=module
        comfy.samplers.KSampler=types.SimpleNamespace(SAMPLERS=['euler'], SCHEDULERS=['normal'])
        comfy.utils.load_torch_file=Mock(return_value={})
        comfy.model_management.throw_exception_if_processing_interrupted=Mock()
        comfy.sd.load_lora_for_models=Mock(return_value=(types.SimpleNamespace(patches={'weight':[1]}),None))
        modules['comfy']=comfy
        modules['folder_paths']=types.SimpleNamespace(get_output_directory=lambda:cls.temp.name,
            get_filename_list=lambda kind:['test.safetensors'],get_full_path_or_raise=lambda *a:'test.safetensors')
        modules['nodes']=types.SimpleNamespace(CLIPTextEncode=lambda:types.SimpleNamespace(encode=lambda *a:([[]],)),
            VAEDecode=lambda:types.SimpleNamespace(decode=lambda vae,samples:(vae.decode(samples['samples']),)),
            common_ksampler=Mock(return_value=({'samples':'sample'},)),
            SaveImage=lambda:types.SimpleNamespace(save_images=lambda *a,**kw:{'ui':{'images':[{'filename':'test.png','subfolder':'krea2_lab','type':'output'}]}}))
        routes=types.SimpleNamespace(get=lambda p:lambda f:f,post=lambda p:lambda f:f)
        modules['server']=types.SimpleNamespace(PromptServer=types.SimpleNamespace(instance=types.SimpleNamespace(routes=routes)))
        cls.old={k:sys.modules.get(k) for k in modules}
        sys.modules.update(modules)
        spec=importlib.util.spec_from_file_location('lab',Path(__file__).parents[1]/'comfyui_krea2_lab/__init__.py')
        cls.lab=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.lab)
        cls.real_start_detector=staticmethod(cls.lab.start_detector)
        cls.lab.start_detector=Mock(return_value=True)
        cls.comfy=comfy

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
        for k,v in cls.old.items():
            if v is None:sys.modules.pop(k,None)
            else:sys.modules[k]=v

    def run_trial(self,lora='NONE',execution_cache=None,model=None,clip=None):
        return self.lab.Krea2LabTrial().run(model=model if model is not None else types.SimpleNamespace(patches={}),clip=clip if clip is not None else object(),
            vae=types.SimpleNamespace(decode=lambda s:'image'),latent={'samples':types.SimpleNamespace(shape=(1,4,128,128))},
            lora_name=lora,strength=.75,prompt='Photograph',trigger='',negative='',seed=42,steps=8,cfg=1,
            sampler_name='euler',scheduler='normal',experiment='Test',api_prompt={'model':'test'},execution_cache=execution_cache)

    def test_execution_cache_reuses_lora_and_conditioning_and_invalidates(self):
        cache={}
        model=types.SimpleNamespace(patches={})
        clip=object()
        encoder=Mock(return_value=([[]],))
        loader=self.comfy.utils.load_torch_file
        loader.reset_mock()
        with patch.object(self.lab.nodes,'CLIPTextEncode',return_value=types.SimpleNamespace(encode=encoder)):
            self.run_trial('test.safetensors',cache,model,clip)
            self.run_trial('test.safetensors',cache,model,clip)
            self.assertEqual(encoder.call_count,2)
            self.assertEqual(loader.call_count,1)
            self.run_trial('NONE',cache,model,clip)
            self.assertEqual(encoder.call_count,2)
            self.run_trial('test.safetensors',cache,types.SimpleNamespace(patches={}),object())
            self.assertEqual(encoder.call_count,4)
            self.assertEqual(loader.call_count,2)

    def test_records_graph_and_preserves_review(self):
        key=self.run_trial()['result'][0]
        path=self.lab.record_path(key)
        record=json.loads(path.read_text())
        self.assertEqual(record['settings']['graph'],{'model':'test'})
        async def data():return {'score':5,'notes':'Natural skin'}
        asyncio.run(self.lab.review(types.SimpleNamespace(match_info={'key':key},json=data)))
        self.run_trial()
        self.assertEqual(json.loads(path.read_text())['review']['score'],5)

    def test_matching_lora_runs(self):
        self.assertEqual(len(self.run_trial('test.safetensors')['result'][0]),64)

    def test_uses_standard_vae_decode_before_save(self):
        decoded = object()
        decoder = Mock(return_value=(decoded,))
        saver = Mock(return_value={'ui':{'images':[{'filename':'decoded.png','subfolder':'krea2_lab','type':'output'}]}})
        with patch.object(self.lab.nodes,'VAEDecode',return_value=types.SimpleNamespace(decode=decoder)), \
             patch.object(self.lab.nodes,'SaveImage',return_value=types.SimpleNamespace(save_images=saver)):
            self.run_trial()
        decoder.assert_called_once()
        self.assertIs(saver.call_args.args[0],decoded)

    def test_unmatched_lora_fails(self):
        self.comfy.sd.load_lora_for_models.return_value=(types.SimpleNamespace(patches={}),None)
        try:
            with self.assertRaisesRegex(ValueError,'No LoRA weights matched'):self.run_trial('test.safetensors')
        finally:self.comfy.sd.load_lora_for_models.return_value=(types.SimpleNamespace(patches={'weight':[1]}),None)

    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):self.lab.record_path('../secrets')

    def test_unknown_lora_rejected(self):
        with self.assertRaisesRegex(ValueError,'installed LoRA'):self.run_trial('../elsewhere')

    def test_detector_is_opt_in_and_setting_persists(self):
        path=self.lab.root()/'detector_settings.json'
        original=path.read_text() if path.exists() else None
        try:
            if path.exists():path.unlink()
            self.assertFalse(self.lab.detector_enabled())
            with patch.object(self.lab.subprocess,'Popen') as popen:
                self.assertFalse(self.real_start_detector())
                popen.assert_not_called()
            async def enable():return {'enabled':True}
            asyncio.run(self.lab.detector_settings(types.SimpleNamespace(json=enable)))
            self.assertTrue(self.lab.detector_enabled())
            async def disable():return {'enabled':False}
            asyncio.run(self.lab.detector_settings(types.SimpleNamespace(json=disable)))
            self.assertFalse(self.lab.detector_enabled())
            status=asyncio.run(self.lab.detector_status(None))
            self.assertFalse(status['enabled'])
            self.assertEqual(status['status'],'disabled')
        finally:
            if original is None:path.unlink(missing_ok=True)
            else:path.write_text(original)

    def test_eta_requires_samples_and_excludes_paused_time(self):
        state=dict(total=100,index=10,status='running',current_started_at=95,recent_seconds=[10,20,30])
        eta=self.lab.eta_fields(state,now=100)
        self.assertEqual(eta['remaining_seconds'],1795)
        self.assertEqual(eta['estimated_finish_at'],1895)
        state['status']='paused'
        self.assertEqual(self.lab.eta_fields(state,now=10000)['remaining_seconds'],1800)
        self.assertIsNone(self.lab.eta_fields(state)['estimated_finish_at'])
        state['recent_seconds']=[1]
        self.assertIsNone(self.lab.eta_fields(state)['remaining_seconds'])
        state['index']=100
        self.assertEqual(self.lab.eta_fields(state)['remaining_seconds'],0)

    def test_gallery_merges_detector_score_without_changing_reviews(self):
        key=self.run_trial()['result'][0]
        directory=self.lab.root()/'scores'
        directory.mkdir(exist_ok=True)
        (directory/(key+'.json')).write_text(json.dumps({'real':0.8,'ai':0.2}))
        stored_before=self.lab.record_path(key).read_text()
        records=asyncio.run(self.lab.trials(None))
        trial=next(t for t in records if t['id']==key)
        self.assertEqual(trial['detector']['real'],0.8)
        self.assertEqual(self.lab.record_path(key).read_text(),stored_before)

    def test_automatic_sweep_all_combinations_once_and_resume(self):
        inventory={'diffusion_models':['krea2/a.safetensors','krea2/b.safetensors','qwen.safetensors'],
                   'loras':['krea2/l1.safetensors','krea2/l2.safetensors','other.safetensors']}
        with patch.object(self.lab.folder_paths,'get_filename_list',side_effect=lambda k:inventory.get(k,[])), \
             patch.object(self.comfy.samplers.KSampler,'SAMPLERS',['euler','heun']), \
             patch.object(self.comfy.samplers.KSampler,'SCHEDULERS',['normal','simple']), \
             patch.object(self.lab.nodes,'UNETLoader',return_value=types.SimpleNamespace(load_unet=lambda *a:(object(),)),create=True), \
             patch.object(self.lab.nodes,'CLIPLoader',return_value=types.SimpleNamespace(load_clip=lambda *a,**k:(object(),)),create=True), \
             patch.object(self.lab.nodes,'VAELoader',return_value=types.SimpleNamespace(load_vae=lambda *a:(object(),)),create=True), \
             patch.object(self.lab.nodes,'EmptyLatentImage',return_value=types.SimpleNamespace(generate=lambda *a:({'samples':types.SimpleNamespace(shape=(1,4,128,128))},)),create=True), \
             patch.object(self.lab.Krea2LabTrial,'run',return_value={'result':('id',)}) as trial:
            args=dict(encoder='encoder',vae_name='vae',strengths='0.5,1',prompts='photo',seeds='42',
                      steps=8,cfg=1,width=1024,height=1024,experiment='Auto test',trigger_map='{}',negative='')
            self.lab.Krea2LabSweep().run(**args)
            self.assertEqual(trial.call_count,2*(2*2+1)*2*2)
            configs=[(c.kwargs['api_prompt']['1']['inputs']['unet_name'], c.kwargs['lora_name'],
                      c.kwargs['strength'],c.kwargs['sampler_name'],c.kwargs['scheduler']) for c in trial.call_args_list]
            self.assertEqual(len(configs),len(set(configs)))
            trial.reset_mock()
            self.lab.Krea2LabSweep().run(**args)
            trial.assert_not_called()
            fixed=dict(test_models=False,test_loras=False,test_strengths=False,test_samplers=False,
                test_schedulers=False,fixed_model='krea2/a.safetensors',fixed_lora='NONE',
                fixed_sampler='euler',fixed_scheduler='normal',include_baseline=False)
            for name, changes, expected in [
                ('samplers',dict(test_samplers=True),2),
                ('schedulers',dict(test_schedulers=True),2),
                ('models',dict(test_models=True),2),
                ('loras',dict(test_loras=True,test_strengths=True),4),
                ('strengths',dict(fixed_lora='krea2/l1.safetensors',test_strengths=True),2),
                ('steps and cfg',dict(step_values='8,12',cfg_values='1,2'),4),
            ]:
                with self.subTest(mode=name):
                    trial.reset_mock()
                    options=dict(fixed,**{})
                    options.update(changes)
                    self.lab.Krea2LabSweep().run(**dict(args,experiment='Selective '+name),**options)
                    self.assertEqual(trial.call_count,expected)
                    self.assertEqual(len({json.dumps(c.kwargs['api_prompt'],sort_keys=True) for c in trial.call_args_list}),expected)
            trial.reset_mock()
            async def disable():return dict(sampler='heun',scheduler='simple',disabled=True)
            async def enable():return dict(sampler='heun',scheduler='simple',disabled=False)
            request=types.SimpleNamespace(json=disable)
            def live_trial(**kwargs):
                asyncio.run(self.lab.set_pair(request))
                return {'result':('id',)}
            trial.side_effect=live_trial
            args['experiment']='Live exclusions test'
            try:
                self.lab.Krea2LabSweep().run(**args)
                self.assertEqual(trial.call_count,30)
                self.assertTrue(all((c.kwargs['sampler_name'],c.kwargs['scheduler'])!=('heun','simple') for c in trial.call_args_list))
                states=[json.loads(p.read_text()) for p in (self.lab.root()/'sweeps').glob('*.json')]
                state=next(s for s in states if s['configuration']['experiment']=='Live exclusions test')
                self.assertEqual(state['skipped'],10)
                self.assertEqual(state['index'],40)
                self.assertIn(('heun','simple'),self.lab.disabled_pairs())
            finally:
                asyncio.run(self.lab.set_pair(types.SimpleNamespace(json=enable)))

    def test_pending_enabled_matches_remaining_combinations(self):
        configuration=dict(models=['a','b'],loras=['x','y'],strengths=[.5,1],
            samplers=['euler','heun'],schedulers=['normal','simple'],prompts=['p','q'],seeds=[1,2])
        disabled={('euler','normal'),('heun','simple')}
        jobs=list(self.lab.itertools.product(configuration['models'],range(5),configuration['samplers'],
            configuration['schedulers'],configuration['prompts'],configuration['seeds']))
        for index in range(len(jobs)+1):
            state=dict(total=len(jobs),index=index,configuration=configuration)
            expected=sum((job[2],job[3]) not in disabled for job in jobs[index:])
            self.assertEqual(self.lab.pending_enabled(state,disabled),expected)

    def test_pair_api_rejects_unknown_names(self):
        async def data():return dict(sampler='unknown',scheduler='normal',disabled=True)
        with self.assertRaises(ValueError):
            asyncio.run(self.lab.set_pair(types.SimpleNamespace(json=data)))

    def test_pair_import_export_merge_replace_and_invalid_are_atomic(self):
        async def request(data):return data
        def imported(data):
            return asyncio.run(self.lab.import_pairs(types.SimpleNamespace(json=lambda:request(data))))
        path=self.lab.root()/'disabled_pairs.json'
        before=path.read_text() if path.exists() else '{"disabled": []}'
        try:
            imported(dict(mode='replace',disabled=[['euler','normal']]))
            exported=json.loads(json.dumps(asyncio.run(self.lab.get_pairs(None))))
            imported(dict(mode='replace',disabled=[]))
            self.assertFalse(self.lab.disabled_pairs())
            imported(exported)
            self.assertEqual(self.lab.disabled_pairs(),{('euler','normal')})
            imported(dict(disabled=[['custom_sampler','custom_scheduler'],['euler','normal']]))
            self.assertEqual(len(self.lab.disabled_pairs()),2)
            saved=path.read_text()
            with self.assertRaises(ValueError):imported(dict(mode='replace',disabled=[['malformed']]))
            self.assertEqual(path.read_text(),saved)
            async def enable_unknown():return dict(sampler='custom_sampler',scheduler='custom_scheduler',disabled=False)
            asyncio.run(self.lab.set_pair(types.SimpleNamespace(json=enable_unknown)))
            self.assertEqual(self.lab.disabled_pairs(),{('euler','normal')})
        finally:
            path.write_text(before)

    def test_sweep_failure_continues_and_pause_resumes(self):
        inventory={'diffusion_models':['krea2/m.safetensors'],'loras':['krea2/l.safetensors']}
        calls=[]
        def trial_run(**kw):
            calls.append(kw['lora_name'])
            if len(calls)==1:
                self.lab.PAUSE.set()
                raise ValueError('Unsupported sampler')
            return {'result':('id',)}
        with patch.object(self.lab.folder_paths,'get_filename_list',side_effect=lambda k:inventory.get(k,[])), \
             patch.object(self.lab.nodes,'UNETLoader',return_value=types.SimpleNamespace(load_unet=lambda *a:(object(),)),create=True), \
             patch.object(self.lab.nodes,'CLIPLoader',return_value=types.SimpleNamespace(load_clip=lambda *a,**k:(object(),)),create=True), \
             patch.object(self.lab.nodes,'VAELoader',return_value=types.SimpleNamespace(load_vae=lambda *a:(object(),)),create=True), \
             patch.object(self.lab.nodes,'EmptyLatentImage',return_value=types.SimpleNamespace(generate=lambda *a:({'samples':types.SimpleNamespace(shape=(1,4,128,128))},)),create=True), \
             patch.object(self.lab.Krea2LabTrial,'run',side_effect=trial_run):
            args=dict(encoder='encoder',vae_name='vae',strengths='0.5,1',prompts='photo',seeds='42',
                      steps=8,cfg=1,width=1024,height=1024,experiment='Pause test',trigger_map='{}',negative='')
            self.assertIn('paused: 1/3',self.lab.Krea2LabSweep().run(**args)[0])
            self.assertIn('complete: 3/3',self.lab.Krea2LabSweep().run(**args)[0])
            self.assertEqual(calls,['NONE','krea2/l.safetensors','krea2/l.safetensors'])


if __name__=='__main__':unittest.main()
