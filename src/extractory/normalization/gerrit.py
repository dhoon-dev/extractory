"""Gerrit normalization."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from extractory.correlation import extract_issue_keys
from extractory.gerrit.records import (
    GerritChangeMessageRecord,
    GerritChangeRecord,
    GerritFileRecord,
    GerritLabelRecord,
    GerritReviewerRecord,
    GerritRevisionRecord,
    GerritSubmitRequirementRecord,
)
from extractory.normalization.builtins import parse_datetime
from extractory.normalization.context import FieldNormalizationContext
from extractory.normalization.registry import (
    ConflictPolicy,
    ErrorPolicy,
    FieldNormalizerRegistry,
    call_normalizer,
    merge_value,
)
from extractory.normalization.result import NormalizationResult


def _account(output_key_prefix: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {
            f"{output_key_prefix}_account_id": None,
            f"{output_key_prefix}_name": None,
            f"{output_key_prefix}_display_name": None,
            f"{output_key_prefix}_email": None,
            f"{output_key_prefix}_username": None,
        }
    return {
        f"{output_key_prefix}_account_id": value.get("_account_id"),
        f"{output_key_prefix}_name": value.get("name"),
        f"{output_key_prefix}_display_name": value.get("display_name") or value.get("displayName"),
        f"{output_key_prefix}_email": value.get("email"),
        f"{output_key_prefix}_username": value.get("username"),
    }


def _as_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _raw_payload(entity: Mapping[str, Any]) -> dict[str, Any]:
    raw = entity.get("raw")
    if isinstance(raw, Mapping):
        nested = raw.get("raw")
        return dict(nested) if isinstance(nested, Mapping) else dict(raw)
    return dict(entity)


def normalize_gerrit_change(
    change: Mapping[str, Any],
    *,
    normalizers: FieldNormalizerRegistry | None = None,
    issue_key_regex: str = r"[A-Z][A-Z0-9]+-\d+",
    include_raw: bool = True,
    conflict_policy: ConflictPolicy = "raise",
    error_policy: ErrorPolicy = "keep_raw",
) -> NormalizationResult[GerritChangeRecord]:
    """Normalize one Gerrit ChangeInfo mapping."""
    raw_payload = _raw_payload(change)
    registry = normalizers or FieldNormalizerRegistry()
    labels = _as_mapping(change.get("labels"))
    tracking_ids = _as_list(change.get("tracking_ids"))
    custom_keyed_values = _as_mapping(change.get("custom_keyed_values"))
    issue_keys: list[str] = []
    for value in (
        change.get("subject"),
        change.get("topic"),
        change.get("hashtags"),
        tracking_ids,
        custom_keyed_values,
        change.get("messages"),
        change.get("revisions"),
    ):
        issue_keys.extend(_extract_recursive(value, issue_key_regex))
    record_data: dict[str, Any] = {
        "id": change.get("id"),
        "triplet_id": change.get("triplet_id") or change.get("id"),
        "change_id": change.get("change_id"),
        "change_number": change.get("_number"),
        "project": change.get("project"),
        "branch": change.get("branch"),
        "full_branch": f"refs/heads/{change.get('branch')}" if change.get("branch") else None,
        "topic": change.get("topic"),
        "subject": change.get("subject"),
        "status": change.get("status"),
        "created_at": parse_datetime(change.get("created")),
        "updated_at": parse_datetime(change.get("updated")),
        "submitted_at": parse_datetime(change.get("submitted")),
        "insertions": change.get("insertions"),
        "deletions": change.get("deletions"),
        "total_comment_count": change.get("total_comment_count"),
        "unresolved_comment_count": change.get("unresolved_comment_count"),
        "current_revision": change.get("current_revision"),
        "current_revision_number": change.get("current_revision_number"),
        "mergeable": change.get("mergeable"),
        "submittable": change.get("submittable"),
        "work_in_progress": bool(change.get("work_in_progress")),
        "is_private": bool(change.get("is_private")),
        "hashtags": _as_list(change.get("hashtags")),
        "custom_keyed_values": custom_keyed_values,
        "label_names": list(labels),
        "labels": labels,
        "submit_requirements": _as_list(change.get("submit_requirements")),
        "tracking_ids": tracking_ids,
        "issue_keys": list(dict.fromkeys(issue_keys)),
        "raw": raw_payload if include_raw else None,
    }
    record_data.update(_account("owner", change.get("owner")))
    submitter = change.get("submitter")
    if isinstance(submitter, Mapping):
        record_data["submitter_account_id"] = submitter.get("_account_id")
        record_data["submitter_name"] = submitter.get("name")

    warnings: list[str] = []
    child_records: list[Any] = []
    custom: dict[str, Any] = {}
    for path, value in (
        (("change", "topic"), change.get("topic")),
        (("change", "custom_keyed_values"), custom_keyed_values),
        (("change", "labels"), labels),
    ):
        context = FieldNormalizationContext(
            source="gerrit",
            entity_type="change",
            change_number=change.get("_number"),
            path=path,
            raw_entity=raw_payload,
        )
        normalizer = registry.resolve(context)
        result = call_normalizer(normalizer, value, context, error_policy=error_policy)
        warnings.extend(result.warnings)
        child_records.extend(result.child_records)
        for key, output_value in result.outputs.items():
            merge_value(record_data, key, output_value, policy=conflict_policy)
        for key, custom_value in result.custom.items():
            merge_value(custom, key, custom_value, policy="namespace", namespace=".".join(path))

    child_records.extend(_revision_records(change))
    child_records.extend(_message_records(change))
    child_records.extend(_label_records(change))
    child_records.extend(_reviewer_records(change))
    child_records.extend(_submit_requirement_records(change))
    record_data["custom"] = custom
    record_data["normalization_warnings"] = warnings
    return NormalizationResult(
        record=GerritChangeRecord.model_validate(record_data),
        child_records=child_records,
        warnings=warnings,
    )


def _extract_recursive(value: Any, pattern: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return extract_issue_keys(value, pattern=pattern)
    if isinstance(value, Mapping):
        result: list[str] = []
        for child in value.values():
            result.extend(_extract_recursive(child, pattern))
        return result
    if isinstance(value, list | tuple):
        result = []
        for child in value:
            result.extend(_extract_recursive(child, pattern))
        return result
    return []


def _revision_records(change: Mapping[str, Any]) -> list[Any]:
    revisions = _as_mapping(change.get("revisions"))
    records: list[Any] = []
    for revision, payload in revisions.items():
        if not isinstance(payload, Mapping):
            continue
        commit = payload.get("commit") if isinstance(payload.get("commit"), Mapping) else {}
        author = commit.get("author") if isinstance(commit.get("author"), Mapping) else {}
        committer = commit.get("committer") if isinstance(commit.get("committer"), Mapping) else {}
        parents = _as_list(commit.get("parents"))
        records.append(
            GerritRevisionRecord(
                change_id=change.get("change_id"),
                change_number=change.get("_number"),
                revision=str(revision),
                patch_set_number=payload.get("_number"),
                kind=payload.get("kind"),
                ref=payload.get("ref"),
                created_at=parse_datetime(payload.get("created")),
                commit_subject=commit.get("subject"),
                commit_message=commit.get("message"),
                author_name=author.get("name") if isinstance(author, Mapping) else None,
                author_email=author.get("email") if isinstance(author, Mapping) else None,
                author_date=parse_datetime(author.get("date"))
                if isinstance(author, Mapping)
                else None,
                author_tz=author.get("tz") if isinstance(author, Mapping) else None,
                committer_name=committer.get("name") if isinstance(committer, Mapping) else None,
                committer_email=committer.get("email") if isinstance(committer, Mapping) else None,
                committer_date=parse_datetime(committer.get("date"))
                if isinstance(committer, Mapping)
                else None,
                committer_tz=committer.get("tz") if isinstance(committer, Mapping) else None,
                parent_commits=[
                    parent.get("commit") for parent in parents if isinstance(parent, Mapping)
                ],
                raw=dict(payload),
            )
        )
        files = _as_mapping(payload.get("files"))
        for file_path, file_payload in files.items():
            if isinstance(file_payload, Mapping):
                records.append(
                    GerritFileRecord(
                        change_id=change.get("change_id"),
                        change_number=change.get("_number"),
                        revision=str(revision),
                        patch_set_number=payload.get("_number"),
                        file_path=str(file_path),
                        status=file_payload.get("status"),
                        old_path=file_payload.get("old_path"),
                        binary=file_payload.get("binary"),
                        lines_inserted=file_payload.get("lines_inserted"),
                        lines_deleted=file_payload.get("lines_deleted"),
                        size_delta=file_payload.get("size_delta"),
                        size=file_payload.get("size"),
                        old_mode=file_payload.get("old_mode"),
                        new_mode=file_payload.get("new_mode"),
                        old_sha=file_payload.get("old_sha"),
                        new_sha=file_payload.get("new_sha"),
                        raw=dict(file_payload),
                    )
                )
    return records


def _message_records(change: Mapping[str, Any]) -> list[GerritChangeMessageRecord]:
    messages = _as_list(change.get("messages"))
    return [
        GerritChangeMessageRecord(
            change_id=change.get("change_id"),
            change_number=change.get("_number"),
            message_id=message.get("id"),
            author_account_id=message.get("author", {}).get("_account_id")
            if isinstance(message.get("author"), Mapping)
            else None,
            author_name=message.get("author", {}).get("name")
            if isinstance(message.get("author"), Mapping)
            else None,
            author_email=message.get("author", {}).get("email")
            if isinstance(message.get("author"), Mapping)
            else None,
            date=parse_datetime(message.get("date")),
            message=message.get("message"),
            tag=message.get("tag"),
            revision_number=message.get("_revision_number"),
            raw=dict(message),
        )
        for message in messages
        if isinstance(message, Mapping)
    ]


def _label_records(change: Mapping[str, Any]) -> list[GerritLabelRecord]:
    labels = _as_mapping(change.get("labels"))
    records: list[GerritLabelRecord] = []
    for label_name, label in labels.items():
        if not isinstance(label, Mapping):
            continue
        approved = label.get("approved") if isinstance(label.get("approved"), Mapping) else {}
        rejected = label.get("rejected") if isinstance(label.get("rejected"), Mapping) else {}
        records.append(
            GerritLabelRecord(
                change_id=change.get("change_id"),
                change_number=change.get("_number"),
                label_name=str(label_name),
                approved_account_id=approved.get("_account_id"),
                approved_name=approved.get("name"),
                rejected_account_id=rejected.get("_account_id"),
                rejected_name=rejected.get("name"),
                value=label.get("value"),
                default_value=label.get("default_value"),
                optional=label.get("optional"),
                blocking=label.get("blocking"),
                raw=dict(label),
            )
        )
    return records


def _reviewer_records(change: Mapping[str, Any]) -> list[GerritReviewerRecord]:
    reviewers = _as_mapping(change.get("reviewers"))
    records: list[GerritReviewerRecord] = []
    for state, accounts in reviewers.items():
        if not isinstance(accounts, list):
            continue
        for account in accounts:
            if not isinstance(account, Mapping):
                continue
            records.append(
                GerritReviewerRecord(
                    change_id=change.get("change_id"),
                    change_number=change.get("_number"),
                    state=str(state),
                    account_id=account.get("_account_id"),
                    name=account.get("name"),
                    display_name=account.get("display_name") or account.get("displayName"),
                    email=account.get("email"),
                    username=account.get("username"),
                    approvals=account.get("approvals")
                    if isinstance(account.get("approvals"), Mapping)
                    else {},
                    raw=dict(account),
                )
            )
    return records


def _submit_requirement_records(change: Mapping[str, Any]) -> list[GerritSubmitRequirementRecord]:
    requirements = _as_list(change.get("submit_requirements"))
    return [
        GerritSubmitRequirementRecord(
            change_id=change.get("change_id"),
            change_number=change.get("_number"),
            name=requirement.get("name") or "",
            description=requirement.get("description"),
            status=requirement.get("status"),
            applicability_expression=requirement.get("applicability_expression"),
            submittability_expression=requirement.get("submittability_expression"),
            override_expression=requirement.get("override_expression"),
            is_legacy=requirement.get("is_legacy"),
            raw=dict(requirement),
        )
        for requirement in requirements
        if isinstance(requirement, Mapping)
    ]
