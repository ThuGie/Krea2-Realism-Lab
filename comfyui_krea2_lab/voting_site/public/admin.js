let csrf='';
const $=id=>document.getElementById(id);
async function api(action,body){const response=await fetch('api.php?action='+action,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(body)});const data=await response.json();if(!response.ok)throw Error(data.error);return data}
function show(admin){$('login').hidden=admin;$('downloads').hidden=!admin}
$('login').onsubmit=async event=>{event.preventDefault();try{await api('admin-login',{key:$('key').value});$('key').value='';$('message').textContent='Signed in.';show(true)}catch(error){$('message').textContent=error.message}};
$('logout').onclick=async()=>{try{await api('admin-logout',{});show(false);$('message').textContent='Signed out.'}catch(error){$('message').textContent=error.message}};
api('meta').then(data=>{csrf=data.csrf;show(data.admin)}).catch(error=>{$('message').textContent=error.message});

const help={login:'Enter the private admin access key supplied in HOSTING.md inside your exported ZIP. It authorizes access to downloads for this export only; do not share it with voters.',csv:'Downloads each voted image with its public vote count, average score and generation settings. Suitable for spreadsheets. Local review scores are not included in public averages.',json:'Downloads all exported trials, run metadata and public votes, including hashed anonymous voter identifiers. Keep this backup private. Backing up private/voting.sqlite also preserves the live database.',logout:'Ends admin access in this browser session. Community voting remains available.'};
document.addEventListener('click',event=>{const button=event.target.closest('[data-help]');if(button){$('helpText').textContent=help[button.dataset.help];$('helpDialog').showModal()}});
$('closeHelp').onclick=()=>$('helpDialog').close();
