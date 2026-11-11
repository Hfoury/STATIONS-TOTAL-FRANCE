import csv,json,math,os,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/"data";DATA.mkdir(exist_ok=True)
API="https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/prix-des-carburants-en-france-flux-instantane-v2/exports/json"
def distance(a,b):
 p=math.pi/180;dlat=(a["latitude"]-b["latitude"])*p;dlon=(a["longitude"]-b["longitude"])*p
 h=math.sin(dlat/2)**2+math.cos(a["latitude"]*p)*math.cos(b["latitude"]*p)*math.sin(dlon/2)**2
 return 6371000*2*math.asin(min(1,math.sqrt(h)))
def main():
 sf=DATA/"stations_osm.json"
 if not sf.exists():raise RuntimeError("Référentiel OSM absent : lancer d'abord le workflow de découverte")
 stations=json.loads(sf.read_text(encoding="utf-8"))["items"]
 r=requests.get(API,params={"lang":"fr"},timeout=180);r.raise_for_status();records=r.json()
 if isinstance(records,dict):records=records.get("results",records.get("records",[]))
 if not records:raise RuntimeError("Flux officiel vide")
 now=datetime.now(timezone.utc);out=[]
 for s in stations:
  best=None;bestd=10**9
  for g in records:
   try:
    lat=float(g.get("latitude"))/100000;lon=float(g.get("longitude"))/100000
    if abs(lat-s["latitude"])>.003 or abs(lon-s["longitude"])>.004:continue
    cand={"latitude":lat,"longitude":lon};d=distance(s,cand)
    if d<bestd:bestd=d;best=g
   except (TypeError,ValueError):continue
  x=dict(s);x["distance_correspondance_m"]=round(bestd,1) if best else None
  x["correspondance_prix"]="proche <= 200 m" if best and bestd<=200 else "non confirmée"
  for fuel in ["gazole","sp95","e10","sp98","e85","gplc"]:
   x[fuel+"_prix"]=best.get(fuel+"_prix") if best and bestd<=200 else None
   x[fuel+"_maj"]=best.get(fuel+"_maj") if best and bestd<=200 else None
  x["station_officielle_id"]=best.get("id") if best and bestd<=200 else None
  x["actualise_le"]=now.isoformat();out.append(x)
 if not out:raise RuntimeError("Aucune station à publier")
 payload={"generated_at":now.isoformat(),"source_prix":"Ministère de l'Économie / DGCCRF - flux instantané","source_enseignes":"OpenStreetMap","note":"Rapprochement géographique indicatif entre OSM et les points officiels ; seuls les rapprochements à 200 m ou moins affichent des prix.","count":len(out),"items":out}
 (DATA/"stations_total.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
 with (DATA/"stations_total.csv").open("w",newline="",encoding="utf-8-sig") as f:
  w=csv.DictWriter(f,fieldnames=list(out[0]),delimiter=";");w.writeheader();w.writerows(out)
 ch=ET.Element("channel")
 for k,v in [("title","Stations Total et Total Access - France"),("link","https://github.com/Hfoury/STATIONS-TOTAL-FRANCE"),("description","Référentiel des stations Total repérées dans OpenStreetMap avec prix officiels rapprochés géographiquement."),("lastBuildDate",now.strftime("%a, %d %b %Y %H:%M:%S +0000"))]:ET.SubElement(ch,k).text=v
 root=ET.Element("rss",version="2.0");root.append(ch)
 for x in out:
  it=ET.SubElement(ch,"item");ET.SubElement(it,"title").text=x["enseigne"]+" - "+(x["commune"] or x["code_postal"] or x["nom"]);ET.SubElement(it,"guid",isPermaLink="false").text=x["osm_id"];ET.SubElement(it,"link").text=x["osm_url"]
  desc=f'{x["adresse"]} | Gazole: {x["gazole_prix"]} | SP95-E10: {x["e10_prix"]} | SP98: {x["sp98_prix"]} | rapprochement: {x["correspondance_prix"]}'
  ET.SubElement(it,"description").text=desc
 ET.ElementTree(root).write(DATA/"flux.rss",encoding="utf-8",xml_declaration=True)
 print(f'{len(out)} stations publiées ; prix rapprochés pour {sum(x["correspondance_prix"]=="proche <= 200 m" for x in out)}')
if __name__=="__main__":main()
