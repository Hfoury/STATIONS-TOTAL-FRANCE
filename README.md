# STATIONS-TOTAL-FRANCE

Référentiel des stations TotalEnergies et Total Access, avec prix carburants, exports et flux RSS.

## Sources et fréquence
- Enseignes et coordonnées : OpenStreetMap via les 22 extraits régionaux métropolitains Geofabrik, traités localement avec PyOsmium.
- Les extraits Geofabrik suivent les anciennes régions françaises, et non les 18 régions administratives actuelles.
- Découverte quotidienne des stations à 04:40 UTC.
- Prix : flux instantané officiel du ministère de l'Économie / DGCCRF, actualisé par la source environ toutes les 10 minutes.
- Le workflow de prix s'exécute toutes les 15 minutes et après une découverte des stations réussie.
- Les prix ne sont associés que si un point officiel est trouvé à 200 m ou moins de la station OSM. La distance et le statut de rapprochement sont conservés pour transparence.
- L'absence de prix ne signifie pas que la station ne vend pas le carburant.
- Attribution : OpenStreetMap (ODbL), extraits Geofabrik, et ministère de l'Économie / DGCCRF (Licence Ouverte).

## Flux et exports
- RSS : https://raw.githubusercontent.com/Hfoury/STATIONS-TOTAL-FRANCE/main/data/flux.rss
- JSON : https://raw.githubusercontent.com/Hfoury/STATIONS-TOTAL-FRANCE/main/data/stations_total.json
- CSV : https://raw.githubusercontent.com/Hfoury/STATIONS-TOTAL-FRANCE/main/data/stations_total.csv

## Lancement manuel
GitHub → Actions → lancer d'abord « Découverte quotidienne des stations Total », puis « Actualisation des prix Total ».
