# Assemblée Nationale

TODO: petite présentation du projet.

## Description des données

Nous utilisons l'api des [tricoteuses](https://www.tricoteuses.fr/) pour récupérer les données. Voici le lien vers la [documentation](https://parlement.tricoteuses.fr/docs#description/introduction).


L'Assemblée Nationale travaille à partir de dossier legislatif. Un dossier législatif permet de suivre l'évolution d'un texte législatif: en commission, au sénat, amendements... Deux types de textes législatifs nous intéressent: proposition de loi proposé par un député, projet de loi proposé par le gouvernement.

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

### Dépendences à installer

- [Installation de Python](#installation-de-python)
- [Installation d'UV](https://docs.astral.sh/uv/)

### Setup
```bash
uv sync
```

### Usages

#### Télécharger les données sur l'API des tricoteuses

La commande suivante va télécharger sur l'API des [tricoteuses](https://www.tricoteuses.fr/) et créer des fichiers json dans le répertoire `./data/`. Pour rajouter un endpoint, il suffit de modifier la variable `APIS` dans `./etl/download.py`

```bash
uv run etl/download.py
```
