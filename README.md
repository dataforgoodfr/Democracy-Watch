# Assemblée Nationale

TODO: petite présentation du projet.

## Description des données

Nous utilisons l'API des [tricoteuses](https://www.tricoteuses.fr/) pour récupérer les données. Voici le lien vers la [documentation](https://parlement.tricoteuses.fr/docs#description/introduction).


L'Assemblée nationale travaille à partir de dossiers législatifs. Un dossier législatif permet de suivre l'évolution d'un texte législatif : en commission, au Sénat, amendements... Deux types de textes législatifs nous intéressent : proposition de loi proposée par un député, projet de loi proposé par le gouvernement.

Voici les différents endpoint: 
* dossiers => `https://parlement.tricoteuses.fr/dossiers`
* texte de loi => `https://parlement.tricoteuses.fr/documents`
* amendements => `https://parlement.tricoteuses.fr/amendements`
* députés => `https://parlement.tricoteuses.fr/acteurs`
* votes => `https://parlement.tricoteuses.fr/scrutins`



[Information sur le chemin d'une loi](https://www.assemblee-nationale.fr/dyn/actualites-accueil-hub/le-parcours-de-la-loi)
[Les documents parlementaires](https://www.assemblee-nationale.fr/dyn/documents-parlementaires)

[Documentation technique de l'API des tricoteuses](https://parlement.tricoteuses.fr/docs#description/introduction)

# Contributing


## Installation

### Dépendances à installer

- [Installation de Python](#installation-de-python)
- [Installation d'UV](https://docs.astral.sh/uv/)

### Setup

1. Installer les dépendances :
```bash
uv sync
```

2. Créer le fichier `.env` à partir de l'exemple, puis l'adapter si besoin :
```bash
cp .env.example .env
```

3. Démarrer PostgreSQL (instance locale définie dans `docker-compose.yml`, sur le port `5432`) :
```bash
docker compose up -d db
```
Les valeurs par défaut de `.env.example` correspondent à ce conteneur (`postgres`/`postgres`, base `ipolitics`).

### Usages

#### Exécuter des commandes

Il y a deux façons d'exécuter des commandes:
* uv run main.py [-h] [-d] [-r] [-e] [-a]
* just

[Just](https://just.systems/man/en/) permet de facilement exécuter des commandes. Si vous ne voulez pas l'installer, vous pouvez toujours utiliser `uv run main.py`

#### Télécharger les données sur l'API des tricoteuses

La commande suivante va télécharger sur l'API des [tricoteuses](https://www.tricoteuses.fr/) et créer des fichiers JSON dans le répertoire `./data/`. Pour rajouter un endpoint, il suffit de modifier la variable `APIS` dans `./etl/download.py`

```bash
uv run main.py -d
# ou
just download
```

#### Construire la base de donnée

```bash
uv run main.py -r
# ou
just db-rebuild
```

#### Exécuter l'ETL

```bash
uv run main.py -e
# ou
just etl
```


#### Recréer la DB et exécuter l'ETL

```bash
uv run main.py -a
# ou
just all
```


## Comment marche l'ETL

Après avoir exécuté `just download`, les données de l'API des tricoteuses sont sauvegardées dans le dossier `./data/` sous la forme de fichiers JSON.
L'ETL permet d'extraire des données de ces fichiers pour les sauvegarder dans la base de données. La base de données est représentée à l'aide de 
modèles créés via [SqlAlchemy](https://docs.sqlalchemy.org/en/20/).

Pour charger **un fichier** en db, il faut rajouter un modèle qui porte le même nom que le fichier sans l'extension.
Pour rajouter **un champ** du json dans la table, il faut rajouter une colonne dans le modèle du même type que le json et du même nom.

L'ETL est capable d'inférer à partir des modèles les fichiers à ouvrir et les champs à charger.

### Exemple


Voici une partie du fichier `./data/dossiers.json`
```json
  {
    "uid": "DLR5L17N54464",
    "dataset": 17,
    "chambre": "AN",
    "numero": "4464",
    ...
    }
```

Je veux rajouter le champ `chambre` dans la DB et faire en sorte que l'ETL l'ajoute de lui-même.
1. Rajouter le champ dans le modèle
```python
class Dossier(Base):
    __tablename__ = "dossiers"

    uid: Mapped[str] = mapped_column(primary_key=True)
    titre: Mapped[str] = mapped_column(String(1000))
    dataset: Mapped[int]
    chambre: Mapped[str] = mapped_column(String(5)) # <-------- nouvelle colonne qui porte le même nom que le champ du fichier json
```

Le champ doit porter le même nom sinon l'ETL ne sera pas capable de le trouver.

2. Exécuter `just all`

## Objets parlementaires chargés


| Table | Endpoint | Contenu | Volume (législature 17) |
|---|---|---|---|
| `acteurs` | `/acteurs` | Députés / sénateurs (référentiel trans-législature) | ~3 100 |
| `organes` | `/organes` | Groupes politiques, commissions, assemblées… | ~5 400 |
| `mandats` | `/mandats` | Jointure acteur ↔ organe (appartenance + dates) | ~25 600 |
| `scrutins` | `/scrutins` | Scrutins publics et résultat agrégé (pour/contre/abstentions) | ~8 200 |
| `groupesVotants` | `/groupesVotants` | Résultat d'un scrutin ventilé par groupe politique | ~121 500 * |
| `documents` | `/documents` | Textes (projets/propositions de loi, rapports…) | ~4 500 |
| `auteursDocument` | `/auteursDocument` | Auteur(s) d'un document | ~20 000 |
| `coSignatairesDocument` | `/coSignatairesDocument` | Co-signataires d'un document | ~116 000 |

\* `groupesVotants` n'expose pas de filtre `legislature` : la table couvre toutes les législatures
(~98 300 lignes se rattachent à un scrutin de la L17, soit 12 groupes pour chacun des 8 192
scrutins concernés). Se scoper par jointure sur `scrutins`.

Les jointures se font par les colonnes `…RefUid` (références molles, nullable, indexées). Schéma
entité-relation ci-dessous — les boîtes ne montrent que les colonnes clés (PK + FK + quelques
champs parlants) ; la liste complète est dans les modèles `models/`.

```mermaid
erDiagram
  dossiers {
    string uid PK
    string titre
    string libelleProcedure
    string statut
  }
  documents {
    string uid PK
    string dossierRefUid FK
    string auteurPrincipalUid FK
    text   titrePrincipal
    string classeLibelle
    bool   texteLoi
    string dateDepot
  }
  amendements {
    string uid PK
    string acteurRefUid FK
    string groupePolitiqueRefUid FK
    string dossierRefUid FK
    string documentRefUid FK
    string scrutinRefUid FK
    string numeroLong
    string divisionArticleDesignation
    text   exposeSommaire
    string sortAmendement
    string dateDepot
  }
  acteurs {
    string uid PK
    string groupeParlementaireUid FK
    string nom
    string prenom
    string chambre
    bool   actif
  }
  organes {
    string uid PK
    string codeType
    string libelleAbrev
    string positionPolitique
  }
  mandats {
    string uid PK
    string acteurRefUid FK
    string organeRefUid FK
    string typeOrgane
    string libQualite
    string dateDebut
    string dateFin
  }
  scrutins {
    string uid PK
    string dossierRefUid FK
    string documentRefUid FK
    string amendementRefUid FK
    string dateScrutin
    text   objet
    string code
    int    pour
    int    contre
    int    abstentions
  }
  groupesVotants {
    string uid PK
    string scrutinRefUid FK
    string organeRefUid FK
    string positionMajoritaire
    int    pour
    int    contre
    int    abstentions
  }
  auteursDocument {
    string uid PK
    string documentRefUid FK
    string acteurRefUid FK
    string qualite
  }
  coSignatairesDocument {
    string uid PK
    string documentRefUid FK
    string acteurRefUid FK
    string dateCosignature
  }

  dossiers    ||--o{ documents             : "dossierRefUid"
  dossiers    ||--o{ amendements           : "dossierRefUid"
  dossiers    ||--o{ scrutins              : "dossierRefUid"
  documents   ||--o{ amendements           : "documentRefUid"
  documents   ||--o{ scrutins              : "documentRefUid"
  documents   ||--o{ auteursDocument       : "documentRefUid"
  documents   ||--o{ coSignatairesDocument : "documentRefUid"
  acteurs     ||--o{ documents             : "auteurPrincipalUid"
  acteurs     ||--o{ amendements           : "acteurRefUid"
  acteurs     ||--o{ mandats               : "acteurRefUid"
  acteurs     ||--o{ auteursDocument       : "acteurRefUid"
  acteurs     ||--o{ coSignatairesDocument : "acteurRefUid"
  organes     ||--o{ acteurs               : "groupeParlementaireUid"
  organes     ||--o{ amendements           : "groupePolitiqueRefUid"
  organes     ||--o{ mandats               : "organeRefUid"
  organes     ||--o{ groupesVotants        : "organeRefUid"
  amendements ||--o{ scrutins              : "amendementRefUid"
  scrutins    ||--o{ amendements           : "scrutinRefUid"
  scrutins    ||--o{ groupesVotants        : "scrutinRefUid"
```

Le lien **amendement ↔ scrutin** est natif, et dans les deux sens : `scrutins.amendementRefUid`
pointe vers l'amendement tranché par le scrutin, et `amendements.scrutinRefUid` vers le scrutin
qui a tranché l'amendement. Le second est le plus large (~11 600 amendements contre ~6 800),
un même scrutin pouvant trancher plusieurs amendements identiques. La jointure reste clairsemée :
la plupart des amendements sont tranchés à main levée, sans scrutin public.
