import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import osmium
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
BASE = "https://download.geofabrik.de/europe/france"
REGIONS = [
    "alsace", "aquitaine", "auvergne", "basse-normandie", "bourgogne",
    "bretagne", "centre", "champagne-ardenne", "corse", "franche-comte",
    "haute-normandie", "ile-de-france", "languedoc-roussillon", "limousin",
    "lorraine", "midi-pyrenees", "nord-pas-de-calais", "pays-de-la-loire",
    "picardie", "poitou-charentes", "provence-alpes-cote-d-azur", "rhone-alpes",
]

def tags_dict(tags):
    return {tag.k: tag.v for tag in tags}

def coordinates(obj):
    if isinstance(obj, osmium.osm.Node):
        return (obj.location.lat, obj.location.lon) if obj.location.valid() else None
    points = [(n.lat, n.lon) for n in obj.nodes if n.location.valid()]
    if not points:
        return None
    return (sum(p[0] for p in points) / len(points),
            sum(p[1] for p in points) / len(points))

class StationHandler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.items = {}

    def inspect(self, obj):
        tags = tags_dict(obj.tags)
        if tags.get("amenity") != "fuel":
            return
        label = " ".join((tags.get("brand", ""), tags.get("name", ""), tags.get("operator", "")))
        if not re.search(r"total", label, re.I):
            return
        location = coordinates(obj)
        if location is None:
            return
        kind = "node" if isinstance(obj, osmium.osm.Node) else "way"
        osm_id = f"{kind}:{obj.id}"
        name = tags.get("name") or tags.get("brand") or tags.get("operator") or "Station Total"
        self.items[osm_id] = {
            "osm_id": osm_id,
            "nom": name,
            "enseigne": "Total Access" if re.search(r"total\s*access", label, re.I) else "TotalEnergies",
            "adresse": ", ".join(filter(None, [
                tags.get("addr:housenumber"), tags.get("addr:street"),
                tags.get("addr:postcode"), tags.get("addr:city"),
            ])),
            "code_postal": tags.get("addr:postcode", ""),
            "commune": tags.get("addr:city", ""),
            "latitude": float(location[0]),
            "longitude": float(location[1]),
            "horaires": tags.get("opening_hours", ""),
            "osm_url": f"https://www.openstreetmap.org/{kind}/{obj.id}",
        }

    def node(self, obj):
        self.inspect(obj)

    def way(self, obj):
        self.inspect(obj)

def download(url, path):
    """Télécharge un extrait Geofabrik avec reprises sur erreurs temporaires."""
    headers = {"User-Agent": "STATIONS-TOTAL-FRANCE/3.0 (OpenStreetMap data updater)"}
    temporary_path = path.with_suffix(path.suffix + ".part")
    max_attempts = 6
    retryable_statuses = {429, 500, 502, 503, 504}

    for attempt in range(1, max_attempts + 1):
        try:
            size = 0
            with requests.get(url, headers=headers, stream=True, timeout=(30, 300)) as response:
                if response.status_code in retryable_statuses:
                    retry_after = response.headers.get("Retry-After")
                    try:
                        delay = min(int(retry_after), 180) if retry_after else min(15 * (2 ** (attempt - 1)), 180)
                    except ValueError:
                        delay = min(15 * (2 ** (attempt - 1)), 180)
                    raise requests.exceptions.HTTPError(
                        f"Erreur HTTP temporaire {response.status_code}; nouvelle tentative dans {delay}s",
                        response=response,
                    )
                response.raise_for_status()
                with temporary_path.open("wb") as out:
                    for chunk in response.iter_content(1024 * 1024):
                        if chunk:
                            out.write(chunk)
                            size += len(chunk)

            if size < 1024 * 1024:
                raise RuntimeError(f"Extrait anormalement petit : {url}")

            temporary_path.replace(path)
            print(f"Téléchargé {path.name}: {size / 1024 / 1024:.1f} Mio", flush=True)
            return

        except requests.exceptions.RequestException as error:
            if temporary_path.exists():
                temporary_path.unlink()
            status = getattr(getattr(error, "response", None), "status_code", None)
            if status is not None and status not in retryable_statuses:
                raise
            if attempt == max_attempts:
                raise RuntimeError(
                    f"Échec du téléchargement après {max_attempts} tentatives : {url} ({error})"
                ) from error

            retry_after = getattr(getattr(error, "response", None), "headers", {}).get("Retry-After")
            try:
                delay = min(int(retry_after), 180) if retry_after else min(15 * (2 ** (attempt - 1)), 180)
            except ValueError:
                delay = min(15 * (2 ** (attempt - 1)), 180)
            print(
                f"Téléchargement temporairement indisponible ({error}). "
                f"Tentative {attempt + 1}/{max_attempts} dans {delay}s.",
                flush=True,
            )
            time.sleep(delay)
        except Exception:
            if temporary_path.exists():
                temporary_path.unlink()
            raise

def main():
    unique = {}
    with tempfile.TemporaryDirectory() as temp:
        for index, region in enumerate(REGIONS, 1):
            print(f"=== {index}/{len(REGIONS)} {region} ===", flush=True)
            path = Path(temp) / f"{region}.osm.pbf"
            download(f"{BASE}/{region}-latest.osm.pbf", path)
            handler = StationHandler()
            handler.apply_file(str(path), locations=True)
            unique.update(handler.items)
            print(f"{region}: {len(handler.items)} stations candidates; cumul {len(unique)}", flush=True)
            path.unlink()
    rows = sorted(unique.values(), key=lambda x: (x["code_postal"], x["commune"], x["nom"]))
    if len(rows) < 500:
        raise RuntimeError(f"Collecte incomplète ou anormale ({len(rows)} stations) : anciennes données conservées")
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "OpenStreetMap / Geofabrik (extraits régionaux)",
        "count": len(rows),
        "items": rows,
    }
    target = DATA / "stations_osm.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"PUBLICATION PRÊTE: {len(rows)} stations candidates Total / Total Access", flush=True)

if __name__ == "__main__":
    main()
