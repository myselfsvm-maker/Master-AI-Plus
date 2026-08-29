import hashlib

import config
import db


def _hash(key: str) -> str:
    """Short, non-reversible fingerprint so we never store raw keys in the DB."""
    return hashlib.sha256(key.encode()).hexdigest()[:12]


class NoAvailableBackend(Exception):
    pass


def get_next_backend(preferred_model_name: str, tried: set):
    """
    Returns (model_name, model_id, api_key) for the next usable combination,
    starting from the user's preferred model (or the top of the chain if 'auto'),
    skipping anything already tried this turn or currently on cooldown.
    """
    chain = config.MODEL_CHAIN
    names = [m["name"] for m in chain]

    if preferred_model_name != "auto" and preferred_model_name in names:
        start = names.index(preferred_model_name)
        order = chain[start:] + chain[:start]
    else:
        order = chain

    for entry in order:
        model_name, model_id = entry["name"], entry["model"]
        for key in config.OPENROUTER_KEYS:
            combo = (model_name, key)
            if combo in tried:
                continue
            if db.is_exhausted(_hash(key), model_id):
                continue
            return model_name, model_id, key

    raise NoAvailableBackend("All configured models/keys are currently rate-limited or exhausted.")


def mark_key_exhausted(model_id: str, key: str):
    db.mark_exhausted(_hash(key), model_id, config.COOLDOWN_SECONDS)
