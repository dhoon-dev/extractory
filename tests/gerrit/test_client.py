from extractory import BasicAuth, GerritClient, GerritConfig


def test_gerrit_query_uses_authenticated_prefix_repeated_options_and_more_changes(
    httpx_mock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=("https://gerrit.example.com/a/changes?q=status%3Aopen&n=1&start=0&o=SKIP_DIFFSTAT"),
        text=')]}\'\n[{"id":"repo~main~I1","project":"repo","branch":"main",'
        '"change_id":"I1","subject":"one","status":"NEW","_number":1,'
        '"_more_changes":true}]',
    )
    httpx_mock.add_response(
        method="GET",
        url=("https://gerrit.example.com/a/changes?q=status%3Aopen&n=1&start=1&o=SKIP_DIFFSTAT"),
        text=')]}\'\n[{"id":"repo~main~I2","project":"repo","branch":"main",'
        '"change_id":"I2","subject":"two","status":"NEW","_number":2}]',
    )
    config = GerritConfig(
        base_url="https://gerrit.example.com",
        auth=BasicAuth("user", "password"),
        page_size=1,
    )

    with GerritClient(config) as client:
        changes = list(client.changes.query_all("status:open", option_preset="minimal"))

    assert [change.change_number for change in changes] == [1, 2]
    assert httpx_mock.get_requests()[0].url.path == "/a/changes"
