from extractory import BearerAuth, JiraClient, JiraConfig
from extractory.tools import JiraIssueGraphTool

config = JiraConfig(base_url="https://jira.company.local/jira", auth=BearerAuth("pat"))
with JiraClient(config) as client:
    graph = JiraIssueGraphTool(client).crawl_connected_issues(["ABC-123"], max_depth=1)
    print(graph.model_dump())
