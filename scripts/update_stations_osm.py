import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

QUERY = """
[out:json][timeout:240];
area["ISO3166-1"="FR"][admin_level=2]->.fr;
(
  nwr["amenity"="fuel"]["brand"~"total",i](area.fr);
  nwr["amenity"="fuel"]["name"~"total",i](area.fr);
  nwr["amenity"="fuel"]["operator"~"total",i](area.fr);
);
out center tags;
"""

OVERPASS_SERVERS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]


def download_overpass():
    errors = []
    headers = {"User-Agent": "STATIONS-TOTAL-FRANCE/1.1 (GitHub Actions)"}

    # On essaie plusieurs instances publiques : une panne ne bloque plus toute la collecte.
    for url in OVERPASS_SERVERS:
        for attempt in range(2):
            try:
                print(f"Interrogation Overpass : {url} (essai {attempt + 1}/2)")
                response = requests.post(
                    url,
                    data={"data": QUERY},
                    headers=headers,
                    timeout=(30, 300),
                )
                response.raise_for_status()
                payload = response.json()
                if "elements" not in payload:
                    raise RuntimeError("Réponse Overpass sans liste 'elements'")
                return payload
            except (requests.exceptions.RequestException, ValueError, RuntimeError) as exc:
                message = f"{url} : {type(exc).__name__} - {exc}"
                print(message)
                errors.append(message)

    raise RuntimeError(
        "Tous les serveurs OpenStreetMap/Overpass sont indisponibles. "
        + " | ".join(errors)
    )


def main():
    data = download_overpass()
    items = {}

    for element in data.get("elements", []):
        tags = element.get("tags", {})
        label = " ".join(
            [tags.get("brand", ""), tags.get("name", ""), tags.get("operator", "")]
        )
        if not re.search(r"total", label, re.I):
            continue

        center = element.get("center", {})
        latitude = element.get("lat", center.get("lat"))
        longitude = element.get("lon", center.get("lon"))
        if latitude is None or longitude is None:
            continue

        name = (
            tags.get("name")
            or tags.get("brand")
            or tags.get("operator")
            or "Station Total"
        )
        element_type = element["type"]
        element_id = element["id"]

        item = {
            "osm_id": f"{element_type}:{element_id}",
            "nom": name,
            "enseigne": (
                "Total Access"
                if re.search(r"total\\s*access", label, re.I)
                else "TotalEnergies"
            ),
            "adresse": ", ".join(
                filter(
                    None,
                    [
                        tags.get("addr:housenumber"),
                        tags.get("addr:street"),
                        tags.get("addr:postcode"),
                        tags.get("addr:city"),
                    ],
                )
            ),
            "code_postal": tags.get("addr:postcode", ""),
            "commune": tags.get("addr:city", ""),
            "latitude": float(latitude),
            "longitude": float(longitude),
            "horaires": tags.get("opening_hours", ""),
            "osm_url": f"https://www.openstreetmap.org/{element_type}/{element_id}",
        }
        items[item["osm_id"]] = item

    if not items:
        raise RuntimeError(
            "Aucune station Total trouvée : le fichier précédent est conservé"
        )

    rows = sorted(
        items.values(),
        key=lambda item: (
            item["code_postal"],
            item["commune"],
            item["nom"],
        ),
    )

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "OpenStreetMap / Overpass",
        "count": len(rows),
        "items": rows,
    }
    (DATA / "stations_osm.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"{len(rows)} stations candidates identifiées dans OpenStreetMap")


if __name__ == "__main__":
    main()
