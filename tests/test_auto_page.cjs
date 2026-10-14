const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync('comfyui_krea2_lab/web/index.html', 'utf8');
const elements = new Map();
for (const match of html.matchAll(/<([a-z0-9]+)[^>]*id="([^"]+)"[^>]*>/g)) {
  const value = match[0].match(/value="([^"]*)"/)?.[1] || '';
  elements.set(match[2], {value, checked:/\schecked(?:\s|>)/.test(match[0]), textContent: '', addEventListener() {}, options: []});
  if (match[1] === 'textarea') elements.get(match[2]).value = html.slice(match.index + match[0].length).split('</textarea>')[0];
}
const catalog = {krea_models:['krea2/a','krea2/b'],krea_loras:['krea2/l1','krea2/l2'],
  encoders:['qwen3vl_4b_fp8_scaled.safetensors'],vaes:['qwen_image_vae.safetensors'],
  samplers:['euler','heun'],schedulers:['normal','simple']};
const trial={id:'a'.repeat(64),settings:{lora:'krea2/l1',sampler:'euler',scheduler:'normal',graph:{'1':{inputs:{unet_name:'krea2/a'}}}},
  images:[{filename:'test.png',subfolder:'krea2_lab',type:'output'}],review:{},detector:{real:.85,ai:.15}};
let backendPairs=[];
const context = vm.createContext({document:{getElementById:id=>{assert(elements.has(id), 'Unknown UI element: '+id);return elements.get(id)},querySelector:()=>({addEventListener(){}})},
  fetch:async (url,options)=>({ok:true,json:async()=>{if(url.endsWith('/pairs')){if(options?.method==='POST'){const data=JSON.parse(options.body);backendPairs=backendPairs.filter(([a,b])=>a!==data.sampler||b!==data.scheduler);if(data.disabled)backendPairs.push([data.sampler,data.scheduler])}return {disabled:backendPairs}}return url.endsWith('/catalog')?catalog:url.endsWith('/trials')?[trial]:url.endsWith('/sweep-status')?{total:100,index:10,succeeded:10,failed:0,status:'running',remaining_seconds:1800,estimated_finish_at:1791914400,timing_samples:3}:{}}}),
  setInterval(){},setTimeout,console,URLSearchParams,crypto:{randomUUID:()=> 'test'},localStorage:{getItem(){return null},setItem(){}}});
vm.runInContext(html.split('<script>')[1].split('</script>')[0], context);
setTimeout(async()=>{
  assert.equal(vm.runInContext("speedCompare(2,10,'fast')",context),-8);
  assert.equal(vm.runInContext("speedCompare(2,10,'slow')",context),8);
  assert.equal(vm.runInContext("speedCompare(null,10,'slow')",context),1);
  assert.equal(vm.runInContext("speedCompare(2,undefined,'fast')",context),-1);

  elements.get('encoder').value=catalog.encoders[0];elements.get('vae').value=catalog.vaes[0];
  const graph=vm.runInContext('automaticGraph()',context);
  assert.equal(graph['1'].class_type,'Krea2LabSweep');
  assert.equal(graph['1'].inputs.seeds,'42');
  assert.equal(graph['1'].inputs.strengths.split(',').length,8);
  assert.equal('lora_name' in graph['1'].inputs,false);
  assert.equal('sampler_name' in graph['1'].inputs,false);
  assert.equal(elements.get('estimate').textContent.startsWith('136 combinations'),true);
  assert.equal(elements.get('discovered').textContent.includes('2 Krea2 models'),true);
  elements.get('fixedModel').value='krea2/a';elements.get('fixedLora').value='NONE';
  elements.get('fixedSampler').value='euler';elements.get('fixedScheduler').value='normal';
  elements.get('testMode').value='schedulers';
  vm.runInContext('applyTestMode()',context);
  const selectedGraph=vm.runInContext('automaticGraph()',context);
  assert.equal(selectedGraph['1'].inputs.test_schedulers,true);
  assert.equal(selectedGraph['1'].inputs.test_loras,false);
  assert.equal(selectedGraph['1'].inputs.test_models,false);
  assert.equal(elements.get('estimate').textContent.startsWith('2 combinations'),true);
  elements.get('testMode').value='full';vm.runInContext('applyTestMode()',context);
  assert.equal(elements.get('gallery').innerHTML.includes('Experimental classifier:'),false);
  assert.equal(elements.get('enableDetector').checked,false);
  assert.equal(elements.get('score').disabled,true);
  vm.runInContext('applyDetectorSetting(true);render()',context);
  assert.equal(elements.get('gallery').innerHTML.includes('human class 85.0%'),true);
  assert.equal(elements.get('leaders').innerHTML.includes('85.0% (1)'),true);
  elements.get('sort').value='real';
  vm.runInContext('applyDetectorSetting(false);render()',context);
  assert.equal(elements.get('sort').value,'new');
  assert.equal(elements.get('leaders').innerHTML.includes('85.0%'),false);
  assert.equal(elements.get('eta').textContent,'Estimated remaining: 30 min');
  assert.equal(elements.get('finish').textContent.includes('(Amsterdam)'),true);
  assert.match(html,/<details id="leaderboard">/);
  assert.equal(html.includes('max-height:270px;overflow:auto'),true);
  assert.equal(elements.has('disablePair'),true);
  assert.equal(elements.has('disableCurrent'),true);
  await vm.runInContext("togglePair('euler','normal',true)",context);
  assert.equal(elements.get('gallery').innerHTML.includes('test.png'),false);
  assert.equal(elements.get('leaderCount').textContent,0);
  assert.equal(elements.get('disabledPairs').innerHTML.includes('euler / normal'),true);
  assert.equal(elements.get('disabledCount').textContent,1);
  await vm.runInContext("togglePair('euler','normal',false)",context);
  assert.equal(elements.get('gallery').innerHTML.includes('test.png'),true);
  assert.equal(elements.get('leaderCount').textContent,1);
  assert.equal(elements.has('exportPairs')&&elements.has('importPairs'),true);
  console.log('Automatic page defaults, detector, ETA and disabled-pair separation passed.');
},20);
