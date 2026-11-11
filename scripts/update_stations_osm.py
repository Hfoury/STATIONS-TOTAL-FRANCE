import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

# Découpage régional par rectangles géographiques. Les recouvrements sont
# volontaires ; les identifiants OSM éliminent les doublons à la fusion.
REGIONS = [
    ("Auvergne-Rhône-Alpes", 44.0, 2.0, 46.8, 7.2),
    ("Bourgogne-Franche-Comté", 46.0, 3.3, 48.5, 7.2),
    ("Bretagne", 47.2, -5.3, 48.9, -1.0),
    ("Centre-Val de Loire", 46.3, 0.0, 48.9, 3.0),
    ("Corse", 41.3, 8.4, 43.1, 9.7),
    ("Grand Est", 47.3, 4.8, 50.3, 8.3),
    ("Hauts-de-France", 49.5, 1.3, 51.3, 4.3),
    ("Normandie", 48.1, -1.9, 50.2, 1.9),
    ("Nouvelle-Aquitaine", 42.7, -1.8, 47.2, 1.5),
    ("Occitanie", 42.3, -0.2, 45.1, 4.9),
    ("Pays de la Loire", 46.2, -2.0, 48.6, 0.9),
    ("Provence-Alpes-Côte d'Azur", 42.9, 4.2, 45.2, 7.8),
    ("Île-de-France", 48.1, 1.4, 49.3, 3.6),
    ("Guadeloupe", 15.8, -61.9, 16.6, -60.9),
    ("Martinique", 14.3, -61.3, 14.9, -60.7),
    ("Guyane", 2.0, -54.7, 5.9, -51.6),
    ("La Réunion", -21.4, 55.2, -20.8, 55.9),
    ("Mayotte", -13.1, 45.0, -12.6, 45.3),
]

OVERPASS_SERVERS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]


def download_region(session, name, south, west, north, east, depth=0):
    query = f"""
    [out:json][timeout:30];
    (
      nwr["amenity"="fuel"]["brand"~"total",i]({south},{west},{north},{east});
      nwr["amenity"="fuel"]["name"~"total",i]({south},{west},{north},{east});
      nwr["amenity"="fuel"]["operator"~"total",i]({south},{west},{north},{east});
    );
    out center tags;
    """
    errors = []
    for server in OVERPASS_SERVERS:
        try:
            print(f"Secteur {name} — interrogation {server}", flush=True)
            response = session.post(
                server, data={"data": query}, timeout=(8, 35)
            )
            response.raise_for_status()
            payload = response.json()
            if "elements" not in payload:
                raise RuntimeError("Réponse Overpass sans liste elements")
            elements = payload["elements"]
            print(f"Secteur {name} : {len(elements)} objets reçus", flush=True)
            return elements
        except Exception as exc:
            message = f"{server}: {type(exc).__name__}: {exc}"
            errors.append(message)
            print(f"Échec {name} — {message}", flush=True)
            time.sleep(1)

    # Si les trois instances sont saturées sur cette zone, on réduit la
    # requête en quatre sous-secteurs avant d'abandonner.
    if depth < 2:
        mid_lat = (south + north) / 2
        mid_lon = (west + east) / 2
        print(f"Subdivision automatique de {name} (niveau {depth + 1})", flush=True)
        sectors = [
            ("sud-ouest", south, west, mid_lat, mid_lon),
            ("sud-est", south, mid_lon, mid_lat, east),
            ("nord-ouest", mid_lat, west, north, mid_lon),
            ("nord-est", mid_lat, mid_lon, north, east),
        ]
        combined = []
        for suffix, s, w, n, e in sectors:
            combined.extend(download_region(
                session, f"{name}/{suffix}", s, w, n, e, depth + 1
            ))
        return combined

    raise RuntimeError(
        f"Collecte impossible pour {name} après 4 niveaux de subdivision. "
        + " | ".join(errors)
    )


def download_overpass():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "STATIONS-TOTAL-FRANCE/2.0 (GitHub Actions)"
    })
    unique = {}
    for index, (name, south, west, north, east) in enumerate(REGIONS, 1):
        print(f"=== {index}/{len(REGIONS)} : {name} ===", flush=True)
        elements = download_region(session, name, south, west, north, east)
        for element in elements:
            unique[f'{element["type"]}:{element["id"]}'] = element
    if not unique:
        raise RuntimeError("Aucune station reçue : référentiel précédent conservé")
    print(f"Collecte terminée : {len(unique)} objets OSM uniques", flush=True)
    return {"elements": list(unique.values())}


def main():
    data = download_overpass()
    items = {}

    for element in data.get("elements", []):
        tags = element.get("tags", {})
        label = " ".join([
            tags.get("brand", ""), tags.get("name", ""), tags.get("operator", "")
        ])
        if not re.search(r"total", label, re.I):
            continue

        center = element.get("center", {})
        latitude = element.get("lat", center.get("lat"))
        longitude = element.get("lon", center.get("lon"))
        if latitude is None or longitude is None:
            continue

        name = tags.get("name") or tags.get("brand") or tags.get("operator") or "Station Total"
        element_type = element["type"]
        element_id = element["id"]
        item = {
            "osm_id": f"{element_type}:{element_id}",
            "nom": name,
            "enseigne": (
                "Total Access"
                if re.search(r"total\s*access", label, re.I)
                else "TotalEnergies"
            ),
            "adresse": ", ".join(filter(None, [
                tags.get("addr:housenumber"), tags.get("addr:street"),
                tags.get("addr:postcode"), tags.get("addr:city"),
            ])),
            "code_postal": tags.get("addr:postcode", ""),
            "commune": tags.get("addr:city", ""),
            "latitude": float(latitude),
            "longitude": float(longitude),
            "horaires": tags.get("opening_hours", ""),
            "osm_url": f"https://www.openstreetmap.org/{element_type}/{element_id}",
        }
        items[item["osm_id"]] = item

    if not items:
        raise RuntimeError("Aucune station Total trouvée : fichier précédent conservé")

    rows = sorted(items.values(), key=lambda item: (
        item["code_postal"], item["commune"], item["nom"]
    ))
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "OpenStreetMap / Overpass",
        "count": len(rows),
        "items": rows,
    }
    (DATA / "stations_osm.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"{len(rows)} stations candidates identifiées dans OpenStreetMap", flush=True)


if __name__ == "__main__":
    main()
