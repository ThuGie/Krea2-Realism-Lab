const $ = id => document.getElementById(id);
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
let csrf = '', after = -1, records = [];
async function api(action, body, query = '') {
  const response = await fetch('api.php?action=' + action + query, body === undefined ? {} : {
    method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':csrf}, body:JSON.stringify(body)
  });
  const data = await response.json();
  if (!response.ok) throw Error(data.error || 'Request failed');
  return data;
}
function preview(url) { $('zoom').querySelector('img').src = url; $('zoom').showModal(); }
function render() {
  $('gallery').innerHTML = records.map(record => `<article class="card" data-id="${record.id}"><img loading="lazy" src="${escapeHtml(record.images[0])}" alt="Image to review"><div class="content"><strong>Image ${record.id.slice(0,8)}</strong><details><summary>Prompt</summary><p>${escapeHtml(record.prompt)}</p></details>${$('blind').checked?'':`<details><summary>Generation settings</summary><pre>${escapeHtml(JSON.stringify(record.settings,null,2))}</pre></details>`}${record.images.length>1?record.images.slice(1).map(url=>`<img loading="lazy" src="${escapeHtml(url)}" alt="Additional generated image">`).join(''):''}<div class="rating">${[1,2,3,4,5].map(score=>`<button data-score="${score}" class="${record.my_score===score?'chosen':''}" aria-label="Rate image ${score} out of 5">${score}</button>`).join('')}</div><p class="muted">${record.my_score?'Your rating: '+record.my_score+' / 5':'Not rated yet'}</p></div></article>`).join('');
}
async function load(reset=false) {
  $('more').disabled = true;
  try {
    if (reset) { after=-1; records=[]; }
    const data = await api('trials',undefined,'&after='+after+'&unrated='+($('unrated').checked?'1':'0'));
    after = data.next; records.push(...data.trials); render(); $('more').hidden=!data.more;
    $('message').textContent = records.length?'':'No more images to rate. Change the filter or view the results.';
  } finally { $('more').disabled=false; }
}
function configurationLabel(value) {
  const settings=JSON.parse(value);
  return [settings.model,settings.lora,'strength '+settings.strength,settings.sampler+'/'+settings.scheduler,settings.steps+' steps','CFG '+settings.cfg].join(' · ');
}
async function results() {
  const data=await api('results');
  $('totalVotes').textContent=data.votes+' community votes. Counts matter: a high average from very few votes is uncertain.';
  $('configurationRows').innerHTML=data.configurations.map(row=>`<tr><td>${escapeHtml(configurationLabel(row.settings))}</td><td>${Number(row.mean).toFixed(2)}</td><td>${row.votes}</td><td>${row.images}</td></tr>`).join('');
  $('winners').innerHTML=data.images.map(row=>`<article class="card"><img loading="lazy" src="${escapeHtml(JSON.parse(row.images)[0])}" alt="Community-rated image"><div class="content"><strong>${Number(row.mean).toFixed(2)} / 5 · ${row.votes} votes</strong><p>${escapeHtml(configurationLabel(row.settings))}</p></div></article>`).join('');
}
async function safely(callback) { try { await callback(); } catch(error) { $('message').textContent=error.message; } }
$('gallery').onclick=event=>safely(async()=>{
  if(event.target.tagName==='IMG') return preview(event.target.src);
  if(!event.target.dataset.score) return;
  const card=event.target.closest('.card'), record=records.find(record=>record.id===card.dataset.id);
  event.target.disabled=true;
  try {
    const data=await api('vote',{trial_id:record.id,score:Number(event.target.dataset.score)});
    record.my_score=data.score; render(); $('message').textContent='Vote saved. Thank you.';
  } finally { event.target.disabled=false; }
});
$('winners').onclick=event=>{if(event.target.tagName==='IMG')preview(event.target.src)};
$('more').onclick=()=>safely(()=>load());
$('blind').onchange=render;
$('unrated').onchange=()=>safely(()=>load(true));
$('resultsTab').onclick=()=>safely(async()=>{$('voting').hidden=true;$('results').hidden=false;await results()});
$('voteTab').onclick=()=>{$('voting').hidden=false;$('results').hidden=true};
$('closeZoom').onclick=()=>$('zoom').close();
$('closeHelp').onclick=()=>$('helpDialog').close();
const help={vote:'Returns to the image rating gallery. Your votes remain saved when switching between views.',more:'Loads the next page of up to 36 images from this exported run. Images already loaded remain visible. Use Only images I have not rated to focus on new reviews.',blind:'Hides model, LoRA and sampling labels so you can judge the image without being influenced by the configuration. The results page reveals labels.',unrated:'Shows images with no vote from this browser. Your identity is a random cookie; clearing it or using another browser creates another identity.',rating:'Rate photographic believability, not whether you like the subject. Check faces, hands, anatomy, skin texture, materials, shadows and lighting. One vote per browser per image is saved; clicking a different number updates that vote.',results:'Public votes are averaged per image and per generation configuration. All votes have equal weight. More votes and coverage across more images make comparisons more useful. Local ComfyUI reviews are never mixed into public totals.'};
document.addEventListener('click',event=>{const button=event.target.closest('[data-help]');if(button){$('helpText').textContent=help[button.dataset.help];$('helpDialog').showModal()}});
safely(async()=>{const data=await api('meta');csrf=data.csrf;$('title').textContent=data.manifest.title;$('coverage').textContent=data.manifest.trials+' images in this run';await load()});
