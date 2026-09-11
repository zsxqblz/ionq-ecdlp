(() => {
 const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
 const fourierD=$('#fourier-d'),fourierC=$('#fourier-c');
 function updateFourier(){
  const d=Number(fourierD.value),c=Number(fourierC.value);
  $('#fourier-d-value').textContent=d;$('#fourier-c-value').textContent=c;
  $$('[data-fourier-grid]').forEach(grid=>{
   const pairs=[];
   grid.querySelectorAll('circle[data-x]').forEach(dot=>{
    const x=Number(dot.dataset.x),y=Number(dot.dataset.y);
    const hit=(grid.dataset.fourierGrid==='input'?(x+d*y-c)%7===0:(y-d*x)%7===0);
    dot.setAttribute('class',hit?'fourier-hit':'fourier-empty');dot.setAttribute('r',hit?'7':'3');
    if(hit)pairs.push(`(${x},${y})`);
   });
   grid.querySelector('desc').textContent='Highlighted pairs: '+pairs.join(', ')+'. Each has probability 1/7.';
  });
  $('#fourier-feedback').textContent=`For d = ${d}, changing c moves the input coset but leaves the Fourier probabilities unchanged.`;
 }
 if(fourierD&&fourierC){fourierD.addEventListener('input',updateFourier);fourierC.addEventListener('input',updateFourier);}
 if($$('[data-runtime-chart]').length)fetch('/data/runtime.json').then(r=>{if(!r.ok)throw Error('data unavailable');return r.json();}).then(d=>{const rows=d.rows;const sum=names=>rows.filter(r=>names.includes(r.component)).reduce((a,r)=>a+r.layers,0);const total=rows.reduce((a,r)=>a+r.layers,0);const a=sum(['In-place multiplication']),b=sum(['Unary lookup','Phase-fix lookup','Initial lookup']),c=sum(['Square subtraction']);const vals=[a,b,c,total-a-b-c].map(v=>v*d.seconds_per_layer/3600);$$('[data-runtime-chart]').forEach(chart=>[...chart.querySelectorAll('.chart-row')].forEach((row,i)=>{row.querySelector('.bar').style.width=(vals[i]/400*100)+'%';row.lastElementChild.textContent=vals[i].toFixed(1)+' h';}));}).catch(()=>{});
 const menu=$('#menu-toggle');menu?.addEventListener('click',()=>{const on=menu.getAttribute('aria-expanded')!=='true';menu.setAttribute('aria-expanded',String(on));$('#top-navigation').classList.toggle('open',on);});
 const chapters=$('#chapters-toggle');chapters?.addEventListener('click',()=>{const on=chapters.getAttribute('aria-expanded')!=='true';chapters.setAttribute('aria-expanded',String(on));$('#sidebar').classList.toggle('open',on);});
 const filter=$('#lesson-search');filter?.addEventListener('input',()=>{const q=filter.value.toLocaleLowerCase().trim();let n=0;$$('.navgroup').forEach(g=>{let visible=0;g.querySelectorAll('a').forEach(a=>{const match=a.textContent.toLocaleLowerCase().includes(q);a.hidden=!match;visible+=+match;});g.hidden=!visible;n+=visible;});$('#no-results').hidden=n>0;});
 const dialog=$('#notation-dialog');let opener;function openNotation(el){opener=el;dialog.showModal();dialog.querySelector('button').focus();}$$('[data-open-notation]').forEach(b=>b.addEventListener('click',()=>openNotation(b)));$('#close-notation')?.addEventListener('click',()=>dialog.close());dialog?.addEventListener('close',()=>opener?.focus());dialog?.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});
 $$('[data-symbol]').forEach(b=>{b.tabIndex=0;b.setAttribute('role','button');b.addEventListener('click',()=>{openNotation(b);setTimeout(()=>dialog.querySelector('#def-'+b.dataset.symbol)?.scrollIntoView({block:'center'}),20);});b.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();b.click();}});});
 $('#expand-derivations')?.addEventListener('click',()=>$$('.lesson details').forEach(d=>d.open=true));$('#collapse-derivations')?.addEventListener('click',()=>$$('.lesson details').forEach(d=>d.open=false));
 if('IntersectionObserver'in window){const obs=new IntersectionObserver(entries=>{entries.filter(e=>e.isIntersecting).forEach(e=>{const id=e.target.id;$$('.toc a').forEach(a=>a.classList.toggle('active',a.hash==='#'+id));});},{rootMargin:'-120px 0px -65% 0px'});$$('.lesson h2[id]').forEach(h=>obs.observe(h));}
 function revealFragment(){if(!location.hash)return;let id;try{id=decodeURIComponent(location.hash.slice(1));}catch{return;}const target=document.getElementById(id);if(target){let p=target.parentElement;while(p){if(p.tagName==='DETAILS')p.open=true;p=p.parentElement;}requestAnimationFrame(()=>target.scrollIntoView());}}
 window.addEventListener('hashchange',revealFragment);revealFragment();
})();
