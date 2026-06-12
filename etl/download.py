import json
import os
from time import sleep

import httpx

LEGISLATURE = 17
# Liste des apis à télécharger
APIS = ["dossiers", "documents", "amendements"]

MAX_PAGE = 1000
BATCH_SIZE = 500
BASE_URL = "https://parlement.tricoteuses.fr/"


def save(data, filename):
    os.makedirs("./data", exist_ok=True)
    with open("./data/" + filename + ".json", "w") as f:
        json.dump(data, f)


def get(page, base_url):
    params = f"?page={page}&perPage={BATCH_SIZE}&legislature={LEGISLATURE}"
    url = base_url + params
    try:
        response = httpx.get(url, timeout=20)
        response.raise_for_status()
        return response
    except Exception as e:
        print(f"Error in Download: {e}")
        return None


def get_api_data(api):
    base_url = BASE_URL + api + "/json"
    data = []
    for page in range(1, MAX_PAGE):
        print("\tpage: ", page)
        response = get(page, base_url)
        if response is None:
            break

        current_batch_data = response.json()
        if len(current_batch_data["data"]) == 0:
            break
        data.extend(current_batch_data["data"])

        sleep(0.3)
    return data


def run_download():
    for api in APIS:
        print("Fetching ", api)
        data = get_api_data(api)
        save(data, api)


if __name__ == "__main__":
    run_download()
