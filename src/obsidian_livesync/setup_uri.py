"""Setup URI generation — native Python, no Deno required."""

from __future__ import annotations

import base64
import os
import secrets
from urllib.parse import quote

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256, Hash
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

NOUNS = [
    "waterfall",
    "river",
    "breeze",
    "moon",
    "rain",
    "wind",
    "sea",
    "morning",
    "snow",
    "lake",
    "sunset",
    "pine",
    "shadow",
    "leaf",
    "dawn",
    "glitter",
    "forest",
    "hill",
    "cloud",
    "meadow",
    "sun",
    "glade",
    "bird",
    "brook",
    "butterfly",
    "bush",
    "dew",
    "dust",
    "field",
    "fire",
    "flower",
    "firefly",
    "feather",
    "grass",
    "haze",
    "mountain",
    "night",
    "pond",
    "darkness",
    "snowflake",
    "silence",
    "sound",
    "sky",
    "shape",
    "surf",
    "thunder",
    "violet",
    "water",
    "wildflower",
    "wave",
    "resonance",
    "log",
    "dream",
    "cherry",
    "tree",
    "fog",
    "frost",
    "voice",
    "paper",
    "frog",
    "smoke",
    "star",
]

ADJECTIVES = [
    "autumn",
    "hidden",
    "bitter",
    "misty",
    "silent",
    "empty",
    "dry",
    "dark",
    "summer",
    "icy",
    "delicate",
    "quiet",
    "white",
    "cool",
    "spring",
    "winter",
    "patient",
    "twilight",
    "dawn",
    "crimson",
    "wispy",
    "weathered",
    "blue",
    "billowing",
    "broken",
    "cold",
    "damp",
    "falling",
    "frosty",
    "green",
    "long",
    "late",
    "lingering",
    "bold",
    "little",
    "morning",
    "muddy",
    "old",
    "red",
    "rough",
    "still",
    "small",
    "sparkling",
    "thrumming",
    "shy",
    "wandering",
    "withered",
    "wild",
    "black",
    "young",
    "holy",
    "solitary",
    "fragrant",
    "aged",
    "snowy",
    "proud",
    "floral",
    "restless",
    "divine",
    "polished",
    "ancient",
    "purple",
    "lively",
    "nameless",
]


def _friendly_passphrase() -> str:
    return f"{secrets.choice(ADJECTIVES)}-{secrets.choice(NOUNS)}"


_SETUP_CONF_DEFAULTS = {
    "syncOnStart": True,
    "gcDelay": 0,
    "periodicReplication": True,
    "syncOnFileOpen": True,
    "encrypt": True,
    "usePathObfuscation": True,
    "batchSave": True,
    "batch_size": 50,
    "batches_limit": 50,
    "useHistory": True,
    "disableRequestURI": True,
    "customChunkSize": 50,
    "syncAfterMerge": False,
    "concurrencyOfReadChunksOnline": 100,
    "minimumIntervalOfReadChunksOnline": 100,
    "handleFilenameCaseSensitive": False,
    "doNotUseFixedRevisionForChunks": False,
    "settingVersion": 10,
    "notifyThresholdOfRemoteStorageSize": 800,
}


def _encrypt(plaintext: str, passphrase: str) -> str:
    """Encrypt config JSON in octagonal-wheels format.

    Format: %<iv_hex_32chars><salt_hex_32chars><base64_ciphertext>

    Key derivation: SHA256(passphrase) → PBKDF2-HMAC-SHA256(100000) → AES-256-GCM.
    """
    iterations = 100000

    digest = Hash(SHA256())
    digest.update(passphrase.encode("utf-8"))
    key_material = digest.finalize()

    salt = os.urandom(16)

    kdf = PBKDF2HMAC(
        algorithm=SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    key = kdf.derive(key_material)

    iv = os.urandom(16)

    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)

    return f"%{iv.hex()}{salt.hex()}{base64.b64encode(ciphertext).decode()}"


def generate_setup_uri(
    hostname: str,
    database: str,
    username: str,
    password: str,
    passphrase: str = "",
) -> tuple[str, str]:
    """Generate an obsidian://setuplivesync URI.

    Returns (setup_uri, uri_passphrase).
    """
    uri_passphrase = passphrase or _friendly_passphrase()

    conf = {
        **_SETUP_CONF_DEFAULTS,
        "couchDB_URI": hostname,
        "couchDB_USER": username,
        "couchDB_PASSWORD": password,
        "couchDB_DBNAME": database,
        "passphrase": passphrase,
    }

    import json

    encrypted = _encrypt(json.dumps(conf), uri_passphrase)
    uri = f"obsidian://setuplivesync?settings={quote(encrypted)}"
    return uri, uri_passphrase
