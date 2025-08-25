async function refresh() {
  try {
    const r = await fetch('/api/stats');
    const s = await r.json();
    document.getElementById('distance')?.innerText = s.distance_m==null ? "--.- m" : `${s.distance_m.toFixed(1)} m`;
    document.getElementById('led')?.innerText = s.led_status || "--";
    document.getElementById('wifi')?.innerText = s.wifi_ssid ? `${s.wifi_ssid} (${s.wifi_rssi}%)` : "--";
    document.getElementById('cpu')?.innerText = (s.cpu_temp_c!=null) ? `${s.cpu_temp_c.toFixed(1)}°C / ${s.cpu_load?.toFixed(2)}` : "--";
    document.getElementById('batt')?.innerText = (s.battery_pct!=null) ? `${s.battery_pct.toFixed(0)}% (${s.voltage?.toFixed(2)}V)` : "--";
    document.getElementById('lux')?.innerText = (s.lux!=null) ? s.lux.toFixed(0) : "--";
  } catch (e) {}
}
async function loadSeries() {
  const r = await fetch('/api/series'); const s = await r.json();
  drawLine('battChart', s.battery.map(p=>({x:p.t*1000,y:p.pct})), 0, 100, 'Battery %');
  drawLine('motionChart', s.motion.map(p=>({x:p.t*1000,y:p.m})), 0, undefined, 'Motion');
}
function drawLine(id, pts, ymin, ymax, label) {
  const c = document.getElementById(id); if (!c) return;
  const ctx = c.getContext('2d'); ctx.clearRect(0,0,c.width,c.height);
  const pad=30; const xs = pts.length ? pts[0].x : Date.now()-1000*60*60*4;
  const xe = pts.length ? pts[pts.length-1].x : Date.now();
  const ys = ymin ?? Math.min(...pts.map(p=>p.y),0), ye = ymax ?? Math.max(...pts.map(p=>p.y),1);
  function X(x){ return pad + ( (x-xs)/(xe-xs||1) ) * (c.width-2*pad); }
  function Y(y){ return c.height-pad - ((y-ys)/(ye-ys||1))*(c.height-2*pad); }
  ctx.strokeStyle = '#5b8cff'; ctx.beginPath();
  pts.forEach((p,i)=>{ if(i===0) ctx.moveTo(X(p.x),Y(p.y)); else ctx.lineTo(X(p.x),Y(p.y)); }); ctx.stroke();
  ctx.fillStyle='#98a2b3'; ctx.fillText(label, 8, 12);
}
async function scanWifi(){
  const out = await (await fetch('/wifi/scan')).json();
  const div = document.getElementById('wifiList'); div.innerHTML = '';
  out.networks.forEach(n=>{
    const el = document.createElement('div');
    el.innerHTML = `<form method="post" action="/wifi/connect" class="wifirow">
      <input type="hidden" name="ssid" value="${n.ssid}">
      <strong>${n.ssid}</strong> (${n.signal}%) ${n.security}
      <input type="password" name="password" placeholder="password">
      <button class="btn" type="submit">Connect</button>
    </form>`;
    div.appendChild(el);
  });
}
setInterval(refresh, 2000);
window.addEventListener('load', ()=>{ refresh(); loadSeries(); });
