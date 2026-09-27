#!/usr/bin/env python3
"""Mise à jour de la carte « Incidents nucléaires » (mesdonneeslocales.fr).

Lit le fichier Excel mensuel (AAAAMMJJ_incidents_nucleaires.xlsx) et produit
incidents_nucleaires/data/centrales_incidents.geojson : un point par centrale,
avec la liste des incidents publiés le mois écoulé.

Onglets utilisés :
  - incidents_nucleaires   : incidents publiés le mois écoulé
  - referentiel_sites      : nom, coordonnées (DMS), lien ASNR de chaque centrale
  - nombre_total_incidents : nombre total d'incidents historique par centrale

Le script met aussi à jour :
  - le titre de la carte (incidents_nucleaires.xml : « … publiés en juillet 2026 »)
  - la date « Mise à jour : » de la fiche (templates/sites.mst)
  - un fichier de suivi (data/centrales_incidents.meta.json)

Exemple :
  python scripts/maj_incidents_nucleaires.py sources/20260801_incidents_nucleaires.xlsx

Codes de sortie :
  0  mise à jour effectuée
  1  erreur : onglet ou colonne absent, coordonnée illisible…
  2  centrales inconnues du référentiel (seulement avec --strict)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import warnings
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

RACINE = Path(__file__).resolve().parent.parent
APP = RACINE / "incidents_nucleaires"

SORTIE_GEOJSON = APP / "data" / "centrales_incidents.geojson"
SORTIE_META = APP / "data" / "centrales_incidents.meta.json"
FICHIER_XML = RACINE / "incidents_nucleaires.xml"
FICHIER_MST = APP / "templates" / "sites.mst"

ONGLET_INCIDENTS = "incidents_nucleaires"
ONGLET_SITES = "referentiel_sites"
ONGLET_TOTAL = "nombre_total_incidents"

COLONNES_INCIDENTS = ["date_releve", "nom_site", "niveau_ines", "date_incident",
                      "date_declaration", "date_publication", "description", "hyperlien"]
COLONNES_SITES = ["nom_site", "coordonnees", "hyperlien"]
COLONNES_TOTAL = ["nom_site", "nb_total_incidents"]

MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"]

FUSEAU = ZoneInfo("Europe/Paris")

# Variantes de noms rencontrées dans les fichiers -> nom du référentiel
SITE_ALIASES = {
    "St-Laurent": "Saint-Laurent",
    "St Laurent": "Saint-Laurent",
    "St Laurent des Eaux": "Saint-Laurent",
    "Saint-Laurent-des-Eaux": "Saint-Laurent",
    "Dampierre-en-Burly": "Dampierre",
    "Dampierre en Burly": "Dampierre",
    "Chooz": "Chooz B",
    "Chooz-B": "Chooz B",
    "Chinon": "Chinon B",
    "Chinon-B": "Chinon B",
    "Cruas-Meysse": "Cruas",
    "Cruaz-Meysse": "Cruas",
}


class ErreurStructure(Exception):
    """Le fichier Excel n'a pas la structure attendue."""


# --------------------------------------------------------------------------
# Nettoyage (repris du notebook incidents_nucleaires_builder)
# --------------------------------------------------------------------------

def normalize_text(value):
    """Espaces, apostrophes typographiques, symboles DMS."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    s = str(value)
    s = s.replace("\xa0", " ").replace("’", "'").replace("‘", "'")
    s = s.replace("′", "'").replace("″", '"')
    s = " ".join(s.split()).strip()
    return s or None


def normalize_site_name(value):
    s = normalize_text(value)
    return SITE_ALIASES.get(s, s) if s else None


def texte_brut(value):
    """Texte sans retouche des apostrophes (descriptions, liens)."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    s = str(value).strip()
    return s or None


