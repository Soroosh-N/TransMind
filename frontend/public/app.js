const $ = id => document.getElementById(id);
let map, journeyBounds, mapLayers;
function element(tag, text, className) { const node = document.createElement(tag); node.textContent = text; if(className) node.className = className; return node; }
function itinerary(target, journey) {
  target.replaceChildren();
  if (!journey) { target.append(element('p', 'No journey found within three hours.')); return; }
  const groups = [];
  for (const leg of journey.legs) { const previous = groups.at(-1); if (previous && leg.trip && previous.trip === leg.trip) { previous.to_name = leg.to_name; previous.arrival = leg.arrival; } else groups.push({...leg}); }
  for (const leg of groups) { const row = element('div', leg.walk ? 'Walk to platform' : `Route ${leg.route}`, 'leg'); row.append(element('span', `${leg.from_name} -> ${leg.to_name}`), element('span', `${leg.departure} - ${leg.arrival}`)); target.append(row); }
}
async function initializeMap() {
  map = L.map('map', {scrollWheelZoom: false}).setView([40.685, -111.893], 13);
  const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19, keepBuffer: 1, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'}).addTo(map);
  tiles.on('tileerror', () => { $('map-status').textContent = 'Some street tiles are unavailable. Local OSM streets and transit routes remain visible.'; if (!map.hasLayer(streets)) streets.addTo(map); });
  tiles.on('tileload', () => { $('map-status').textContent = 'Street basemap: pan, zoom, and click routes or stops. Local OSM streets are available as a separate layer.'; });
  const streets = L.geoJSON(null, {style: feature => ({color: feature.properties.highway === 'footway' ? '#cdc4b4' : '#c1b8a8', weight: 2}), onEachFeature: (feature, layer) => { if (feature.properties.name) layer.bindPopup(element('span', feature.properties.name)); }});
  map.attributionControl.addAttribution('Local roads &copy; OpenStreetMap contributors / <a href="https://www.openstreetmap.org/copyright">ODbL</a>');
  mapLayers = {affected: L.layerGroup().addTo(map), normal: L.layerGroup().addTo(map), alternative: L.layerGroup().addTo(map), walk: L.layerGroup().addTo(map), stops: L.layerGroup().addTo(map), incident: L.layerGroup().addTo(map)};
  L.control.layers({'OpenStreetMap streets': tiles}, {'Local street network': streets, 'Affected route shapes': mapLayers.affected, 'Normal journey': mapLayers.normal, 'Alternative journey': mapLayers.alternative, 'Station walk': mapLayers.walk, 'Stops': mapLayers.stops, 'Simulated incident': mapLayers.incident}, {collapsed: window.innerWidth <= 760}).addTo(map);
  try { const response = await fetch('/assets/map-context.geojson'); if (!response.ok) throw new Error('Local roads unavailable'); streets.addData(await response.json()); } catch { $('map-status').textContent = 'Local road layer unavailable; online basemap remains enabled.'; }
}
function latLng(coordinate) { return [coordinate[1], coordinate[0]]; }
function drawMap(data) {
  for (const layer of Object.values(mapLayers)) layer.clearLayers();
  const info = data.map;
  for (const coordinates of info.affected_paths) L.polyline(coordinates.map(latLng), {color: '#e58c20', weight: 7, opacity: .5}).addTo(mapLayers.affected).bindPopup('Route shape containing a modeled affected trip. Delay applies downstream of the incident.');
  for (const path of info.baseline_paths) L.polyline(path.coordinates.map(latLng), {color: '#2369bc', weight: 5}).addTo(mapLayers.normal).bindPopup(element('span', `Normal journey / Route ${path.route}`));
  for (const path of info.alternative_paths) L.polyline(path.coordinates.map(latLng), {color: '#159369', weight: 3, dashArray: '8 5'}).addTo(mapLayers.alternative).bindPopup(element('span', `Alternative / Route ${path.route}`));
  L.polyline(info.walk_coordinates.map(latLng), {color: '#705cb3', weight: 4, dashArray: '4 4'}).addTo(mapLayers.walk).bindPopup('Mapped station walking transfer; accessibility has not been field-verified.');
  for (const stop of info.stops) L.circleMarker([stop.lat, stop.lon], {radius: 5, color: '#38556a', fillColor: '#fff', fillOpacity: 1, weight: 2}).addTo(mapLayers.stops).bindPopup(element('span', stop.name));
  if (data.scenario.delay_minutes > 0) { L.circle(latLng(info.incident_center), {radius: info.incident_radius_meters, color: '#c54934', fillOpacity: .3}).addTo(mapLayers.incident).bindPopup(element('span', `Simulated Vine Street incident / ${data.scenario.direction} / ${data.scenario.start_time} / ${data.scenario.delay_minutes} minute assumed delay`)); L.circleMarker(latLng(info.incident_center), {radius: 8, color: '#fff', fillColor: '#c54934', fillOpacity: 1, weight: 2}).addTo(mapLayers.incident); }
  const coordinates = info.baseline_paths.concat(info.alternative_paths).flatMap(path => path.coordinates);
  journeyBounds = L.latLngBounds((coordinates.length ? coordinates : info.stops.map(stop => [stop.lon, stop.lat])).map(latLng)); journeyBounds.extend(latLng(info.incident_center)); map.fitBounds(journeyBounds, {padding: [30, 30], maxZoom: 15});
  window.transitMindMapState = {normalPaths: info.baseline_paths.length, alternativePaths: info.alternative_paths.length, affectedPaths: info.affected_paths.length, bounds: journeyBounds.toBBoxString()};
}
async function calculate() {
  $('run').disabled = true; $('reset').disabled = true; $('status').textContent = 'Calculating incident impacts and journeys...';
  const query = new URLSearchParams({delay_minutes: $('delay').value, origin_id: $('origin').value, destination_id: $('destination').value, departure_time: $('departure').value, direction: $('direction').value, start_time: $('incident-start').value, duration_minutes: $('incident-duration').value});
  try { const response = await fetch(`/api/demo?${query}`); if (!response.ok) throw new Error(`Journey request returned ${response.status}`); const data = await response.json();
    $('date').textContent = `Fixed demo date: ${data.service_date}`; $('normal-arrival').textContent = data.baseline?.arrival || 'No journey'; $('alternative-arrival').textContent = data.alternative?.arrival || 'No journey'; itinerary($('normal-legs'), data.baseline); itinerary($('alternative-legs'), data.alternative);
    $('alert').textContent = data.scenario.missed_transfer ? `Your ${data.scenario.original_train_departure} connection is missed. Modeled bus arrival: ${data.scenario.delayed_bus_arrival}. ${data.alternative ? `The replacement arrives ${data.arrival_penalty_minutes} minutes later.` : 'No replacement found.'}` : (data.baseline ? 'The original connection remains feasible under this scenario.' : 'No scheduled journey found for these stops and departure time.');
    $('impact-list').replaceChildren(element('strong', `${data.scenario.affected_trip_count} affected trips`), element('p', data.scenario.affected_routes.length ? `Routes ${data.scenario.affected_routes.join(', ')} / ${data.scenario.direction}` : 'No trips match this direction and incident window.')); for (const impact of data.scenario.impacts) $('impact-list').append(element('div', `Trip ${impact.trip_id} / encounter ${impact.encounter_time}`));
    $('limitations').replaceChildren(...data.limitations.map(text => element('li', text))); $('results').hidden = false; drawMap(data); $('status').textContent = `${data.origin} -> ${data.destination}. ${data.scenario.affected_trip_count} trips intersect the incident corridor during its active window.`;
  } catch(error) { $('results').hidden = true; $('status').textContent = 'Unable to calculate this journey. Check the selected times and stops, then retry.'; } finally { $('run').disabled = false; $('reset').disabled = false; }
}
async function start() {
  $('run').disabled = true; $('reset').disabled = true;
  try { await initializeMap(); const response = await fetch('/api/options'); if (!response.ok) throw new Error('Dataset not ready'); const options = await response.json(); for (const stop of options.stops) for (const id of ['origin', 'destination']) { const option = element('option', stop.name); option.value = stop.id; $(id).append(option); } $('origin').value = options.origin_id; $('destination').value = options.destination_id; await calculate(); } catch(error) { $('status').textContent = 'Transit data or map setup is unavailable. Refresh after the service is ready.'; }
}
$('delay').addEventListener('input', () => { $('delay-label').textContent = `${$('delay').value} minutes`; }); $('run').addEventListener('click', calculate); $('reset').addEventListener('click', () => { $('delay').value = 0; $('delay-label').textContent = '0 minutes'; calculate(); }); $('fit-map').addEventListener('click', () => { if (journeyBounds) map.fitBounds(journeyBounds, {padding: [30, 30], maxZoom: 15}); }); start();
