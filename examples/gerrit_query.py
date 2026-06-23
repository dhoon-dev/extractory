from extractory import BasicAuth, GerritClient, GerritConfig, normalize_gerrit_change

config = GerritConfig(base_url="https://gerrit.company.local", auth=BasicAuth("user", "token"))

with GerritClient(config) as client:
    for change in client.changes.query_all("status:open project:my/repo", option_preset="standard"):
        print(normalize_gerrit_change(change.model_dump(by_alias=True)).record.model_dump())
