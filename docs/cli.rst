CLI
===

The CLI uses Typer and Rich, and supports JSON, JSONL, CSV, and graph-specific outputs.

.. code-block:: bash

   extractory jira search --base-url https://jira.company.local --jql "project = ABC"
   extractory gerrit query --base-url https://gerrit.company.local --query "status:open"
