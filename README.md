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

L'API propose de nombreux endpoints.


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
Il contient la connexion PostgreSQL (`PG_*`) et la configuration du modèle de langage
utilisé par l'analyse des amendements (`LLM_*`, voir plus bas).

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

# Analyse : détection des mentions de collaboration externe

Objectif : repérer les amendements dont l'exposé sommaire déclare une collaboration ou une
inspiration avec une **entité externe** (lobby, syndicat, association, entreprise, fédération
professionnelle, ONG…) — formulations du type « travaillé avec… », « en concertation avec… »,
« inspiré de… ».

Version **v1 exploratoire, sans pré-filtre** : chaque amendement est soumis à un modèle de langage
(`analysis/detect_mentions.py`).

## Prérequis

1. La base doit être alimentée (table `amendements` peuplée) — voir les sections ETL ci-dessus.
2. Configurer l'accès au modèle de langage dans `.env`. Le script utilise le SDK OpenAI contre
   **n'importe quelle API compatible OpenAI** (Scaleway, OpenRouter…) via trois variables :

```dotenv
LLM_API_KEY=...                              # clé du provider
LLM_BASE_URL=https://openrouter.ai/api/v1    # endpoint OpenAI-compatible
LLM_MODEL=qwen/qwen3-30b-a3b                  # identifiant exact du modèle
```

Changer de provider = changer ces trois lignes, rien d'autre.

## Lancer une analyse

```bash
# Sur les 50 premiers amendements (par ordre de dépôt)
just detect-mentions

# Sur 100 amendements tirés aléatoirement dans tout le corpus
just detect-mentions 100 --random

# Idem, en persistant les résultats dans la table amendement_mentions
just detect-mentions 100 --random --persist

# Équivalent sans just :
uv run python -m analysis.detect_mentions --limit 100 --random --persist
```

Options (`uv run python -m analysis.detect_mentions --help`) :

| Option      | Effet                                                                       |
| ----------- | --------------------------------------------------------------------------- |
| `--limit N` | Nombre d'amendements à analyser (défaut : 50).                              |
| `--offset N`| Décalage dans l'échantillon déterministe (ignoré avec `--random`).          |
| `--random`  | Tirage aléatoire sur tout le corpus (utile car les mentions sont rares).    |
| `--delay S` | Pause en secondes entre deux appels (throttle anti rate-limit, défaut : 4). |
| `--persist` | Écrit aussi les mentions dans la table `amendement_mentions`.               |

## Sorties

- **JSONL brut** : `analysis/output/mentions_sample.jsonl` (une ligne par amendement, dossier
  gitignoré). Réécrit à chaque exécution.
- **Récap console** : nombre d'amendements avec mention et fréquence des formulations rencontrées.
- **Base** (avec `--persist`) : table `amendement_mentions`, une ligne par mention détectée
  (`amendementUid`, `citation`, `formulation`, `entite`, `typeEntite`, `externe`, `modele`,
  `createdAt`). L'écriture est idempotente par amendement (une nouvelle passe remplace ses lignes).

## Tables d'analyse et rebuild

`amendement_mentions` est une **table d'analyse** : elle n'est pas listée dans `ETL_TABLES`
(`etl/database.py`) et **survit donc à un `db-rebuild`**, contrairement à `amendements`/`dossiers`
qui sont détruites puis rechargées. Sa colonne `amendementUid` est une référence *molle* vers
`amendements.uid` (pas de `ForeignKey`), afin qu'aucune contrainte ne bloque le drop de la table ETL.
Pour ajouter une nouvelle analyse, créer un modèle sur ce principe (hors `ETL_TABLES`).
