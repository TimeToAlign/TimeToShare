# Why this file exists: pre-commit installs a hook written in Python by running
# `pip install .` at the root of its clone of this repository, while the
# timetoshare package lives in python/ (built by python/pyproject.toml). This
# file builds an empty distribution, timetoshare-pre-commit-hooks, so that the
# root installs at all; each hook in .pre-commit-hooks.yaml installs the real
# package through `additional_dependencies: ["./python[tables]"]`. Nothing else
# reads this file, and it declares no dependency of its own.
from setuptools import setup

setup(
    name="timetoshare-pre-commit-hooks",
    version="0",
    packages=[],
    py_modules=[],
)
