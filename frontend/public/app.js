const $ = id => document.getElementById(id);
const svgNS = 'http://www.w3.org/2000/svg';
function element(tag, text, className) { const node = document.createElement(tag); node.textContent = text; if(className) node.className = className; return node; }
function itinerary(target, journey) {
  target.replaceChildren();
  if (!journey) { target.append(element('p', 'No feasible journey within the three-hour search window.')); return; }
  const groups=[];
  for(const leg of journey.legs) { const previous=groups.at(-1); if(previous && leg.trip && previous.trip===leg.trip) { previous.to_name=leg.to_name;previous.arrival=leg.arrival; } else groups.push({...leg}); }
  for(const leg of groups) { const row=element('div', leg.walk?'Walk to platform':`Route ${leg.route}`, 'leg');row.append(element('span',`${leg.from_name} → ${leg.to_name}`),element('span',`${leg.departure} – ${leg.arrival}`)); target.append(row); }
}
function drawMap(map) {
  const svg=$('map');svg.replaceChildren();
  const all=map.stops.map(s=>[s.lon,s.lat]).concat(map.walk_coordinates,[map.incident_center]);
  const xs=all.map(p=>p[0]),ys=all.map(p=>p[1]);const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
  const project=p=>[80+(p[0]-minX)/(maxX-minX||.001)*640,380-(p[1]-minY)/(maxY-minY||.001)*300];
  function add(tag,attrs,text) {const n=document.createElementNS(svgNS,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);if(text)n.textContent=text;svg.append(n);return n;}
  add('polyline',{points:map.stops.map(s=>project([s.lon,s.lat]).join(',')).join(' '),fill:'none',stroke:'#5595cd','stroke-width':4,'stroke-dasharray':'8 6'});
  add('polyline',{points:map.walk_coordinates.map(p=>project(p).join(',')).join(' '),fill:'none',stroke:'#7ae2bd','stroke-width':5});
  map.stops.forEach((s,i)=>{const [x,y]=project([s.lon,s.lat]);add('circle',{cx:x,cy:y,r:6,fill:'#b8dbf7'});const c=add('text',{x:x+10,y:y+(i%2?18:-12),fill:'#e5edf6','font-size':12},s.name);if(i>0 && i<map.stops.length-1)c.setAttribute('font-size','10');});
  const [x,y]=project(map.incident_center);add('path',{d:`M ${x} ${y-10} l 10 10 -10 10 -10 -10 Z`,fill:'#ffc16c'});
}
async function calculate() {
  $('run').disabled=true;$('reset').disabled=true;$('status').textContent='Calculating journeys from the transit network…';
  try { const response=await fetch(`/api/demo?delay_minutes=${$('delay').value}`);if(!response.ok)throw new Error(`API returned ${response.status}`);const data=await response.json();
    $('date').textContent=`Fixed demo date: ${data.service_date} · America/Denver`;
    $('normal-arrival').textContent=data.baseline.arrival;$('alternative-arrival').textContent=data.alternative?.arrival||'No connection';
    itinerary($('normal-legs'),data.baseline);itinerary($('alternative-legs'),data.alternative);
    $('alert').textContent=data.scenario.missed_transfer?`Your ${data.scenario.original_train_departure} connection is missed. Modeled bus arrival: ${data.scenario.delayed_bus_arrival}. ${data.alternative?`The replacement arrives ${data.arrival_penalty_minutes} minutes later.`:'No replacement found.'}`:'The original connection remains feasible with the assumed delay.';
    $('limitations').replaceChildren(...data.limitations.map(text=>element('li',text)));drawMap(data.map);$('results').hidden=false;$('status').textContent=`${data.origin} → ${data.destination}. Assumed delay on ${data.scenario.road}: ${data.scenario.delay_minutes} minutes.`;
  } catch(error) {$('results').hidden=true;$('status').textContent='The routing dataset is unavailable. Check /ready and run the documented preparation command.';} finally {$('run').disabled=false;$('reset').disabled=false;}
}
$('delay').addEventListener('input',()=>{$('delay-label').textContent=`${$('delay').value} minutes`;});
$('run').addEventListener('click',calculate);$('reset').addEventListener('click',()=>{$('delay').value=0;$('delay-label').textContent='0 minutes';calculate();});
calculate();
