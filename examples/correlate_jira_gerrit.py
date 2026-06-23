from extractory import correlate_issue_keys

change_payload = {"subject": "ABC-123 fix startup failure", "_number": 42}
print([link.model_dump() for link in correlate_issue_keys(change_payload)])
