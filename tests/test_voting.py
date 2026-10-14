import base64
from contextlib import closing
import hashlib
import http.cookiejar
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sqlite3
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import zipfile

SOURCE = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location('voting_export', SOURCE / 'comfyui_krea2_lab/voting_export.py')
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWQAAAABJRU5ErkJggg==')


def fixture(output):
    lab = output / 'krea2_lab'
    lab.mkdir()
    configuration = dict(models=['krea2/model.safetensors'],loras=['krea2/lora.safetensors'],strengths=[.5],
        samplers=['euler'],schedulers=['simple','karras'],prompts=['A photographic portrait'],seeds=[42],
        encoder='qwen.safetensors',vae='vae.safetensors',width=64,height=64,steps=8,cfg=1,
        experiment='Community test',negative='',triggers={})
    run = dict(id='f'*64,configuration=configuration,status='running',succeeded=3,total=4)
    for letter, lora, scheduler, experiment in [
        ('a','NONE','simple','Community test'),('b','krea2/lora.safetensors','simple','Community test'),
        ('c','krea2/lora.safetensors','karras','Community test'),('d','NONE','simple','Different run'),
        ('e','NONE','simple','Community test')]:
        key=letter*64
        graph={'1':{'inputs':{'unet_name':configuration['models'][0]}},
            '2':{'inputs':{'clip_name':configuration['encoder']}},'3':{'inputs':{'vae_name':configuration['vae']}},
            '4':{'inputs':{'width':64,'height':64}}}
        trial=dict(id=key,settings=dict(lora=lora,strength=0 if lora=='NONE' else .5,sampler='euler',
            scheduler=scheduler,prompt=configuration['prompts'][0],seed=42,steps=8,cfg=1,trigger='',negative='',
            experiment=experiment,graph=graph),images=[dict(subfolder='krea2_lab',filename=key+'.png',type='output')],
            review={'score':5,'notes':'PRIVATE LOCAL NOTE'})
        (lab/(key+'.json')).write_text(json.dumps(trial))
        if letter!='e':(lab/(key+'.png')).write_bytes(PNG)
    return run


class VotingExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output=Path(self.temporary.name)
        self.run=fixture(self.output)

    def unpack(self, **options):
        archive=exporter.build_voting_export(self.output,self.run,[('euler','karras')],**options)
        target=self.output/('site-'+str(len(list(self.output.glob('site-*')))))
        with zipfile.ZipFile(archive) as bundle:bundle.extractall(target)
        return target

    def test_snapshot_is_run_scoped_and_private_reviews_are_opt_in(self):
        target=self.unpack()
        for name in ['public/index.html','public/api.php','public/app.js','public/style.css','private/voting.sqlite','private/config.php','HOSTING.md']:
            self.assertTrue((target/name).is_file(),name)
        with closing(sqlite3.connect(target/'private/voting.sqlite')) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM trials').fetchone()[0],2)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM votes').fetchone()[0],0)
            rows=db.execute('SELECT settings,local_review FROM trials').fetchall()
            self.assertTrue(all(review is None for _,review in rows))
            self.assertTrue(all('graph' not in json.loads(settings) for settings,_ in rows))
        self.assertEqual(json.loads((target/'manifest.json').read_text())['missing_images'],1)
        second=self.unpack(include_disabled=True,include_reviews=True)
        with closing(sqlite3.connect(second/'private/voting.sqlite')) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM trials').fetchone()[0],3)
            self.assertIn('PRIVATE LOCAL NOTE',db.execute('SELECT local_review FROM trials LIMIT 1').fetchone()[0])
        self.assertNotEqual((target/'private/config.php').read_text(),(second/'private/config.php').read_text())

    def test_export_rejects_image_path_traversal(self):
        path=self.output/'krea2_lab'/('a'*64+'.json')
        record=json.loads(path.read_text());record['images'][0]['subfolder']='../'
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,'inside Krea2 Lab'):
            self.unpack()

    def test_php_site_voting_admin_exports_and_csrf(self):
        php=os.environ.get('KREA_PHP') or shutil.which('php')
        portable=SOURCE/'.tools/php/php.exe'
        if not php and portable.is_file():php=str(portable)
        if not php:self.skipTest('PHP is not installed; export structure tests still run')
        target=self.unpack()
        arguments=[php]
        if os.name=='nt' and (Path(php).parent/'ext/php_pdo_sqlite.dll').exists():
            arguments+=['-n','-d','extension_dir='+str(Path(php).parent/'ext'),'-d','extension=pdo_sqlite']
        for path in (target/'public').glob('*.php'):
            subprocess.run(arguments+['-l',str(path)],check=True,capture_output=True)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        log=(target/'server.log').open('wb');self.addCleanup(log.close)
        server=subprocess.Popen(arguments+['-S',f'127.0.0.1:{port}','-t',str(target/'public')],stdout=log,stderr=log)
        def stop():
            server.terminate();server.wait(timeout=10)
        self.addCleanup(stop)
        base=f'http://127.0.0.1:{port}/'
        client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        def request(action,body=None,csrf=None,opener=client):
            headers={}
            if body is not None:headers={'Content-Type':'application/json','X-CSRF-Token':csrf or ''}
            req=urllib.request.Request(base+'api.php?action='+action,
                data=json.dumps(body).encode() if body is not None else None,headers=headers)
            try:
                with opener.open(req,timeout=10) as response:return response.status,response.read()
            except urllib.error.HTTPError as error:
                with error:return error.code,error.read()
        for attempt in range(60):
            try:
                status,raw=request('meta')
                if status==200:break
                self.fail(raw.decode())
            except urllib.error.URLError:time.sleep(.1)
        else:self.fail('PHP server did not start')
        token=json.loads(raw)['csrf']
        with client.open(base) as response:self.assertEqual(response.status,200)
        self.assertEqual(request('export-json')[0],403)
        self.assertEqual(request('vote',{'trial_id':'a'*64,'score':5})[0],403)
        self.assertEqual(request('vote',{'trial_id':'a'*64,'score':5},token)[0],200)
        self.assertEqual(request('vote',{'trial_id':'a'*64,'score':3},token)[0],200)
        self.assertEqual(request('vote',{'trial_id':'a'*64,'score':6},token)[0],400)
        self.assertEqual(request('vote',{'trial_id':'0'*64,'score':4},token)[0],404)
        other=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        _,raw=request('meta',opener=other);other_token=json.loads(raw)['csrf']
        self.assertEqual(request('vote',{'trial_id':'a'*64,'score':5},other_token,other)[0],200)
        _,raw=request('results');results=json.loads(raw)
        self.assertEqual(results['votes'],2)
        self.assertEqual(float(results['images'][0]['mean']),4)
        _,raw=request('trials');trials=json.loads(raw)['trials']
        self.assertEqual(next(t for t in trials if t['id']=='a'*64)['my_score'],3)
        key=re.search(r'Admin access key: `([^`]+)`',(target/'HOSTING.md').read_text()).group(1)
        self.assertEqual(request('admin-login',{'key':'wrong'},token)[0],403)
        self.assertEqual(request('admin-login',{'key':key},token)[0],200)
        status,raw=request('export-json');backup=json.loads(raw)
        self.assertEqual(status,200);self.assertEqual(len(backup['votes']),2)
        self.assertEqual(request('export-csv')[0],200)
        self.assertEqual(request('admin-logout',{},token)[0],200)
        self.assertEqual(request('export-json')[0],403)
        try:
            with client.open(base+'private/voting.sqlite') as response:
                self.assertFalse(response.read().startswith(b'SQLite format 3'))
        except urllib.error.HTTPError as error:
            with error:self.assertEqual(error.code,404)


if __name__=='__main__':unittest.main()