def to_iso_date(value):
    """20260412, Timestamp ou chaîne -> '2026-04-12'."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        s = str(int(value))
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 else None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.strftime("%Y-%m-%d")
    s = normalize_text(value)
    if not s:
        return None
    if re.fullmatch(r"\d{8}", s):
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
    return None if pd.isna(dt) else dt.strftime("%Y-%m-%d")


def dms_to_decimal(dms_str):
    """'47° 30′ 35″ N' -> 47.509722"""
    s = normalize_text(dms_str)
    if not s:
        return None
    s = s.replace("°", "°")
    m = re.search(r"(\d+)\s*°\s*(\d+)\s*'\s*(\d+(?:[.,]\d+)?)\s*\"\s*([NSEWO])", s, re.I)
    if not m:
        raise ErreurStructure(f"Coordonnée non reconnue : {dms_str!r}")
    deg, mn = int(m.group(1)), int(m.group(2))
    sec = float(m.group(3).replace(",", "."))
    decimal = deg + mn / 60 + sec / 3600
    return -decimal if m.group(4).upper() in ("S", "O", "W") else decimal


def parse_lat_lon(coordonnees):
    s = normalize_text(coordonnees)
    if not s or "," not in s:
        raise ErreurStructure(f"Coordonnées illisibles : {coordonnees!r}")
    lat, lon = (dms_to_decimal(p) for p in s.split(",", 1))
    return lat, lon


# --------------------------------------------------------------------------
# Lecture du fichier Excel
# --------------------------------------------------------------------------

def lire_onglet(xls: pd.ExcelFile, onglet: str, colonnes: list[str]) -> pd.DataFrame:
    if onglet not in xls.sheet_names:
        raise ErreurStructure(f"Onglet absent : {onglet}. Onglets du fichier : {xls.sheet_names}")
    df = xls.parse(onglet)
    df.columns = [str(c).strip() for c in df.columns]
    manquantes = [c for c in colonnes if c not in df.columns]
    if manquantes:
        raise ErreurStructure(
            f"Onglet {onglet} : colonnes absentes {manquantes}. Trouvées : {list(df.columns)}"
        )
    return df


def lire_incidents(xls: pd.ExcelFile) -> pd.DataFrame:
    df = lire_onglet(xls, ONGLET_INCIDENTS, COLONNES_INCIDENTS)
    df["nom_site"] = df["nom_site"].apply(normalize_site_name)
    # Lignes parasites : vides, valeurs isolées, en-têtes répétés
    df = df[df["nom_site"].notna() & (df["nom_site"] != "nom_site")].copy()
    df["niveau_ines"] = pd.to_numeric(df["niveau_ines"], errors="coerce")
    for col in ["date_releve", "date_incident", "date_declaration", "date_publication"]:
        df[col] = df[col].apply(to_iso_date)
    df["description"] = df["description"].apply(texte_brut)
    df["hyperlien"] = df["hyperlien"].apply(texte_brut)
    return df.reset_index(drop=True)


def lire_sites(xls: pd.ExcelFile) -> pd.DataFrame:
    df = lire_onglet(xls, ONGLET_SITES, COLONNES_SITES)
    df["nom_site"] = df["nom_site"].apply(normalize_site_name)
    df = df[df["nom_site"].notna()].copy()
    doublons = df[df["nom_site"].duplicated()]["nom_site"].tolist()
    if doublons:
        raise ErreurStructure(f"Centrales en double dans le référentiel : {doublons}")
    coords = df["coordonnees"].apply(parse_lat_lon)
    df["latitude"] = coords.str[0]
    df["longitude"] = coords.str[1]
    df["hyperlien"] = df["hyperlien"].apply(texte_brut)
    return df.reset_index(drop=True)


def lire_totaux(xls: pd.ExcelFile) -> dict:
    df = lire_onglet(xls, ONGLET_TOTAL, COLONNES_TOTAL)
    df["nom_site"] = df["nom_site"].apply(normalize_site_name)
    df = df[df["nom_site"].notna()]
    return {
        r.nom_site: int(r.nb_total_incidents)
        for r in df.itertuples() if pd.notna(r.nb_total_incidents)
    }


# --------------------------------------------------------------------------
# Contrôles
# --------------------------------------------------------------------------

def controler(incidents: pd.DataFrame, sites: pd.DataFrame, totaux: dict) -> dict:
    """Erreurs bloquantes -> exception ; anomalies -> liste d'alertes."""
    alertes = []

    for r in sites.itertuples():
        # Emprise large : métropole
        if not (41 <= r.latitude <= 52 and -6 <= r.longitude <= 10):
            raise ErreurStructure(
                f"Coordonnées hors de France pour {r.nom_site} : {r.latitude}, {r.longitude}"
            )

    inconnus = sorted(set(incidents["nom_site"]) - set(sites["nom_site"]))

    ines_ko = incidents[incidents["niveau_ines"].isna() |
                        ~incidents["niveau_ines"].between(0, 7)]
    for r in ines_ko.itertuples():
        alertes.append(f"Niveau INES absent ou hors 0-7 : {r.nom_site} ({r.date_publication})")

    for r in incidents.itertuples():
        if r.date_incident and r.date_declaration and r.date_declaration < r.date_incident:
            alertes.append(
                f"Déclaration ({r.date_declaration}) antérieure à l'incident "
                f"({r.date_incident}) : {r.nom_site}"
            )
        if not r.date_publication:
            alertes.append(f"Date de publication absente : {r.nom_site}")

    sans_total = sorted(set(sites["nom_site"]) - set(totaux))
    if sans_total:
        alertes.append(f"Total historique absent pour : {', '.join(sans_total)} (compté 0)")

    return {"centrales_inconnues": inconnus, "alertes": alertes}


