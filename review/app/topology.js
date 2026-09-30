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
    $('phase-explanation').textContent=p.clock+'。'+p.text+' 待验证：'+p.verify;
    $('group-explanation').textContent=g?g.text:'五个功能块：选择后定位成员，不改变相位或导通判断。';
    $('topology-picture').innerHTML=`<img src="${t.image}" alt="用户提供的 Bootstrap 电路静态图"><svg viewBox="0 0 1034 675" aria-hidden="true">${(a?a.nets:[]).filter(n=>t.net_marks[n]).map(n=>`<path d="${t.net_marks[n].path}" class="net-highlight"/>`).join('')}</svg>${Object.entries(t.anchors).map(([id,[x,y,w,h]])=>`<button class="device-hotspot ${attention.has(id)?'attention':''} ${id===selected?'picked':''}" data-device="${id}" aria-label="查看 ${id} 端子" title="${id}" style="left:${x/1034*100}%;top:${y/675*100}%;width:${w/1034*100}%;height:${h/675*100}%"></button>`).join('')}`;
    $('topic-explanation').innerHTML=a?`<h3>${esc(a.title)}</h3><p class="analysis-fact"><b>拓扑事实</b>${esc(a.fact)}</p><p class="analysis-inference"><b>条件推断</b>${esc(a.inference)}</p><p class="analysis-check"><b>待验证</b>${esc(a.verify)}</p><small>关注网络：${a.nets.map(n=>esc(t.aliases[n]?t.aliases[n]+' / '+n:n)).join(' · ')}</small>`:'<p>当前仅按相位显示关注器件。选择主题查看事实、推断与验证需求。</p>';
    if(selected){
      const pins=t.devices[selected],related=t.topics.filter(a=>a.devices.includes(selected));
      $('device-explanation').innerHTML=`<h3>${esc(selected)}</h3><p>${Object.entries(pins).map(([pin,net])=>`${pin} → ${esc(t.aliases[net]?t.aliases[net]+' ('+net+')':net)}`).join('<br>')}</p><p>所属功能：${esc(t.groups.find(g=>g.devices.includes(selected)).title)}</p><p>相关分析</p>${related.length?buttons(related,'topic',topic):'<small>暂无专题；可按所属功能块审查。</small>'}`;
    }else $('device-explanation').innerHTML='<p>点击图中器件，反查网表端子与相关分析。端序暂按 D/G/S/B；体端不会省略。</p>';
  }
  $('topology-title').textContent=t.title;
  $('topology-notice').textContent=t.notice;
  $('topology-mapping').textContent=t.mapping+' 网表版本 '+t.revision+'；图片版本 '+t.image_revision+'。本样例无外部保持负载；不提供数值精度或可靠性结论。';
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
