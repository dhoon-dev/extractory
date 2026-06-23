from extractory import BasicAuth, GerritClient, GerritConfig
from extractory.tools import GerritChangeGraphTool

config = GerritConfig(base_url="https://gerrit.company.local", auth=BasicAuth("user", "token"))
with GerritClient(config) as client:
    graph = GerritChangeGraphTool(client).crawl_related_changes(["12345"], max_depth=1)
    print(graph.model_dump())