# --------------------------------------------------------------------------
# Construction du GeoJSON
# --------------------------------------------------------------------------

def construire_geojson(incidents: pd.DataFrame, sites: pd.DataFrame, totaux: dict) -> dict:
    features = []
    for s in sites.itertuples():
        lignes = incidents[incidents["nom_site"] == s.nom_site]
        liste = [
            {
                "niveau_ines": int(r.niveau_ines) if pd.notna(r.niveau_ines) else None,
                "date_incident": r.date_incident,
                "date_declaration": r.date_declaration,
                "date_publication": r.date_publication,
                "description": r.description,
                "url_incident": r.hyperlien,
            }
            for r in lignes.itertuples()
        ]
        liste.sort(key=lambda i: i["date_publication"] or "", reverse=True)
        niveaux = [i["niveau_ines"] for i in liste if i["niveau_ines"] is not None]
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [round(float(s.longitude), 6), round(float(s.latitude), 6)],
            },
            "properties": {
                "nom_site": s.nom_site,
                "nb_incidents_affiches": len(liste),
                "nb_total_incidents": totaux.get(s.nom_site, 0),
                "ines_max": max(niveaux, default=0),
                "a_des_incidents": bool(liste),
                "url_asnr": s.hyperlien,
                "incidents": liste,
            },
        })

    # Centrales avec incidents d'abord (publication la plus récente en tête),
    # puis les autres dans l'ordre du référentiel.
    avec = [f for f in features if f["properties"]["incidents"]]
    sans = [f for f in features if not f["properties"]["incidents"]]
    avec.sort(key=lambda f: f["properties"]["incidents"][0]["date_publication"] or "",
              reverse=True)
    features = avec + sans

    return {
        "type": "FeatureCollection",
        "metadata": {
            "generated": datetime.now(FUSEAU).strftime("%Y-%m-%dT%H:%M:%S"),
            "nb_sites": len(features),
            "nb_incidents_affiches": sum(f["properties"]["nb_incidents_affiches"] for f in features),
            "nb_total_incidents": sum(f["properties"]["nb_total_incidents"] for f in features),
        },
        "features": features,
    }


# --------------------------------------------------------------------------
# Titre et date d'affichage
# --------------------------------------------------------------------------

