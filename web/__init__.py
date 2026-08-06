"""Interface web serveur : gabarits Jinja, vues HTML et fichiers statiques.

Les vues appellent directement les fonctions de service de `api/routers/` (pas de
saut HTTP) et rendent du HTML côté serveur. Aucun outillage Node : HTMX gère les
échanges de fragments, Alpine les deux fonctions qui ont besoin de localStorage.
Voir `web/views/` pour les routes.
"""
