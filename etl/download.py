import json
import os
from time import sleep

import httpx

LEGISLATURE = 17

# APIs à télécharger, avec pour chacune : faut-il filtrer par législature ?
#   True  -> ajoute &legislature=17. Réservé aux endpoints qui exposent ce filtre
#            dans l'API ET pour lesquels il est pertinent de se limiter à la L17.
#   False -> pas de filtre. Nécessaire pour :
#            - les référentiels trans-législature (`acteurs` renvoie même une 500 avec
#              le filtre ; `organes` est partagé et on le veut complet pour éviter des
#              références orphelines) ;
#            - les endpoints qui n'exposent pas de paramètre `legislature`
#              (`auteursDocument`, `coSignatairesDocument`, `groupesVotants`) : on les
#              scope alors à la L17 par jointure (sur `documents` ou `scrutins`) au
#              moment de l'analyse.
APIS = {
    "dossiers": True,
    "actesLegislatifs": True,
    "documents": True,
    "amendements": True,
    "acteurs": False,
    "organes": False,
    "mandats": True,
    "scrutins": True,
    "auteursDocument": False,
    "coSignatairesDocument": False,
    "groupesVotants": False,
}

BATCH_SIZE = 500
BASE_URL = "https://parlement.tricoteuses.fr/"
TIMEOUT = 90
MAX_RETRIES = 3


def save(data, filename):
    os.makedirs("./data", exist_ok=True)
    with open("./data/" + filename + ".json", "w") as f:
        json.dump(data, f)


def get(page, base_url, with_legislature):
    """Récupère une page, avec quelques tentatives : l'API ferme parfois la
    connexion en cours de route sur les gros volumes."""
    params = f"?page={page}&perPage={BATCH_SIZE}"
    if with_legislature:
        params += f"&legislature={LEGISLATURE}"
    url = base_url + params
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = httpx.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            return response
        except Exception as e:
            print(f"\tpage {page} tentative {attempt}/{MAX_RETRIES}: {e}")
            sleep(3 * attempt)
    return None


def get_api_data(api, with_legislature):
    base_url = BASE_URL + api + "/json"
    data = []
    page = 1
    while True:
        response = get(page, base_url, with_legislature)
        if response is None:
            # On abandonne l'endpoint plutôt que de sauvegarder un fichier tronqué.
            raise RuntimeError(
                f"Abandon de {api} à la page {page} après {MAX_RETRIES} tentatives"
            )

        current_batch_data = response.json()["data"]
        if len(current_batch_data) == 0:
            break
        data.extend(current_batch_data)
        print(f"\t{api} page {page}: +{len(current_batch_data)} (total {len(data)})")
        page += 1
        sleep(0.3)
    return data


def run_download():
    for api, with_legislature in APIS.items():
        print("Fetching ", api)
        data = get_api_data(api, with_legislature)
        save(data, api)


if __name__ == "__main__":
    run_download()
