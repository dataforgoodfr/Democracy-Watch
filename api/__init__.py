"""Couche de lecture : accès aux données et API JSON publique.

Toute la logique (SQL, agrégations, similarité vectorielle) vit ici, à côté de
l'ETL et des modèles qu'elle réutilise (`models/`, `etl/database.py`,
`etl/vectordb/`). Les pages HTML de `web/` appellent les mêmes fonctions de
service en direct, sans aller-retour HTTP ; `/api/**` les publie pour les
consommateurs tiers.
"""
