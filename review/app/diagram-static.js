// Adapter boundary: render a snapshot using semantic device/net selections.
// Analysis code never reads image coordinates. Future Canvas adapters implement
// render(host, snapshot, selection) and emit a data-device selection by stable ID.
const ReviewDiagram = {
  render(host, t, selection) {
    const {attention, selected, nets} = selection;
    const a = {nets};
    host.innerHTML = `<img src="${t.image}" alt="用户提供的 Bootstrap 电路静态图"><svg viewBox="0 0 ${t.width} ${t.height}" aria-hidden="true">${(a?a.nets:[]).filter(n=>t.net_marks[n]).map(n=>`<path d="${t.net_marks[n].path}" class="net-highlight"/>`).join('')}</svg>${Object.entries(t.anchors).map(([id,[x,y,w,h]])=>`<button class="device-hotspot ${attention.has(id)?'attention':''} ${id===selected?'picked':''}" data-device="${id}" aria-label="查看 ${id} 端子" title="${id}" style="left:${x/t.width*100}%;top:${y/t.height*100}%;width:${w/t.width*100}%;height:${h/t.height*100}%"></button>`).join('')}`;
  }
};
