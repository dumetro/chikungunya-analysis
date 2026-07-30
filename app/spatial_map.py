"""Build the interactive Leaflet outbreak-map dashboard for the Spatial Analysis page.

Reads the bundled Earth-AI geodata layers (``data/geodata/``) and returns a
self-contained HTML string (Leaflet from CDN, GeoJSON embedded inline) rendered
over an OpenStreetMap-derived CARTO base map. Four toggleable overlays — district
case-intensity choropleth, graduated case-volume symbols, Aedes albopictus
vector hotspots and the Aug–Oct expansion-risk forecast — plus district outlines,
a legend that follows the active layer, and headline stat cards.

The HTML is embedded on the page with ``streamlit.components.v1.html``. It is a
fixed July-2026 geodata snapshot (independent of the sidebar filters), matching
the other curated-geodata visual on the page.
"""

from __future__ import annotations

import json
from pathlib import Path

# Locality labels for the 10 Aedes hotspot points, ordered as in the vector-risk
# layer (from the entomological survey findings the layer was built from).
_HOTSPOT_LABELS = [
    "Rose-Hill (Stanley / Roches-Brunes)", "Beau-Bassin", "Quatre-Bornes",
    "Rose-Hill (Plaisance)", "Vacoas-Phoenix", "Baie-du-Tombeau",
    "Péreybère / Grand-Baie", "Chemin-Grenier", "Tyack / Souillac",
    "Pointe-d'Esny / Mahébourg",
]

_INTENSITY_RANK = {"Very High": 4, "High": 3, "Moderate": 2, "Low": 1, "Minimal": 0}


def _read(geodir: Path, name: str) -> dict | None:
    p = geodir / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _centroid(geom: dict) -> tuple[float, float] | None:
    """Rough centroid of a Polygon / MultiPolygon (largest ring)."""
    def ring_mean(coords):
        xs = [pt[0] for pt in coords]
        ys = [pt[1] for pt in coords]
        return sum(xs) / len(xs), sum(ys) / len(ys)

    t, c = geom.get("type"), geom.get("coordinates")
    if t == "Polygon" and c:
        return ring_mean(c[0])
    if t == "MultiPolygon" and c:
        best = max((poly[0] for poly in c), key=len)
        return ring_mean(best)
    return None


