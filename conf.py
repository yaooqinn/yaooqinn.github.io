import os
import sys
import datetime
import sphinx_markdown_tables
import recommonmark
from recommonmark.transform import AutoStructify
from recommonmark.parser import CommonMarkParser

sys.path.insert(0, os.path.abspath('.'))

source_suffix = {
    '.rst': 'restructuredtext',
    '.txt': 'restructuredtext',
    '.md': 'markdown',
}

source_parsers = {
    '.md': CommonMarkParser,
}

# -- Project information -----------------------------------------------------

project = 'napping'
copyright = datetime.datetime.now().strftime("%Y") + ' Kent Yao'
author = 'Kent Yao'

# The full version, including alpha/beta/rc tags
release = '0.0.1'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.mathjax',
    'recommonmark',
    'sphinx_copybutton',
    'sphinx_markdown_tables',
    'sphinx_togglebutton',
    'notfound.extension',
    'sphinxemoji.sphinxemoji',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'README.md', "requirements.txt"]

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_book_theme'
html_theme_options = {
    "repository_url": "https://github.com/yaooqinn/yaooqinn.github.io",
    "use_repository_button": True,
    "use_edit_page_button": True,
    "use_download_button": True,
    "use_fullscreen_button": True,
    "repository_branch": "main",
    "path_to_docs": ".",
    "logo_only": True,
    "home_page_in_toc": False,
    "show_navbar_depth": 1,
    "show_toc_level": 2,
    "announcement": "&#129412; Greetings From Kent Yao! &#x2728;, v" + release,
    "toc_title": "",
    "extra_navbar": "Version " + release,
}

html_title = 'Kent Yao'

# html_static_path = ['_static']
htmlhelp_basename = 'Recommonmarkdoc'
github_doc_root = 'https://github.com/yaooqinn/yaooqinn.github.io/tree/main/docs/'


def setup(app):
    app.add_config_value('recommonmark_config', {
        'url_resolver': lambda url: github_doc_root + url,
        'auto_toc_tree_section': 'Contents',
        'enable_eval_rst': True,
    }, True)
    app.add_transform(AutoStructify)
