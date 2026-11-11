"""Data that is not stored in git."""

import sys

from invoke import task

from ._common import ROOT


@task
def fetch(c, locomo_only=False, cache_only=False):
    """Download LoCoMo and the optional embedding cache."""
    sys.path.insert(0, str(ROOT / "src"))
    import fetch_data

    if not cache_only:
        fetch_data.fetch_locomo()
    if not locomo_only:
        fetch_data.fetch_cache()