def build_map_html(geodata_dir: str | Path) -> str:
    """Return the self-contained Leaflet dashboard HTML built from ``geodata_dir``."""
    geodir = Path(geodata_dir)

    intensity = _read(geodir, "chikungunya_district_intensity__corrected_scheme_.geojson")
    expansion = _read(geodir, "chikungunya_expansion_risk__aug-oct_2026_.geojson")
    hotspots = _read(geodir, "aedes_albopictus_hotspots__vector_risk_.geojson")

    if intensity is None:
        return ("<div style='padding:24px;font-family:sans-serif;color:#5B6B7B'>"
                "Interactive map geodata not found in <code>data/geodata/</code>.</div>")

    # Label the hotspot points.
    if hotspots:
        for i, f in enumerate(hotspots.get("features", [])):
            f.setdefault("properties", {})["locality"] = (
                _HOTSPOT_LABELS[i] if i < len(_HOTSPOT_LABELS) else "Aedes hotspot")

    # Graduated-symbol points from the intensity polygons.
    grad = []
    for f in intensity.get("features", []):
        p = f.get("properties", {})
        cases = int(p.get("cases", 0) or 0)
        if cases <= 0:
            continue
        ct = _centroid(f.get("geometry", {}))
        if ct:
            grad.append({"name": p.get("name", "").replace(" District", ""),
                         "cases": cases, "intensity": p.get("intensity", "Minimal"),
                         "color": p.get("color", "#FFE873"), "lon": ct[0], "lat": ct[1]})

    # Headline stats.
    districts = [f["properties"] for f in intensity.get("features", [])]
    total = sum(int(p.get("cases", 0) or 0) for p in districts)
    epi = max(districts, key=lambda p: int(p.get("cases", 0) or 0), default={})
    n_hot = len(hotspots.get("features", [])) if hotspots else 0
    high_risk = 0
    if expansion:
        for f in expansion.get("features", []):
            cat = str(f["properties"].get("expansion_risk_category")
                      or f["properties"].get("spread_risk_category") or "")
            if cat in ("High", "Very High"):
                high_risk += 1

    data = {
        "intensity": intensity, "expansion": expansion or {"type": "FeatureCollection", "features": []},
        "hotspots": hotspots or {"type": "FeatureCollection", "features": []},
        "grad": grad,
        "stats": {"total": total, "epi_name": epi.get("name", "—"),
                  "epi_cases": int(epi.get("cases", 0) or 0),
                  "hotspots": n_hot, "high_risk": high_risk},
    }
    return _HTML_TEMPLATE.replace("__DATA__", json.dumps(data))


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css"/>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<style>
*{box-sizing:border-box}
html,body{margin:0;height:100%;font-family:Lato,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1F2937}
#app{display:flex;flex-direction:column;height:100vh}
.stats{display:flex;gap:10px;flex-wrap:wrap;padding:10px 4px 12px}
.stat{background:#fff;border:1px solid #E6ECF2;border-left:4px solid #0093D5;border-radius:12px;padding:9px 14px;min-width:130px;box-shadow:0 1px 3px rgba(16,42,67,.05)}
.stat b{display:block;font-size:20px;color:#002D72;line-height:1.1}
.stat span{font-size:11px;color:#5B6B7B;text-transform:uppercase;letter-spacing:.3px}
#map{flex:1;border:1px solid #E6ECF2;border-radius:14px;box-shadow:0 1px 3px rgba(16,42,67,.05)}
.legend{background:#fff;padding:8px 10px;border-radius:8px;box-shadow:0 1px 6px rgba(0,0,0,.2);font-size:12px;line-height:1.7;color:#1F2937}
.legend i{width:14px;height:14px;display:inline-block;margin-right:6px;border-radius:3px;vertical-align:-2px;opacity:.85}
.legend .dot{width:12px;height:12px;border-radius:50%;background:#7b1fa2;border:2px solid #fff;box-shadow:0 0 0 1px #7b1fa2;display:inline-block;margin-right:6px}
.leaflet-control-layers{font-size:13px}
</style></head>
<body>
<div id="app">
  <div class="stats" id="stats"></div>
  <div id="map"></div>
</div>
<script>
const D=__DATA__;
const s=D.stats;
document.getElementById('stats').innerHTML=[
  [s.total.toLocaleString(),'Cases (July 2026)'],
  [(s.epi_cases).toLocaleString(),(s.epi_name||'')+' (epicentre)'],
  [s.hotspots,'Aedes hotspots'],
  [s.high_risk,'High-risk districts (Aug–Oct)']
].map(x=>`<div class="stat"><b>${x[0]}</b><span>${x[1]}</span></div>`).join('');

const map=L.map('map',{zoomControl:true}).setView([-20.28,57.55],10);
L.tileLayer('https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png',
 {attribution:'&copy; OpenStreetMap contributors &copy; CARTO',subdomains:'abcd',maxZoom:19}).addTo(map);

const intensity=L.geoJSON(D.intensity,{
  style:f=>({fillColor:f.properties.color,color:'#555',weight:1,fillOpacity:.72}),
  onEachFeature:(f,l)=>{const p=f.properties;l.bindPopup(`<b>${p.name}</b><br>Intensity: ${p.intensity}<br>Est. cases: ${(p.cases||0).toLocaleString()}`);}
});
const grad=L.layerGroup(D.grad.map(d=>{
  const r=6+Math.sqrt(d.cases)*0.85;
  return L.circleMarker([d.lat,d.lon],{radius:r,fillColor:d.color,color:'#7a1010',weight:1,fillOpacity:.8})
    .bindPopup(`<b>${d.name}</b><br>${d.cases.toLocaleString()} cases · ${d.intensity}`)
    .bindTooltip(`${d.name}: ${d.cases.toLocaleString()}`,{direction:'top'});
}));
const vicon=L.divIcon({className:'',html:'<div style="width:16px;height:16px;border-radius:50%;background:#7b1fa2;border:2px solid #fff;box-shadow:0 0 0 1.5px #7b1fa2,0 1px 4px rgba(0,0,0,.4)"></div>',iconSize:[16,16],iconAnchor:[8,8]});
const hotspots=L.layerGroup((D.hotspots.features||[]).map(f=>{
  const c=f.geometry.coordinates,p=f.properties||{};
  return L.marker([c[1],c[0]],{icon:vicon}).bindPopup(`<b>Aedes albopictus hotspot</b><br>${p.locality||''}<br><i>High vector density (Breteau Index &gt;5); priority for larviciding / SIT.</i>`);
}));
const expansion=L.geoJSON(D.expansion,{
  style:f=>({fillColor:f.properties.color,color:'#444',weight:1,fillOpacity:.72}),
  onEachFeature:(f,l)=>{const p=f.properties;l.bindPopup(`<b>${p.name}</b><br>Spread-risk: <b>${p.expansion_risk_category||p.spread_risk_category||'—'}</b><br>Connectivity ${p.connectivity_score} · Environment ${p.env_score} · Vector ${p.vector_score}`);}
});

intensity.addTo(map);
const overlays={
 "Case intensity (choropleth)":intensity,
 "Graduated symbols (case volume)":grad,
 "Aedes hotspots (vector risk)":hotspots,
 "Expansion risk — Aug–Oct 2026":expansion
};
L.control.layers(null,overlays,{collapsed:false,position:'topright'}).addTo(map);

const legend=L.control({position:'bottomright'});
legend.onAdd=function(){this._d=L.DomUtil.create('div','legend');this.update();return this._d;};
function legendHTML(){
 const exp=map.hasLayer(expansion),hot=map.hasLayer(hotspots);
 let h= exp
  ? '<b>Spread-risk (Aug–Oct)</b><br><i style="background:#8B0000"></i>Very High<br><i style="background:#FF4500"></i>High<br><i style="background:#FFA500"></i>Moderate<br><i style="background:#FFD700"></i>Low<br>'
  : '<b>Case intensity</b><br><i style="background:#FF0000"></i>Very High (&gt;2000)<br><i style="background:#FFA500"></i>High / Moderate<br><i style="background:#FFFF00"></i>Low<br><i style="background:#FFFFE0"></i>Minimal<br>';
 if(hot) h+='<span class="dot"></span>Aedes hotspot<br>';
 return h;
}
legend.update=function(){this._d.innerHTML=legendHTML();};
legend.addTo(map);
map.on('overlayadd overlayremove',()=>legend.update());
</script>
</body></html>"""
