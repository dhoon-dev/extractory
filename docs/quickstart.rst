Quickstart
==========

Install with uv or pip, then pass credentials explicitly to SDK constructors. The SDK
does not read environment variables.

.. code-block:: python

   from extractory import BearerAuth, JiraClient, JiraConfig

   config = JiraConfig(base_url="https://jira.company.local/jira", auth=BearerAuth("pat"))
   with JiraClient(config) as client:
       issue = client.issues.get("ABC-123", fields=["summary", "status"])

Gerrit authenticated requests use the ``/a/`` path prefix by default.
