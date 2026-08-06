"""Réglages de l'application, lus depuis l'environnement."""

from os import getenv

#: Aucune origine tierce par défaut : l'interface est servie par le même processus,
#: donc de même origine, et n'a besoin d'aucune autorisation CORS.
DEFAULT_ALLOWED_ORIGINS = ""

#: Délai maximal d'une requête SQL : une requête pathologique échoue au lieu de
#: retenir une connexion du pool.
STATEMENT_TIMEOUT_MS = 15_000


def get_api_host() -> str:
    return getenv("API_HOST", "127.0.0.1")


def get_api_port() -> int:
    return int(getenv("API_PORT", "8000"))


def get_allowed_origins() -> list[str]:
    """Origines autorisées en CORS, pour les consommateurs tiers de l'API JSON.

    L'interface HTML est servie par ce même processus : elle est de même origine et
    ne passe jamais par ce réglage. Renseigner `API_ALLOWED_ORIGINS` n'est donc utile
    que pour autoriser une application extérieure à interroger `/api/**`.
    """
    raw = getenv("API_ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def get_pool_size() -> int:
    return int(getenv("API_POOL_SIZE", "10"))
