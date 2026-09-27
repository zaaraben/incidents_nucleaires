# Mise à jour mensuelle des données

Le script `maj_incidents_nucleaires.py` produit le fichier chargé par la
carte, `incidents_nucleaires/data/centrales_incidents.geojson`, à partir du
fichier Excel mensuel (`AAAAMMJJ_incidents_nucleaires.xlsx`).

Il remplace les notebooks `20260327_incidents_nucleaires.ipynb` et
`incidents_nucleaires_builder.ipynb`, qui produisaient d'autres fichiers
que celui utilisé par la carte.

## Utilisation

Depuis la racine du dépôt :

```bash
pip install -r scripts/requirements.txt
python scripts/maj_incidents_nucleaires.py chemin/vers/20260801_incidents_nucleaires.xlsx
```

Option `--strict` : n'écrit rien si un incident concerne un site absent du
référentiel.

## Onglets lus dans le fichier Excel

| Onglet | Contenu | Colonnes nécessaires |
|---|---|---|
| `incidents_nucleaires` | Incidents publiés le mois écoulé | `date_releve`, `nom_site`, `niveau_ines`, `date_incident`, `date_declaration`, `date_publication`, `description`, `hyperlien` |
| `referentiel_sites` | Les centrales | `nom_site`, `coordonnees` (ex. `47° 30′ 35″ N, 2° 52′ 30″ E`), `hyperlien` (page ASNR) |
| `nombre_total_incidents` | Total historique par centrale | `nom_site`, `nb_total_incidents` |

Les autres onglets sont ignorés. Les lignes vides, valeurs isolées et
en-têtes répétés de l'onglet `incidents_nucleaires` sont écartés.

Le mois affiché est celui qui précède `date_releve` (relevé du 01/08/2026 →
« publiés en juillet 2026 »).

## Ce que le script modifie

- `incidents_nucleaires/data/centrales_incidents.geojson` : les données
- `incidents_nucleaires.xml` : le titre (« … publiés en juillet 2026 »)
- `incidents_nucleaires/templates/sites.mst` : la date « Mise à jour : »
- `incidents_nucleaires/data/centrales_incidents.meta.json` : le suivi

## Contrôles

Arrêt sans rien modifier si un onglet ou une colonne manque, si une
coordonnée est illisible ou hors de France, ou si une centrale est en double
dans le référentiel.

Simples alertes : site absent du référentiel (ses incidents ne sont pas
affichés), niveau INES absent ou hors 0-7, déclaration antérieure à
l'incident, total historique manquant.

## Automatisation

Déposer le fichier Excel du mois dans le dossier `sources/` (sur le site
GitHub : *Add file › Upload files*). Le workflow
`.github/workflows/maj-incidents.yml` se déclenche alors, lance ce script et
enregistre la carte mise à jour dans le dépôt.

- Erreur (onglet, colonne, coordonnée) : le workflow échoue, GitHub envoie un e-mail.
- Site absent du référentiel : une issue est ouverte.
- Relancer à la main : onglet **Actions** › « Mise à jour des incidents » ›
  « Run workflow » (le fichier le plus récent de `sources/` est utilisé).
