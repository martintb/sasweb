from __future__ import annotations

import importlib.metadata

import sasweb as m


def test_version():
    assert importlib.metadata.version("sasweb") == m.__version__
