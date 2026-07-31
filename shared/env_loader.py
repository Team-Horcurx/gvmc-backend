import os

_loaded = False


def load_secrets():
    global _loaded
    if _loaded:
        return
    _loaded = True
