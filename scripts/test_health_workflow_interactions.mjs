import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {webcrypto} from 'node:crypto';
const source=fs.readFileSync(new URL('../src/web/health-export.js',import.meta.url),'utf8');
function fixture(workflow=null) {
 const elements=new Map();
 const element=()=>({disabled:false,hidden:false,checked:true,value:'',files:[{name:'sample.json',size:2,arrayBuffer:async()=>new Uint8Array([123,125]).buffer}],textContent:'',replaceChildren(){},append(){},focus(){},setAttribute(){}});
 const get=id=>{if(!elements.has(id))elements.set(id,element());return elements.get(id);};
 const values=new Map([['unisonAccessToken','synthetic'],['unison.synthetic.workflow',workflow]]), calls=[], events={};
 const context=vm.createContext({document:{getElementById:get,hidden:false,createElement:element,createTextNode:t=>t,addEventListener:(k,f)=>events[k]=f},window:{addEventListener:(k,f)=>events[k]=f},sessionStorage:{getItem:k=>values.get(k),setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)},crypto:webcrypto,Uint8Array,btoa:s=>Buffer.from(s,'binary').toString('base64'),fetch:(url,options)=>new Promise(resolve=>calls.push({url,options,resolve:data=>resolve({ok:true,json:async()=>data})}))});
 vm.runInContext(source,context);
 return {get,calls,events,context};
}
const tick=()=>new Promise(resolve=>setTimeout(resolve,10));
const review={state:'review',filename:'sample.json',records:[],summary:[],duplicates_removed:0};
{
 const f=fixture();const pending=f.get('import').onclick();await tick();
 assert.equal(f.calls.length,1);
 for(const id of ['cancel','export-file','consent','import','revoke','delete'])assert.equal(f.get(id).disabled,true,`${id} must be honestly disabled during consent`);
 f.calls[0].resolve({workflow_id:'test'});await tick();assert.equal(f.calls[1].url,'/health-workflows/test/upload');
 f.calls[1].resolve({});await tick();f.calls[2].resolve(review);await pending;
 assert.equal(f.get('cancel').disabled,false);
 f.get('cancel').onclick();assert.match(f.get('status').textContent,/Selection cleared/);
}
for(const mode of ['revoke','delete']) {
 const f=fixture('test');const pending=f.get('summarize').onclick();await tick();
 assert.equal(f.get(mode).disabled,true,`${mode} must be disabled while brief is pending`);
 f.calls[0].resolve(review);await pending;
 assert.equal(f.get(mode).disabled,false);
 const terminal=f.get(mode).onclick();await tick();assert.equal(f.calls[1].options.method,mode==='revoke'?'POST':'DELETE');
 f.calls[1].resolve({state:mode==='revoke'?'revoked':'deleted'});await terminal;
 assert.equal(f.get('summary').hidden,true);
}
{
 const f=fixture('test');const pending=f.get('summarize').onclick();await tick();
 f.context.document.hidden=true;f.events.visibilitychange();f.calls[0].resolve(review);await pending;
 assert.equal(f.get('summary').hidden,true,'late brief must not display after visibility invalidation');
}
{
 const f=fixture();const pending=f.get('import').onclick();await tick();
 f.context.document.hidden=true;f.events.visibilitychange();f.calls[0].resolve({workflow_id:'test'});await pending;
 assert.equal(f.calls.length,1,'invalidated consent continuation must not upload');
}
{
 const f=fixture('test');vm.runInContext("snapshot='backup'; controls();",f.context);
 const pending=f.get('restore').onclick();await tick();
 for(const id of ['cancel','import','revoke','delete','restore']) assert.equal(f.get(id).disabled,true);
 f.calls[0].resolve({unavailable:false});await tick();
 f.context.document.hidden=true;f.events.visibilitychange();f.calls[1].resolve(review);await pending;
 assert.equal(f.get('review').hidden,true,'late restore review must stay cleared');
 assert.equal(f.get('revoke').disabled,false);
}
console.log('Delayed health workflow interactions passed');
