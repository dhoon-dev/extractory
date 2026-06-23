Development
===========

Run the quality gate before handoff:

.. code-block:: bash

   uv sync --locked --all-extras --group docs
   uv run --locked ruff format --check .
   uv run --locked ruff check .
   uv run --locked ty check
   uv run --locked pytest -m "not live"
   uv run --locked --group docs sphinx-build -W -b html docs docs/_build/html
   uv build
