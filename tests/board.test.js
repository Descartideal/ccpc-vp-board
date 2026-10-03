const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../board.html'),'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
const minute=60000;

class Element{
 constructor(){this.childNodes=[];this.value='';this.textContent='';this.handlers={}}
 setAttribute(k,v){this[k]=v}
 addEventListener(k,cb){this.handlers[k]=cb}
 append(...nodes){for(const node of nodes)this.childNodes.push(...(node.fragment?node.childNodes:[node]))}
 replaceChildren(...nodes){this.childNodes=[];this.append(...nodes)}
}

function board(mode,rows,elapsed){
 const nodes=new Map();
 const document={querySelector(s){if(!nodes.has(s))nodes.set(s,new Element());return nodes.get(s)},createElement(){return new Element()},createDocumentFragment(){const e=new Element();e.fragment=true;return e}};
 const start=Date.parse('2026-10-03T13:00:00+08:00');let now=start+elapsed;
 class Clock extends Date{static now(){return now}}
 const data={mode,startAt:new Date(start).toISOString(),ranklist:{contest:{title:'Regression contest',duration:[5,'h']},problems:rows[0].statuses.map((_,i)=>({alias:String.fromCharCode(65+i)})),rows}};
 const context={document,Date:Clock,setInterval(){}};vm.createContext(context);
 vm.runInContext(source.replace('/*__VP_DATA__*/',JSON.stringify(data)),context);
 return{
  nodes,
  advance(ms){now=start+ms;vm.runInContext('tick()',context)},
  row(name){return nodes.get('#body').childNodes.find(r=>r.childNodes[1]?.textContent===name)?.childNodes},
  count(p){return nodes.get('#head').childNodes[0].childNodes[p+4]?.childNodes[1]},
 };
}
const solution=(result,time)=>({result,time:[time,'min']});
const status=(result,solutions)=>({result,solutions});
function freezeRows(){return[{user:{name:'alpha'},statuses:[
 status('AC',[solution('AC',2)]),
 status('AC',[solution('WA',239),solution('AC',241),solution('WA',242)]),
 status('AC',[solution('AC',240)]),
 {result:'AC',time:[250,'min'],tries:9},
 status('AC',[solution('AC',299),solution('AC',300)]),
 ]},{user:{name:'beta'},statuses:[
 status('AC',[solution('AC',3)]),
 status('RJ',[solution('WA',239),solution('WA',241),solution('TLE',242)]),
 status('RJ',[solution('WA',240)]),
 {result:'RJ',time:[250,'min'],tries:9},
 status('RJ',[solution('WA',299),solution('WA',300)]),
 ]}]}

test('ICPC exposes every problem and public result before freeze',()=>{
 const b=board('icpc',freezeRows(),239*minute);
 assert.equal(b.nodes.get('#head').childNodes[0].childNodes.length,9);
 assert.equal(b.row('alpha')[4].className,'ac');
 assert.equal(b.row('alpha')[5].textContent,'−1');
 assert.equal(b.row('alpha')[2].textContent,'1');
 assert.equal(b.count(0).textContent,'通过 2 队');
});

test('freeze hides both correct and incorrect submissions with identical pending markers',()=>{
 const b=board('icpc',freezeRows(),239*minute);
 const before=['alpha','beta'].map(name=>b.row(name).slice(0,4).map(td=>td.textContent));
 b.advance(240*minute);
 for(const name of ['alpha','beta'])assert.equal(b.row(name)[6].textContent,'? +1');
 b.advance(241*minute);
 for(const name of ['alpha','beta'])assert.equal(b.row(name)[5].textContent,'−1 / ? +1');
 b.advance(242*minute);
 for(const name of ['alpha','beta']){
  assert.equal(b.row(name)[5].textContent,'−1 / ? +2');
  assert.equal(b.row(name)[5].className,'pending');
 }
 assert.deepEqual(['alpha','beta'].map(name=>b.row(name).slice(0,4).map(td=>td.textContent)),before);
 assert.equal(b.count(1).textContent,'通过 0 队');
 b.count(1).handlers.click();
 assert.equal(b.nodes.get('#body').childNodes[0].childNodes[0].textContent,'当前没有匹配的该题通过队伍');
});

test('summary-only frozen submissions reveal neither final results nor final tries',()=>{
 const b=board('icpc',freezeRows(),250*minute);
 for(const name of ['alpha','beta'])assert.equal(b.row(name)[7].textContent,'? 已提交');
});

test('ICPC tracks final-hour activity until contest end and stays frozen afterward',()=>{
 const b=board('icpc',freezeRows(),299*minute);
 assert.equal(b.row('alpha')[8].textContent,'? +1');
 b.advance(300*minute);
 const frozen=b.row('alpha').map(td=>td.textContent);
 b.advance(360*minute);
 assert.deepEqual(b.row('alpha').map(td=>td.textContent),frozen);
 assert.equal(b.row('alpha')[8].textContent,'? +1');
 assert.equal(b.nodes.get('#progress').textContent,'比赛结束 · 保持封榜');
});

test('submission replay refreshes within a minute, and never exposes future results',()=>{
 const rows=[{user:{name:'alpha'},statuses:[status('AC',[solution('AC',10.5)])]}];
 const b=board('icpc',rows,10*minute);
 assert.equal(b.row('alpha')[2].textContent,'0');
 b.advance(10.5*minute);
 assert.equal(b.row('alpha')[2].textContent,'1');
 b.advance(-minute);
 assert.equal(b.row('alpha')[2].textContent,'0');
});

test('CCPC retains threshold reveal and the fixed 4-hour snapshot',()=>{
 const rows=freezeRows();while(rows.length<10)rows.push({user:{name:'empty'+rows.length},statuses:Array.from({length:5},()=>({result:null}))});
 const b=board('ccpc',rows,minute);
 assert.equal(b.nodes.get('#head').childNodes[0].childNodes.length,4);
 b.advance(240*minute);
 assert.equal(b.row('alpha')[6].className,'ac');
 const frozen=b.row('alpha').map(td=>td.textContent);
 b.advance(299*minute);
 assert.deepEqual(b.row('alpha').map(td=>td.textContent),frozen);
});
