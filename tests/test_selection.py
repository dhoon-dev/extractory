from extractory.selection import (
    FetchProfile,
    GerritChangeOption,
    jira_profile_selection,
    normalize_gerrit_options,
    serialize_jira_fields,
)


def test_jira_field_serialization_supports_exclusions() -> None:
    assert serialize_jira_fields(["*all"], ["comment"]) == "*all,-comment"


def test_jira_normalized_profile_includes_field_map_values() -> None:
    selection = jira_profile_selection(
        FetchProfile.NORMALIZED,
        field_map={"story_points": "customfield_10016"},
    )

    assert "customfield_10016" in selection.include
    assert "changelog" not in selection.expand


def test_gerrit_option_preset_is_deterministic() -> None:
    options = normalize_gerrit_options(["CURRENT_REVISION"], option_preset="minimal")

    assert options == (GerritChangeOption.SKIP_DIFFSTAT, GerritChangeOption.CURRENT_REVISION)
