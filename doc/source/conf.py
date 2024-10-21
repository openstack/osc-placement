# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# -- General configuration ----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'openstackdocstheme',
    'sphinx.ext.autodoc',
    'cliff.sphinxext'
]

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'osc-placement'
copyright = '2016, OpenStack Foundation'

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'native'

# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'openstackdocs'

# See: https://docs.openstack.org/cliff/2.6.0/sphinxext.html
autoprogram_cliff_application = 'openstack'

autoprogram_cliff_ignored = [
    '--help', '--format', '--column', '--max-width', '--fit-width',
    '--print-empty', '--prefix', '--noindent', '--quote']

# openstackdocstheme options
openstackdocs_repo_name = 'openstack/osc-placement'
openstackdocs_pdf_link = True
openstackdocs_auto_name = False
openstackdocs_use_storyboard = True

# -- Options for LaTeX output -------------------------------------------------

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass
# [howto/manual]).
latex_use_xindy = False
latex_documents = [
    ('index', 'doc-osc-placement.tex', 'osc-placement Documentation',
     'OpenStack Foundation', 'manual'),
]
