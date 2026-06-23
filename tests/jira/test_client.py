from extractory import BearerAuth, JiraClient, JiraConfig


def test_jira_search_post_uses_context_path_and_offset_pagination(httpx_mock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://jira.example.com/jira/rest/api/2/search",
        json={
            "startAt": 0,
            "maxResults": 1,
            "total": 2,
            "issues": [{"id": "1", "key": "ABC-1", "fields": {"summary": "one"}}],
        },
    )
    httpx_mock.add_response(
        method="POST",
        url="https://jira.example.com/jira/rest/api/2/search",
        json={
            "startAt": 1,
            "maxResults": 1,
            "total": 2,
            "issues": [{"id": "2", "key": "ABC-2", "fields": {"summary": "two"}}],
        },
    )
    config = JiraConfig(
        base_url="https://jira.example.com/jira/",
        auth=BearerAuth("pat"),
        page_size=1,
    )

    with JiraClient(config) as client:
        issues = list(client.issues.search_all("project = ABC"))

    assert [issue.key for issue in issues] == ["ABC-1", "ABC-2"]
    requests = httpx_mock.get_requests()
    assert requests[0].headers["Authorization"] == "Bearer pat"
    assert requests[0].read() == b'{"jql":"project = ABC","startAt":0,"maxResults":1}'


def test_jira_issue_get_serializes_fields_and_expand(httpx_mock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=(
            "https://jira.example.com/rest/api/2/issue/ABC-1"
            "?fields=%2Aall%2C-comment&expand=changelog"
        ),
        json={"id": "1", "key": "ABC-1", "fields": {}},
    )
    config = JiraConfig(base_url="https://jira.example.com")

    with JiraClient(config) as client:
        issue = client.issues.get(
            "ABC-1", fields=["*all"], exclude_fields=["comment"], expand=["changelog"]
        )

    assert issue.key == "ABC-1"
