import os
import sys

sys.path.insert(0, os.path.abspath("../.."))

project = "Smart Meeting Room"
copyright = "2025, Leila"
author = "Leila Mounzer"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns: list[str] = []

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
