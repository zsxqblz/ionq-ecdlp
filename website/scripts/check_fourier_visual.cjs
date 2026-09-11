// Check the real UI event handlers against an independently evaluated 2D DFT.
// This checks states and controls, not browser layout or native keyboard behavior.
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert/strict');
const root=path.resolve(__dirname,'..');
const page=fs.readFileSync(path.join(root,'dist/lesson/shor-ecdlp/index.html'),'utf8');
const grids=[...page.matchAll(/<svg\b[^>]*data-fourier-grid="(input|frequency)"[^>]*>([\s\S]*?)<\/svg>/g)].map(m=>{
 const dots=[...m[2].matchAll(/<circle\b([^>]*)\/>/g)].map(c=>{
  const attrs=Object.fromEntries([...c[1].matchAll(/([\w-]+)="([^"]*)"/g)].map(a=>[a[1],a[2]]));
  return {dataset:{x:attrs['data-x'],y:attrs['data-y']},attrs,setAttribute(k,v){this.attrs[k]=v;}};
 });
 const desc={textContent:''};
 return {dataset:{fourierGrid:m[1]},dots,querySelectorAll(){return dots;},querySelector(){return desc;}};
});
assert.equal(grids.length,2);grids.forEach(g=>assert.equal(g.dots.length,49));
function slider(value){return {value:String(value),listeners:{},addEventListener(k,f){this.listeners[k]=f;}};}
const dInput=slider(3),cInput=slider(2);
const nodes={'#fourier-d':dInput,'#fourier-c':cInput,'#fourier-d-value':{},'#fourier-c-value':{},'#fourier-feedback':{}};
const document={querySelector:s=>nodes[s]||null,querySelectorAll:s=>s==='[data-fourier-grid]'?grids:[]};
vm.runInNewContext(fs.readFileSync(path.join(root,'site.js'),'utf8'),{document,window:{addEventListener(){}},location:{hash:''}});
function selected(g){return new Set(g.dots.filter(x=>x.attrs.class==='fourier-hit').map(x=>`${x.dataset.x},${x.dataset.y}`));}
function expected(d,c){
 // Explicit input state: labels with equal classical point output.
 const inputs=[];for(let k=0;k<7;k++)for(let l=0;l<7;l++)if((k+d*l)%7===c)inputs.push([k,l]);
 const frequencies=[];
 for(let u=0;u<7;u++)for(let v=0;v<7;v++){
  let real=0,imag=0;
  for(const [k,l] of inputs){const theta=-2*Math.PI*(u*k+v*l)/7;real+=Math.cos(theta)/(7*Math.sqrt(7));imag+=Math.sin(theta)/(7*Math.sqrt(7));}
  const prob=real*real+imag*imag;
  if(prob>1e-12){assert.ok(Math.abs(prob-1/7)<1e-12);frequencies.push([u,v]);}
 }
 return [inputs,frequencies].map(a=>new Set(a.map(p=>p.join(','))));
}
function check(d,c){const pairs=expected(d,c);grids.forEach((g,i)=>assert.deepEqual(selected(g),pairs[i]));}
check(3,2); // The static fallback must already match the controls before JS runs.
for(let d=0;d<7;d++)for(let c=0;c<7;c++){
 dInput.value=String(d);cInput.value=String(c);
 dInput.listeners.input();cInput.listeners.input();check(d,c);
 assert.equal(nodes['#fourier-d-value'].textContent,d);assert.equal(nodes['#fourier-c-value'].textContent,c);
}
console.log('Fourier visual: static fallback and both controls match the exact inverse DFT for all 49 parameter pairs.');
