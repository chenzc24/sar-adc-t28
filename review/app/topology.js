(function(){
  'use strict';
  const t=JSON.parse(document.getElementById('review-data').textContent).topology;
  const $=id=>document.getElementById(id);
  const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let phase='track',topic='bootstrap',selected=null,group=null;
  const buttons=(items,key,active)=>items.map(i=>`<button data-${key}="${i.id}" aria-pressed="${i.id===active}">${esc(i.title)}</button>`).join('');
  function render(){
    const p=t.phases.find(x=>x.id===phase), a=t.topics.find(x=>x.id===topic);
    const g=t.groups.find(x=>x.id===group);
    const attention=new Set(g?g.devices:a?a.devices:p.devices);
    if(selected)attention.add(selected);
    $('phase-controls').innerHTML=buttons(t.phases,'phase',phase);
    $('topic-controls').innerHTML=buttons(t.topics,'topic',topic);
    $('group-controls').innerHTML=buttons(t.groups,'group',group);
    $('phase-explanation').textContent=p.clock+'。'+p.text;
    $('group-explanation').textContent=g?g.text:'';
    ReviewDiagram.render($('topology-picture'), t, {attention, selected, nets:a?a.nets:[]});
    $('topic-explanation').innerHTML=a?`<p class="analysis-fact"><b>连接</b>${esc(a.fact)}</p><p class="analysis-inference"><b>推断</b>${esc(a.inference)}</p><p class="analysis-check"><b>验证</b>${esc(a.verify)}</p>`:`<p class="analysis-check"><b>本相位验证</b>${esc(p.verify)}</p>`;
    if(selected){
      const pins=t.devices[selected],related=t.topics.filter(a=>a.devices.includes(selected));
      $('device-explanation').innerHTML=`<h3>${esc(selected)}</h3><p>${Object.entries(pins).map(([pin,net])=>`${pin} → ${esc(t.aliases[net]?t.aliases[net]+' ('+net+')':net)}`).join('<br>')}</p><p>所属功能：${esc(t.groups.find(g=>g.devices.includes(selected)).title)}</p><p>相关分析</p>${related.length?buttons(related,'topic',topic):'<small>暂无专题；可按所属功能块审查。</small>'}`;
    }else $('device-explanation').innerHTML='<p>点击器件查看端子与相关分析。</p>';
  }
  $('topology-title').textContent=t.title;
  $('topology-notice').textContent=t.notice;
  $('topology-mapping').textContent=t.mapping+' 高亮仅定位器件与网络，不表示导通状态或电流方向。网表 '+t.revision+'；图片 '+t.image_revision+'。';
  document.addEventListener('click',e=>{
    const b=e.target.closest('button');if(!b)return;
    if(b.dataset.topology){topic=b.dataset.topology;phase=t.topics.find(x=>x.id===topic).phase;selected=null;group=null;render();$('topology-dialog').showModal();}
    else if(b.id==='close-topology')$('topology-dialog').close();
    else if(b.dataset.phase){phase=b.dataset.phase;topic=null;group=null;selected=null;render();}
    else if(b.dataset.topic){topic=b.dataset.topic;phase=t.topics.find(x=>x.id===topic).phase;group=null;render();}
    else if(b.dataset.group){group=b.dataset.group;topic=null;selected=null;render();}
    else if(b.dataset.device){selected=b.dataset.device;render();}
  });
})();
