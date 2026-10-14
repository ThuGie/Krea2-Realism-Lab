const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('comfyui_krea2_lab/web/index.html','utf8').split('<script src=')[0];
const script=fs.readFileSync('comfyui_krea2_lab/web/help.js','utf8');
const elements={helpTitle:{},helpText:{},helpDialog:{showModal(){this.open=true},close(){this.open=false}},closeHelp:{}};
let click;
const context=vm.createContext({document:{addEventListener(type,callback){click=callback},getElementById:id=>elements[id]}});
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
elements.closeHelp.onclick();assert(!elements.helpDialog.open);
console.log('Every option has an accessible help button and explanation.');
