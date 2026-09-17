// Source-level JS execution with minimal DOM; not browser visual QA.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const elements=new Map();
const ctx=vm.createContext({document:{getElementById(id){if(!elements.has(id))elements.set(id,{});return elements.get(id);}},fetch:async()=>({ok:true,json:async()=>({token:'test'})})});
vm.runInContext(fs.readFileSync('web/app.js','utf8'),ctx);
const row={id:'a',classifier_top_label:'ACCEPT',final_policy_label:'QUALIFY',classifier_top_label_probability:.8,classifier_probability_for_final_label:.1};
function validate(data){ctx.input=data;return vm.runInContext('validateReceipt(input)',ctx);}
assert.equal(validate({records:[row]}).records[0].id,'a');
const bad=[null,{}, {records:[]}, {records:[row,row]}, {records:[{...row,id:''}]}, {records:[{...row,final_policy_label:'UNKNOWN'}]}, {records:[{...row,classifier_probability_for_final_label:'0.1'}]}, {records:[{...row,classifier_top_label_probability:NaN}]}, {records:Array.from({length:1001},(_,i)=>({...row,id:String(i)}))}];
for(const value of bad)assert.throws(()=>validate(value));
ctx.input={records:[row]};vm.runInContext('prior=validateReceipt(input)',ctx);
ctx.input={records:[{id:'broken'}]};assert.throws(()=>vm.runInContext('prior=validateReceipt(input)',ctx));
assert.equal(vm.runInContext('prior.records[0].id',ctx),'a');
console.log('PASS: valid receipt accepted, malformed imports rejected, prior receipt preserved after failed import.');
