const $=id=>document.getElementById(id);
let frame=null,busy=false,epoch=0;
const savedMode=sessionStorage.getItem('unison.synthetic.intent.mode');if(['visual','screenless'].includes(savedMode))$('mode').value=savedMode;
const status=text=>{$('status').textContent=text;};
function controls(){for(const control of document.querySelectorAll('button,input,select'))control.disabled=busy;}
function clear(){frame=null;$('intent').hidden=true;$('description').textContent='';$('terms').textContent='';$('choices').replaceChildren();$('spoken').textContent='';}
function render(value){frame=value;sessionStorage.setItem('unison.synthetic.intent',JSON.stringify({collection:value.collection,resource:value.resource}));$('choices').replaceChildren();$('intent').hidden=!value.visual;
 if(value.visual){$('description').textContent=value.visual.description;$('terms').textContent=value.visual.permission_summary||'';
 for(const choice of value.visual.choices){const button=document.createElement('button');button.textContent=choice.replaceAll('_',' ');button.onclick=()=>respond(choice);$('choices').append(button);}}
 $('spoken').textContent=value.audio_text||'Spoken representation unavailable; visual controls remain available.';status('Current intent state: '+value.state);}
async function run(body){if(busy)return;busy=true;const mine=++epoch;controls();status('Request in progress. Choices are temporarily unavailable.');try{
 const token=sessionStorage.getItem('unisonAccessToken');if(!token)throw Error('Sign in through Unison first.');
 const response=await fetch('/synthetic-intent',{method:'POST',cache:'no-store',credentials:'omit',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({...body,mode:$('mode').value})});
 const value=await response.json();if(mine!==epoch||document.hidden)return;if(!response.ok)throw Error(value.detail||'Interaction unavailable.');render(value);
 }catch(error){if(mine===epoch){clear();status(error.message);$('status').focus();}}finally{busy=false;controls();}}
function respond(command){if(!frame)return status('Refresh current state before choosing.');return run({operation:'respond',frame,command});}
$('start').onclick=()=>run({operation:'start',mechanism:$('mechanism').value});
function refresh(){const saved=sessionStorage.getItem('unison.synthetic.intent');if(!saved)return status('Begin a synthetic source review first.');return run({operation:'current',...JSON.parse(saved)});}
$('refresh').onclick=refresh;$('mode').onchange=()=>{sessionStorage.setItem('unison.synthetic.intent.mode',$('mode').value);refresh();};
$('send').onclick=()=>{const command=$('command').value.trim().toLowerCase().replaceAll(' ','_');$('command').value='';respond(command);};
$('command').onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();$('send').click();}};
document.addEventListener('visibilitychange',()=>{epoch++;clear();if(!document.hidden&&!busy)refresh();});
window.addEventListener('pageshow',()=>{clear();if(sessionStorage.getItem('unison.synthetic.intent'))refresh();});
