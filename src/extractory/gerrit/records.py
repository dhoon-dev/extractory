"""Analytics-friendly Gerrit record models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from extractory.records import AnalyticsRecord


class GerritChangeRecord(AnalyticsRecord):
    """Normalized Gerrit change record."""

    source: Literal["gerrit"] = "gerrit"
    id: str | None = None
    triplet_id: str | None = None
    change_id: str | None = None
    change_number: int | None = None
    project: str | None = None
    branch: str | None = None
    full_branch: str | None = None
    topic: str | None = None
    subject: str | None = None
    status: str | None = None
    owner_account_id: int | None = None
    owner_name: str | None = None
    owner_display_name: str | None = None
    owner_email: str | None = None
    owner_username: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    submitted_at: datetime | None = None
    submitter_account_id: int | None = None
    submitter_name: str | None = None
    insertions: int | None = None
    deletions: int | None = None
    total_comment_count: int | None = None
    unresolved_comment_count: int | None = None
    current_revision: str | None = None
    current_revision_number: int | None = None
    mergeable: bool | None = None
    submittable: bool | None = None
    work_in_progress: bool = False
    is_private: bool = False
    hashtags: list[str] = Field(default_factory=list)
    custom_keyed_values: dict[str, Any] = Field(default_factory=dict)
    label_names: list[str] = Field(default_factory=list)
    labels: dict[str, Any] = Field(default_factory=dict)
    submit_requirements: list[dict[str, Any]] = Field(default_factory=list)
    tracking_ids: list[dict[str, Any]] = Field(default_factory=list)
    issue_keys: list[str] = Field(default_factory=list)
    custom: dict[str, Any] = Field(default_factory=dict)
    normalization_warnings: list[str] = Field(default_factory=list)
    raw: dict[str, Any] | None = None


class GerritRevisionRecord(AnalyticsRecord):
    """Normalized Gerrit revision record."""

    source: Literal["gerrit"] = "gerrit"
    change_id: str | None = None
    change_number: int | None = None
    revision: str
    patch_set_number: int | None = None
    kind: str | None = None
    ref: str | None = None
    branch: str | None = None
    created_at: datetime | None = None
    uploader_account_id: int | None = None
    uploader_name: str | None = None
    uploader_email: str | None = None
    commit_subject: str | None = None
    commit_message: str | None = None
    author_name: str | None = None
    author_email: str | None = None
    author_date: datetime | None = None
    author_tz: int | None = None
    committer_name: str | None = None
    committer_email: str | None = None
    committer_date: datetime | None = None
    committer_tz: int | None = None
    parent_commits: list[str] = Field(default_factory=list)
    raw: dict[str, Any] | None = None


class GerritFileRecord(AnalyticsRecord):
    """Normalized Gerrit file record."""

    source: Literal["gerrit"] = "gerrit"
    change_id: str | None = None
    change_number: int | None = None
    revision: str | None = None
    patch_set_number: int | None = None
    file_path: str
    status: str | None = None
    old_path: str | None = None
    binary: bool | None = None
    lines_inserted: int | None = None
    lines_deleted: int | None = None
    size_delta: int | None = None
    size: int | None = None
    old_mode: int | None = None
    new_mode: int | None = None
    old_sha: str | None = None
    new_sha: str | None = None
    raw: dict[str, Any] | None = None


class GerritCommentRecord(AnalyticsRecord):
    """Normalized Gerrit inline comment record."""

    source: Literal["gerrit"] = "gerrit"
    change_id: str | None = None
    change_number: int | None = None
    revision: str | None = None
    patch_set_number: int | None = None
    comment_id: str | None = None
    file_path: str | None = None
    side: str | None = None
    parent: str | None = None
    line: int | None = None
    range_start_line: int | None = None
    range_start_character: int | None = None
    range_end_line: int | None = None
    range_end_character: int | None = None
    in_reply_to: str | None = None
    message: str | None = None
    updated_at: datetime | None = None
    author_account_id: int | None = None
    author_name: str | None = None
    author_display_name: str | None = None
    author_email: str | None = None
    tag: str | None = None
    unresolved: bool | None = None
    change_message_id: str | None = None
    commit_id: str | None = None
    raw: dict[str, Any] | None = None


class GerritChangeMessageRecord(AnalyticsRecord):
    """Normalized Gerrit change message record."""

    source: Literal["gerrit"] = "gerrit"
    change_id: str | None = None
    change_number: int | None = None
    message_id: str | None = None
    author_account_id: int | None = None
    author_name: str | None = None
    author_email: str | None = None
    date: datetime | None = None
    message: str | None = None
    tag: str | None = None
    revision_number: int | None = None
    raw: dict[str, Any] | None = None


class GerritLabelRecord(AnalyticsRecord):
    """Normalized Gerrit label record."""

    source: Literal["gerrit"] = "gerrit"
    change_id: str | None = None
    change_number: int | None = None
    label_name: str
    approved_account_id: int | None = None
    approved_name: str | None = None
    rejected_account_id: int | None = None
    rejected_name: str | None = None
    recommended_account_id: int | None = None
    disliked_account_id: int | None = None
    value: int | None = None
    default_value: int | None = None
    optional: bool | None = None
    blocking: bool | None = None
    raw: dict[str, Any] | None = None


class GerritReviewerRecord(AnalyticsRecord):
    """Normalized Gerrit reviewer record."""

    source: Literal["gerrit"] = "gerrit"
    change_id: str | None = None
    change_number: int | None = None
    state: str
    account_id: int | None = None
    name: str | None = None
    display_name: str | None = None
    email: str | None = None
    username: str | None = None
    approvals: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] | None = None


class GerritSubmitRequirementRecord(AnalyticsRecord):
    """Normalized Gerrit submit requirement record."""

    source: Literal["gerrit"] = "gerrit"
    change_id: str | None = None
    change_number: int | None = None
    name: str
    description: str | None = None
    status: str | None = None
    applicability_expression: str | None = None
    submittability_expression: str | None = None
    override_expression: str | None = None
    is_legacy: bool | None = None
    raw: dict[str, Any] | None = None
