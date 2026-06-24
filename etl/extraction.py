import json

BASE_PATH = "./data/"


def extract(filename: str, required_fields: list[str]) -> list[dict[str, str | int]]:
    """Extract from a JSON file a list of entries and return a dict for the required fields"""
    with open(BASE_PATH + filename + ".json", "r") as f:
        content = json.load(f)

    data = []
    for entry in content:
        datum = {key: value for key, value in entry.items() if key in required_fields}

        data.append(datum)

    return data