def mois_des_publications(incidents: pd.DataFrame, fichier: Path) -> tuple[int, int]:
    """Mois couvert = mois précédant la date de relevé (20260801 -> juillet 2026).
    À défaut, date au début du nom de fichier."""
    releves = incidents["date_releve"].dropna()
    if not releves.empty:
        releve = releves.mode().iloc[0]
    else:
        m = re.match(r"(\d{8})", fichier.name)
        if not m:
            raise ErreurStructure(
                "Impossible de déterminer le mois : pas de date_releve ni de date "
                "AAAAMMJJ au début du nom de fichier."
            )
        releve = to_iso_date(m.group(1))
    annee, mois = int(releve[:4]), int(releve[5:7])
    return (annee - 1, 12) if mois == 1 else (annee, mois - 1)


def maj_titre(annee: int, mois: int) -> None:
    texte = FICHIER_XML.read_text(encoding="utf-8")
    nouveau, n = re.subn(r"publiés en [a-zéû]+ \d{4}",
                         f"publiés en {MOIS_FR[mois - 1]} {annee}", texte)
    if n == 0:
        print(f"ATTENTION : titre non trouvé dans {FICHIER_XML.name}, non modifié.")
        return
    FICHIER_XML.write_text(nouveau, encoding="utf-8")


def maj_date_template(jour: date) -> None:
    texte = FICHIER_MST.read_text(encoding="utf-8")
    nouveau, n = re.subn(r"Mise à jour : \d{2}/\d{2}/\d{4}",
                         f"Mise à jour : {jour.strftime('%d/%m/%Y')}", texte)
    if n == 0:
        print(f"ATTENTION : date non trouvée dans {FICHIER_MST.name}, non modifiée.")
        return
    FICHIER_MST.write_text(nouveau, encoding="utf-8")


# --------------------------------------------------------------------------
# Programme principal
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("fichier", type=Path, help="Fichier Excel du mois")
    parser.add_argument("--strict", action="store_true",
                        help="Échouer si une centrale est absente du référentiel")
    args = parser.parse_args(argv)

    print(f"== Incidents nucléaires : {args.fichier.name} ==")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # avertissements openpyxl sans intérêt
            xls = pd.ExcelFile(args.fichier)
            incidents = lire_incidents(xls)
            sites = lire_sites(xls)
            totaux = lire_totaux(xls)
        diag = controler(incidents, sites, totaux)
        annee, mois = mois_des_publications(incidents, args.fichier)
        geojson = construire_geojson(incidents, sites, totaux)
    except ErreurStructure as e:
        print(f"ERREUR : {e}")
        return 1

    meta = geojson["metadata"]
    print(f"Mois couvert         : {MOIS_FR[mois - 1]} {annee}")
    print(f"Centrales            : {meta['nb_sites']}")
    print(f"Incidents du mois    : {meta['nb_incidents_affiches']}")
    for a in diag["alertes"]:
        print(f"ATTENTION : {a}")
    if diag["centrales_inconnues"]:
        print("ATTENTION : incidents sur des sites absents du référentiel "
              f"(non affichés) : {', '.join(diag['centrales_inconnues'])}")
        if args.strict:
            print("Mode strict : aucune donnée écrite.")
            return 2

    SORTIE_GEOJSON.write_text(
        json.dumps(geojson, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    maj_titre(annee, mois)
    aujourdhui = datetime.now(FUSEAU).date()
    maj_date_template(aujourdhui)
    SORTIE_META.write_text(json.dumps({
        "mois_publications": f"{annee}-{mois:02d}",
        "source": args.fichier.name,
        "date_traitement": aujourdhui.isoformat(),
        "nb_incidents_affiches": meta["nb_incidents_affiches"],
        "centrales_inconnues": diag["centrales_inconnues"],
        "alertes": diag["alertes"],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Écrit : {SORTIE_GEOJSON.relative_to(RACINE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
