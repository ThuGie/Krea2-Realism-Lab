const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('comfyui_krea2_lab/web/index.html','utf8').replace(/\r\n/g,'\n');
const script=fs.readFileSync('comfyui_krea2_lab/web/help.js','utf8').replace(/\r\n/g,'\n');
const elements={helpTitle:{},helpText:{},helpDialog:{showModal(){this.open=true},close(){this.open=false}},closeHelp:{}};
assert.equal(html.split('<script id="optionHelpScript">\n')[1].split('</script>')[0],script);
assert(!html.includes('src="/krea2-lab/help.js"'));
elements.optionTooltip={style:{},matches(){return !!this.open},showPopover(){this.open=true},hidePopover(){this.open=false},getBoundingClientRect(){return {width:300,height:120}}};
const handlers={};let click;
const context=vm.createContext({window:{innerWidth:800,innerHeight:600},document:{addEventListener(type,callback){handlers[type]=callback;if(type==='click')click=callback},getElementById:id=>elements[id]}});
vm.runInContext(script,context);
const keys=vm.runInContext('Object.keys(OPTION_HELP)',context);
for(const match of html.matchAll(/<(?:input|select|textarea|button)\b[^>]*\bid="([^"]+)"[^>]*>/g)){
  const id=match[1];if(['pairsFile','closeHelp'].includes(id))continue;
  assert(keys.includes(id),'Missing help text for '+id);
  assert(html.includes('data-help="'+id+'"'),'Missing help button for '+id);
  click({target:{closest:()=>({dataset:{help:id}})},preventDefault(){},stopPropagation(){}});
  assert(elements.helpText.textContent.length>40,'Unhelpful explanation for '+id);
}
assert(elements.helpDialog.open);
const button={dataset:{help:'sort'},setAttribute(){},getBoundingClientRect(){return {left:750,top:500,bottom:520}}};
handlers.pointerover({target:{closest:()=>button}});
assert(elements.optionTooltip.open);assert(elements.optionTooltip.textContent.includes('Sort results'));
assert.equal(elements.optionTooltip.style.left,'492px');
handlers.pointerout({target:{closest:()=>button}});assert(!elements.optionTooltip.open);
handlers.focusin({target:{closest:()=>button}});assert(elements.optionTooltip.open);
handlers.keydown({key:'Escape'});assert(!elements.optionTooltip.open);
elements.closeHelp.onclick();assert(!elements.helpDialog.open);
console.log('Every option has an accessible help button and explanation.');
