from extractory import BearerAuth, JiraClient, JiraConfig, normalize_jira_issue

config = JiraConfig(base_url="https://jira.company.local/jira", auth=BearerAuth("pat"))

with JiraClient(config) as client:
    for issue in client.issues.search_all("project = ABC", fields=["summary", "status"]):
        print(normalize_jira_issue(issue.model_dump(by_alias=True)).record.model_dump())
