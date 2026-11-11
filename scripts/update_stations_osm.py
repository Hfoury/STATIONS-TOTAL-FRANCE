import json,re,os
from datetime import datetime,timezone
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/"data";DATA.mkdir(exist_ok=True)
Q='[out:json][timeout:240];area["ISO3166-1"="FR"][admin_level=2]->.fr;(nwr["amenity"="fuel"]["brand"~"total",i](area.fr);nwr["amenity"="fuel"]["name"~"total",i](area.fr);nwr["amenity"="fuel"]["operator"~"total",i](area.fr););out center tags;'
def main():
 u=os.getenv("OVERPASS_URL","https://overpass-api.de/api/interpreter")
 r=requests.post(u,data={"data":Q},headers={"User-Agent":"STATIONS-TOTAL-FRANCE/1.0"},timeout=300);r.raise_for_status()
 items={}
 for e in r.json().get("elements",[]):
  t=e.get("tags",{}); text=" ".join([t.get("brand",""),t.get("name",""),t.get("operator","")])
  if not re.search(r"total",text,re.I):continue
  c=e.get("center",{});lat=e.get("lat",c.get("lat"));lon=e.get("lon",c.get("lon"))
  if lat is None or lon is None:continue
  name=t.get("name") or t.get("brand") or t.get("operator") or "Station Total"
  item={"osm_id":f'{e["type"]}:{e["id"]}',"nom":name,"enseigne":("Total Access" if re.search(r"total\s*access",text,re.I) else "TotalEnergies"),"adresse":", ".join(filter(None,[t.get("addr:housenumber"),t.get("addr:street"),t.get("addr:postcode"),t.get("addr:city")])),"code_postal":t.get("addr:postcode",""),"commune":t.get("addr:city",""),"latitude":float(lat),"longitude":float(lon),"horaires":t.get("opening_hours",""),"osm_url":f'https://www.openstreetmap.org/{e["type"]}/{e["id"]}'}
  items[item["osm_id"]]=item
 if not items:raise RuntimeError("Aucune station Total trouvée : fichier précédent conservé")
 rows=sorted(items.values(),key=lambda x:(x["code_postal"],x["commune"],x["nom"]))
 (DATA/"stations_osm.json").write_text(json.dumps({"generated_at":datetime.now(timezone.utc).isoformat(),"source":"OpenStreetMap / Overpass","count":len(rows),"items":rows},ensure_ascii=False,indent=2),encoding="utf-8")
 print(f"{len(rows)} stations candidates identifiées dans OpenStreetMap")
if __name__=="__main__":main()
