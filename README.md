# STATIONS-TOTAL-FRANCE
Référentiel national des stations TotalEnergies et Total Access, avec prix carburants, exports et flux RSS.

## Sources et fréquence
- Enseignes et coordonnées : OpenStreetMap / Overpass, recherche quotidienne des stations dont brand, name ou operator mentionne Total.
- Prix : flux instantané officiel du ministère de l'Économie / DGCCRF, actualisé par la source environ toutes les 10 minutes.
- Le workflow de prix s'exécute toutes les 15 minutes ; la découverte des stations est quotidienne.
- Les prix ne sont associés que si un point officiel est trouvé à 200 m ou moins de la station OSM. La distance et le statut de rapprochement sont conservés pour transparence.
- L'absence de prix ne signifie pas que la station ne vend pas le carburant.
- Attribution : OpenStreetMap (ODbL) et ministère de l'Économie / DGCCRF (Licence Ouverte).

## Flux et exports
- RSS : https://raw.githubusercontent.com/Hfoury/STATIONS-TOTAL-FRANCE/main/data/flux.rss
- JSON : https://raw.githubusercontent.com/Hfoury/STATIONS-TOTAL-FRANCE/main/data/stations_total.json
- CSV : https://raw.githubusercontent.com/Hfoury/STATIONS-TOTAL-FRANCE/main/data/stations_total.csv

## Lancement manuel
GitHub → Actions → lancer d'abord « Découverte quotidienne des stations Total », puis « Actualisation des prix Total ».
