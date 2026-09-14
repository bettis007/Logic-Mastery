// Executes application action coordination with a minimal DOM stub, not a browser.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const elements=new Map();
const context=vm.createContext({document:{getElementById(id){if(!elements.has(id))elements.set(id,{});return elements.get(id);}},fetch:async()=>({ok:true,json:async()=>({token:'test'})}),console});
vm.runInContext(fs.readFileSync('web/app.js','utf8'),context);
(async()=>{
 await new Promise(resolve=>setImmediate(resolve));
 let release;context.pending=new Promise(resolve=>{release=resolve;});
 const running=vm.runInContext('action(async()=>{await pending;})',context);
 for(const id of ['demo','demo-labels','features-file','labels-file','prior-file','features'])assert.equal(elements.get(id).disabled,true);
 assert.equal(vm.runInContext('busy',context),true);
 await vm.runInContext('action(async()=>{throw Error("overlap executed");})',context);
 assert.equal(vm.runInContext('busy',context),true);
 assert.notEqual(elements.get('status').textContent,'overlap executed');
 release();await running;
 assert.equal(vm.runInContext('busy',context),false);
 assert.equal(elements.get('demo').disabled,false);
 await vm.runInContext('action(async()=>{throw Error("expected failure");})',context);
 assert.equal(vm.runInContext('busy',context),false);
 assert.equal(elements.get('status').textContent,'expected failure');
 console.log('PASS: overlapping actions ignored; mutation controls locked; success/error paths unlock.');
})().catch(e=>{console.error(e);process.exitCode=1;});
