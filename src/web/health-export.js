const $ = id => document.getElementById(id);
let wid = sessionStorage.getItem('unison.synthetic.workflow');
let snapshot = sessionStorage.getItem('unison.synthetic.snapshot');
let active = false, epoch = 0, busy = false;
const status = text => { $('status').textContent = text; };
function clearFacts() { $('facts').replaceChildren(); $('summary-text').replaceChildren(); $('review').hidden = true; $('summary').hidden = true; }
function controls() {
  $('controls').hidden = !wid;
  for (const id of ['cancel','export-file','consent','summarize','backup','revoke','delete']) $(id).disabled = busy;
  $('restore').disabled = !snapshot || busy; $('import').disabled = active || busy;
  $('main').setAttribute('aria-busy', String(busy));
}
function current(mine) { if (mine !== epoch || document.hidden) throw new Error('View interrupted. An already sent request may have completed. Return and check current state before continuing.'); }
async function request(path, method='GET', body) {
  const mine = epoch;
  current(mine);
  const token = sessionStorage.getItem('unisonAccessToken');
  if (!token) throw new Error('Sign in through the main Unison surface before importing.');
  const response = await fetch(path, {method, cache:'no-store', credentials:'omit',
    headers:{Authorization:`Bearer ${token}`, 'Content-Type':'application/json'}, ...(body === undefined ? {} : {body:JSON.stringify(body)})});
  const data = await response.json();
  current(mine);
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'The workflow is unavailable.');
  return data;
}
const path = () => `/health-workflows/${encodeURIComponent(wid)}`;
function render(data) {
  clearFacts();
  if(data.state !== 'review') return;
  $('review-note').textContent = `${data.filename}: ${data.records.length} facts; ${data.duplicates_removed} identical duplicate rows removed. Each source link opens the exact extracted row.`;
  for (const record of data.records) {
    const f=record.facts, p=record.provenance;
    const item=document.createElement('article'); item.id=`fact-${record.record_id}`; item.tabIndex=-1;
    const title=document.createElement('h3'); title.textContent=`${f.metric === 'steps' ? 'Steps' : 'Sleep duration'} · ${f.source_day}`;
    const text=document.createElement('p'); text.textContent=`${f.value === null ? 'Unknown: '+f.missing_reason : f.value+' '+f.unit}. ${f.kind}; quality: ${f.quality}; revision ${f.revision}. ${f.original_timezone}.`;
    const details=document.createElement('details'), label=document.createElement('summary'); label.textContent='Inspect original source row';
    const source=document.createElement('p'); source.textContent=`${data.filename} ${p.row_pointer}. Source: ${f.source}; device: ${f.device}; method: ${f.method}. Interval: ${f.measured_start} to ${f.measured_end}.`;
    const raw=document.createElement('pre'); raw.textContent=JSON.stringify(f.original_payload,null,2);
    const hash=document.createElement('p'); hash.textContent=`Source SHA-256: ${p.source_sha256}. Parser: ${p.parser_version}. Fact SHA-256: ${p.fact_sha256}.`;
    details.append(label,source,raw,hash); item.append(title,text,details); $('facts').append(item);
  }
  for(const entry of data.summary) {
    const p=document.createElement('p'); p.append(document.createTextNode(entry.text+' '));
    for(const [i,id] of entry.record_ids.entries()) { const link=document.createElement('a'); link.href=`#fact-${id}`; link.textContent=`Source measurement ${i+1}`; p.append(link,document.createTextNode(' ')); }
    $('summary-text').append(p);
  }
  $('review').hidden=false;
}
async function refresh() { const mine=epoch; const data=await request(path()); current(mine); render(data); active=true; controls(); return data; }
async function run(action) {
  if(busy) { status('A request is in progress. Wait for completion before choosing another action.'); return; } busy=true; epoch++; controls(); status('Request in progress. Controls are temporarily unavailable until it completes.');
  try { await action(); } catch(error) { clearFacts(); active=false; status(error.message); $('status').focus(); }
  finally { busy=false; controls(); }
}
$('import').onclick=()=>run(async()=>{
  const mine=epoch;
  const file=$('export-file').files[0];
  if(!file || !$('consent').checked) throw new Error('Choose one synthetic JSON export and permit its use before uploading.');
  if(file.size>1048576 || !file.size) throw new Error('Choose a nonempty JSON export no larger than 1 MiB.');
  const bytes=new Uint8Array(await file.arrayBuffer());
  const sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(n=>n.toString(16).padStart(2,'0')).join('');
  current(mine);
  const consent=await request('/health-workflows','POST',{filename:file.name,sha256:sha,size_bytes:bytes.length,confirmed:true});
  wid=consent.workflow_id; snapshot=null; sessionStorage.setItem('unison.synthetic.workflow',wid); sessionStorage.removeItem('unison.synthetic.snapshot');
  let binary=''; for(const byte of bytes) binary+=String.fromCharCode(byte);
  try { await request(path()+'/upload','POST',{content_b64:btoa(binary)}); }
  finally { bytes.fill(0); binary=''; $('export-file').value=''; $('consent').checked=false; }
  await refresh(); status('Import validated. Review your source-linked facts, then read the summary.'); $('review-title').focus();
});
$('cancel').onclick=()=>{ if(busy) return; $('export-file').value=''; $('consent').checked=false; status('Selection cleared. This does not cancel an earlier import or remove retained data.'); };
$('summarize').onclick=()=>run(async()=>{ await refresh(); $('summary').hidden=false; $('summary-title').focus(); status('Summary ready. Each measurement links to its source; missing information remains unknown.'); });
$('backup').onclick=()=>run(async()=>{ const result=await request(path()+'/backup','POST',{}); snapshot=result.snapshot_id; sessionStorage.setItem('unison.synthetic.snapshot',snapshot); status('Encrypted workflow backup saved. The authority ledger is excluded.'); });
async function terminate(mode) { clearFacts(); active=false; const result=await request(path()+(mode==='revoke'?'/revoke':''),mode==='revoke'?'POST':'DELETE',mode==='revoke'?{}:undefined); status(`Permission ${result.state}. Current facts and saved snapshots removed. Older restored data remains unavailable.`); $('status').focus(); }
$('revoke').onclick=()=>run(()=>terminate('revoke'));
$('delete').onclick=()=>run(()=>terminate('delete'));
$('restore').onclick=()=>run(async()=>{ clearFacts(); const result=await request(path()+'/restore','POST',{snapshot_id:snapshot}); if(result.unavailable) { active=false; status('Restore blocked: revoked or deleted data remains unavailable.'); $('status').focus(); } else { await refresh(); status('Backup restored under current permission. Review the facts again.'); } });
async function checkCurrent() { if(!wid || busy || document.hidden) return; await run(async()=>{ await refresh(); status('Current permission checked. Review the facts before continuing.'); }); }
window.addEventListener('pageshow',()=>{ clearFacts(); checkCurrent(); });
document.addEventListener('visibilitychange',()=>{ epoch++; clearFacts(); if(!document.hidden) checkCurrent(); });
controls();
