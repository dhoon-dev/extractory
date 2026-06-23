from extractory.tools import summarize_change_risk

summary = summarize_change_risk(issue_keys=["ABC-123"], gerrit_query="project:my/repo status:open")
print(summary.model_dump())
