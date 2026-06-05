# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

# -- Patch python domain signature regex to allow "foo-bar" style names ------

import os
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup
from docutils.nodes import document
from sphinx.application import Sphinx
from sphinx.domains import python
from sphinx.highlighting import lexers as sphinx_lexers

sys.path.insert(0, str(Path(__file__).parent / "_ext"))
from rattle_pygments import DarkerModernPythonLexer

# modified from sphinx/domains/python.py
py_sig_re = re.compile(
    r"""^ ([\w.]*\.)?            # class name(s)
          ([\w-]+)  \s*             # thing name
          (?: \(\s*(.*)\s*\)     # optional: arguments
           (?:\s* -> \s* (.*))?  #           return annotation
          )? $                   # and nothing more
          """,
    re.VERBOSE,
)

python.py_sig_re = py_sig_re

# -- Project information -----------------------------------------------------

project = "Rattle"
project_copyright = "contributors"
globals()["copyright"] = project_copyright
author = ""
# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "myst_parser",
    "sphinx_copybutton",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns: list[str] = []

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "myst",
}

myst_heading_anchors = 3

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
}
autodoc_member_order = "groupwise"
autodoc_typehints = "description"
autodoc_typehints_format = "short"

pygments_style = "github-light"
pygments_dark_style = "rattle_pygments.DarkerModernStyle"
sphinx_lexers["python"] = DarkerModernPythonLexer()
sphinx_lexers["python3"] = DarkerModernPythonLexer()
sphinx_lexers["py"] = DarkerModernPythonLexer()

copybutton_prompt_text = r"^((>>> |\.\.\. |\$ |# )|((\(.+\) )?\$ ))"
copybutton_prompt_is_regexp = True
copybutton_remove_prompts = True

# highlight_language = "python3"
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "libcst": ("https://libcst.rtfd.io/en/latest", None),
    "packaging": ("https://packaging.pypa.io/en/latest", None),
}
master_doc = "index"

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"
html_title = project
html_show_sourcelink = False
html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "")
html_theme_options = {
    "top_of_page_buttons": "",
}

html_context = {}
if os.environ.get("READTHEDOCS"):
    html_context["READTHEDOCS"] = True


def _expand_rules_sidebar_section(
    _app: Sphinx,
    _pagename: str,
    _templatename: str,
    context: dict[str, object],
    _doctree: document | None,
) -> None:
    navigation_tree = context.get("furo_navigation_tree")
    if not isinstance(navigation_tree, str):
        return

    soup = BeautifulSoup(navigation_tree, "html.parser")
    for item in soup.select("li.has-children"):
        link = item.find("a", recursive=False)
        if link is None or link.get_text(strip=True) != "Rules":
            continue

        checkbox = item.find("input", class_="toctree-checkbox", recursive=False)
        if checkbox is not None:
            checkbox["checked"] = ""

    context["furo_navigation_tree"] = str(soup)


def setup(app: Sphinx) -> dict[str, bool]:
    app.connect("html-page-context", _expand_rules_sidebar_section, priority=900)
    return {"parallel_read_safe": True, "parallel_write_safe": True}


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_js_files = ["copy_as_markdown.js"]
