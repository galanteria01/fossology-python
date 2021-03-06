|License| |PyPI Version| |Python Version| |Static Checks| |Fossology Tests| |Coverage|

.. |License| image:: https://img.shields.io/badge/license-MIT-blue.svg
   :target: https://github.com/deveaud-m/fossology-python/LICENSE.md

.. |PyPI Version| image:: https://badge.fury.io/py/fossology.svg
   :target: https://pypi.org/project/fossology

.. |Python Version| image:: https://img.shields.io/badge/python-3.7%2C3.8%2C3.9-blue?logo=python
   :target: https://www.python.org/doc/versions/

.. |Static Checks| image:: https://github.com/deveaud-m/fossology-python/workflows/Static%20Checks/badge.svg
   :target: https://github.com/deveaud-m/fossology-python/actions?query=workflow%3A%22Static+Checks%22
   
.. |Fossology Tests| image:: https://github.com/deveaud-m/fossology-python/workflows/Fossology%20Tests/badge.svg
   :target: https://github.com/deveaud-m/fossology-python/actions?query=workflow%3A%22Fossology+Tests%22

.. |Coverage| image:: https://codecov.io/gh/fossology/fossology-python/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/fossology/fossology-python

A simple wrapper for the Fossology REST API.

See `the OpenAPI specification <https://raw.githubusercontent.com/fossology/fossology/master/src/www/ui/api/documentation/openapi.yaml>`_ used to implement this library.

   Compatible from API version 1.0.16 up to 1.2.1

Documentation
=============

See `fossology-python on Github Pages <https://fossology.github.io/fossology-python>`_.

Usage
=====

Installation
------------

   This project is available as `Python package on PyPi.org <https://pypi.org/project/fossology/>`_.

-  Install fossology and required dependencies:

   .. code:: shell

      pip install fossology requests

Using the API
-------------

-  Get a REST API token either from the Fossology server under "User->Edit user account" or generate a token using the method available in this library:

   .. code:: Python

      from fossology import fossology_token
      from fossology.obj import TokenScope

      FOSSOLOGY_SERVER = "https://fossology.example.com/"
      FOSSOLOGY_USER = "fossy"
      FOSSOLOGY_PASSWORD = "fossy"
      TOKEN_NAME = "fossy_token"

      token = fossology_token(
            FOSSOLOGY_SERVER,
            FOSSOLOGY_USER,
            FOSSOLOGY_PASSWORD,
            TOKEN_NAME,
            TokenScope.WRITE
      )

-  Start using the API:

   .. code:: python

      from fossology import Fossology

      foss = Fossology(
            FOSSOLOGY_SERVER,
            token,
            FOSSOLOGY_USER
      )


Contribute
==========

Develop
-------

-  All contributions in form of bug reports, feature requests or merge requests!

-  Use proper
   `docstrings <https://realpython.com/documenting-python-code/>`__ to
   document functions and classes

-  Extend the testsuite **poetry run pytest** with the new functions/classes

-  The **documentation website** can automatically be generated by the `Sphinx autodoc
   extension <http://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html>`_


Build
-----

- You can build the PyPi package using `poetry <https://poetry.eustace.io/>`_:

  .. code:: shell

    poetry build

- Build documentation (the generated static site must be pushed to the **gh-pages** branch):

  .. code:: shell

     git clone -b gh-pages git@github.com:fossology/fossology-python.git docs/
     poetry run sphinx-build docs-source docs/
     cd docs/
     # Create a new branch to be merged into gh-pages and commit your changes

- Cleanup builds:

  .. code:: shell

     rm -r dist/ docs/

Tag
----

Each new release gets a new tag with important information about the changes added to the new release:

.. code:: shell

   git tag -a vx.x.x -m "New major/minor/patch release x.x.x"
   git push origin vx.x.x

Add required information in the corresponding `release in the Github project <https://github.com/fossology/fossology-python/releases>`_.


Test
----

The testsuite available in this project expects a running Fossology instance under the hostname **fossology** with the default admin user "fossy".

- Use the latest Fossology container from `Docker hub <https://hub.docker.com/r/fossology/fossology>`_:

  .. code:: shell

    docker pull fossology/fossology
    tar xJf tests/files/base-files_11.tar.xz -C /tmp
    docker run --mount src="/tmp",dst=/tmp,type=bind --name fossology -p 80:80 fossology/fossology

- Start the complete test suite or a specific test case (and generate coverage report):

  .. code:: shell

     poetry run coverage run --source=fossology -m pytest
     poetry run coverage report -m
     poetry run coverage html
