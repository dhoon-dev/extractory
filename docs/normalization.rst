Normalization
=============

Extractory separates raw payloads, tolerant API models, and analytics-friendly records.
Custom normalization is callable-first. Register functions or callable classes with
``FieldNormalizerRegistry`` and preserve raw values on failure by default.

Normalized records dump observed values by default. If a Jira field was not fetched,
``record.model_dump()`` omits the corresponding normalized key. If the field was fetched
and its value is empty, the key remains present with ``None``, ``[]``, or ``{}``.
Use ``record.model_dump(exclude_unset=False)`` only when a full schema dump is needed.

All fetched Jira fields pass through the same normalizer resolution path. Built-in Jira
fields such as ``summary``, ``description``, ``status``, and ``assignee`` have default
normalizers, but an exact ``register_field_id(...)`` entry overrides the default in the
same way it does for custom fields.

Built-in Normalizers
--------------------

All built-in normalizers are importable from ``extractory.normalization`` and can be
registered by field id, alias, field name, Jira schema, or Gerrit path. Most normalizers
accept an optional ``output_key`` argument for the normalized record key they emit. When
omitted, they use the field alias, then the source field id, then their documented
fallback output key.

.. code-block:: python

   from extractory.normalization import DelimitedTextArrayNormalizer, FieldNormalizerRegistry

   registry = FieldNormalizerRegistry()
   registry.register_field_id(
       "customfield_10029",
       DelimitedTextArrayNormalizer(output_key="release_tags"),
   )

When ``delimiter`` is omitted, ``DelimitedTextArrayNormalizer`` uses Python's built-in
whitespace splitting, equivalent to ``str(value).split()``. Pass ``delimiter`` to split
on a literal string:

.. code-block:: python

   registry.register_field_id(
       "customfield_10030",
       DelimitedTextArrayNormalizer(delimiter=",", output_key="release_tags"),
   )

Use ``regex=True`` only when ``delimiter`` should be interpreted as a Python regular
expression. Regex mode uses ``re.split``; use non-capturing groups such as ``(?:...)`` if
grouping is needed without including delimiter text in the result:

.. code-block:: python

   registry.register_field_id(
       "customfield_10031",
       DelimitedTextArrayNormalizer(
           delimiter=r"\s*[,;]\s*",
           output_key="release_tags",
           regex=True,
       ),
   )

General scalar and array normalizers:

.. list-table::
   :header-rows: 1
   :widths: 28 28 44

   * - Normalizer
     - Input
     - Output
   * - ``IdentityNormalizer(output_key=None)``
     - Any value.
     - Emits the value unchanged under ``output_key``. The fallback output key is
       ``value``.
   * - ``StringNormalizer(output_key=None)``
     - Any value.
     - Emits ``None`` for ``None``; otherwise emits ``str(value)``.
   * - ``TextNormalizer(output_key=None)``
     - Any value.
     - Alias of ``StringNormalizer`` for larger text fields.
   * - ``DelimitedTextArrayNormalizer(delimiter=None, output_key=None, regex=False, strip=True, drop_empty=True)``
     - Text or any scalar value.
     - Splits ``str(value)`` into ``list[str]``. With ``delimiter=None``, it uses
       Python whitespace splitting. Otherwise, ``delimiter`` is a literal string unless
       ``regex=True`` enables Python ``re.split``. ``None`` and ``""`` become ``[]``.
       Empty delimiters are rejected, and invalid regex delimiters fail during normalizer
       construction.
   * - ``NumberNormalizer(output_key=None)``
     - Number-like scalar.
     - Emits ``float(value)``. ``None`` and ``""`` become ``None``; invalid values are
       handled by the configured normalization error policy.
   * - ``BooleanNormalizer(output_key=None)``
     - Any value.
     - Emits ``None`` for ``None``; otherwise emits ``bool(value)``.
   * - ``DateNormalizer(output_key=None)``
     - ISO date string or ``date``.
     - Emits a ``date`` when parsing succeeds, otherwise ``None``.
   * - ``DatetimeNormalizer(output_key=None)``
     - Jira, Gerrit, or ISO timestamp string, or ``datetime``.
     - Emits a timezone-aware ``datetime`` when parsing succeeds, otherwise ``None``.
   * - ``LabelsNormalizer(output_key="labels")``
     - Jira label array.
     - Emits a list of string labels. Non-list values become ``[]``.

Jira object and option normalizers:

.. list-table::
   :header-rows: 1
   :widths: 28 28 44

   * - Normalizer
     - Input
     - Output
   * - ``NamedObjectNormalizer(output_key=None)``
     - Object with ``name``, ``value``, or ``displayName`` and optional ``id`` or ``key``.
     - Emits ``<output_key>`` and ``<output_key>_id``. Scalar values are stringified as the
       display value with no id.
   * - ``NamedArrayNormalizer(output_key=None)``
     - Array of named objects or scalars.
     - Emits a list of display values. The fallback output key is ``values``.
   * - ``OptionNormalizer(output_key=None)``
     - Jira single-select option object.
     - Alias of ``NamedObjectNormalizer`` for option fields.
   * - ``OptionArrayNormalizer(output_key=None)``
     - Jira multi-select option array.
     - Alias of ``NamedArrayNormalizer`` for option arrays.
   * - ``VersionArrayNormalizer(output_key=None)``
     - Jira version object array.
     - Alias of ``NamedArrayNormalizer`` for version arrays.
   * - ``ComponentArrayNormalizer(output_key=None)``
     - Jira component object array.
     - Alias of ``NamedArrayNormalizer`` for component arrays.
   * - ``CascadingSelectNormalizer(output_key=None)``
     - Jira cascading select object with ``value`` and optional ``child.value``.
     - Emits ``<output_key>_parent``, ``<output_key>_child``, and
       ``<output_key>_path``.

Jira user, sprint, and link normalizers:

.. list-table::
   :header-rows: 1
   :widths: 28 28 44

   * - Normalizer
     - Input
     - Output
   * - ``JiraUserNormalizer(output_key_prefix=None)``
     - Jira user object.
     - Emits ``<output_key_prefix>_name``, ``<output_key_prefix>_key``,
       ``<output_key_prefix>_display_name``, and ``<output_key_prefix>_email``.
       Non-object values are left unnormalized.
   * - ``JiraUserArrayNormalizer(output_key=None)``
     - Array of Jira user objects.
     - Emits a list of ``displayName`` values. The fallback output key is ``users``.
   * - ``JiraSprintNormalizer(sprint_names_output_key="sprint_names", active_sprint_names_output_key="active_sprint_names", latest_sprint_name_output_key="latest_sprint_name", emit_child_records=False)``
     - Jira Agile sprint strings or sprint objects, either one value or an array.
     - Emits ``sprint_ids``, ``sprint_states``, the configured name output keys, and
       optional ``JiraSprintRecord`` child records.
   * - ``JiraIssueLinksNormalizer(include_fields=None, include_raw=None)``
     - Jira ``issuelinks`` array.
     - Emits one ``JiraIssueLinkRecord`` child record for each inward or outward linked
       issue. It does not emit normalized outputs. ``include_fields`` may restrict child
       record fields to ``source``, ``issue_key``, ``linked_issue_key``, ``link_type``,
       ``direction``, ``linked_issue_id``, ``linked_issue_status``,
       ``linked_issue_summary``, and ``raw``. ``linked_issue_key`` is always emitted.
       The default field set includes ``issue_key`` for export-friendly relationship
       rows, but explicit ``include_fields`` selections may omit it. ``include_raw=False``
       removes ``raw`` from the child records.

Raw and extraction normalizers:

.. list-table::
   :header-rows: 1
   :widths: 28 28 44

   * - Normalizer
     - Input
     - Output
   * - ``RawJsonNormalizer()``
     - Any value.
     - Preserves the value in the record ``custom`` mapping under the field alias, field
       id, Gerrit path, or ``raw``.
   * - ``RegexExtractNormalizer(pattern, numbered_group_output_keys=None, named_group_output_keys=None)``
     - Text or any scalar value.
     - Applies ``pattern`` and emits selected regex groups.
       ``numbered_group_output_keys`` maps integer capture-group numbers to output
       keys. ``named_group_output_keys`` maps named capture groups to output keys.
       At least one mapping is required.
   * - ``IssueKeyExtractNormalizer(pattern, output_key="issue_keys")``
     - Text or any scalar value.
     - Emits a list of issue keys found by ``extract_issue_keys`` using ``pattern``.

When a Jira field catalog is available, Extractory can also select generic normalizers by
Jira schema:

.. list-table::
   :header-rows: 1
   :widths: 36 64

   * - Jira schema
     - Generic normalizer
   * - ``type: string``
     - ``StringNormalizer``
   * - ``type: number``
     - ``NumberNormalizer``
   * - ``type: date``
     - ``DateNormalizer``
   * - ``type: datetime``
     - ``DatetimeNormalizer``
   * - ``type: user``
     - ``JiraUserNormalizer``
   * - ``type: option``
     - ``OptionNormalizer``
   * - ``type: array`` with ``items: option``, ``version``, or ``component``
     - ``NamedArrayNormalizer``

Jira Issue Default Field Mapping
--------------------------------

Default Jira issue normalizers keep the original Jira field id for the primary value
whenever possible. When a Jira field is an object, Extractory emits the primary display
value under the original field id and uses ``_<subfield>`` suffixes for useful nested
attributes.

.. list-table::
   :header-rows: 1
   :widths: 24 34 42

   * - Jira source field
     - Normalized key(s)
     - Value shape
   * - ``project``
     - ``project``, ``project_id``, ``project_key``
     - Project name, id, and key from the Jira project object.
   * - ``issuetype``
     - ``issuetype``, ``issuetype_id``
     - Issue type name and id.
   * - ``summary``
     - ``summary``
     - Original scalar value.
   * - ``description``
     - ``description``
     - Original scalar value.
   * - ``status``
     - ``status``, ``status_id``, ``status_category``, ``status_category_key``
     - Status name/id plus status category name/key.
   * - ``priority``
     - ``priority``, ``priority_id``
     - Priority name and id.
   * - ``resolution``
     - ``resolution``, ``resolution_id``
     - Resolution name and id.
   * - ``assignee``, ``reporter``, ``creator``
     - ``<field>``, ``<field>_name``, ``<field>_key``, ``<field>_display_name``, ``<field>_email``
     - User display value plus common Jira user identifiers.
   * - ``labels``
     - ``labels``
     - List of label strings.
   * - ``components``
     - ``components``
     - List of component names.
   * - ``fixVersions``
     - ``fixVersions``
     - List of version names.
   * - ``versions``
     - ``versions``
     - List of affected version names.
   * - ``created``
     - ``created``
     - Parsed ``datetime`` value.
   * - ``updated``
     - ``updated``
     - Parsed ``datetime`` value.
   * - ``resolutiondate``
     - ``resolutiondate``
     - Parsed ``datetime`` value.
   * - ``duedate``
     - ``duedate``
     - Parsed ``date`` value.
   * - ``issuelinks``
     - Child ``JiraIssueLinkRecord`` rows
     - One child record per inward/outward linked issue.

For example, fetching only ``description`` now yields a normalized ``description`` key,
not ``description_text``. If you need a different shape, register a custom normalizer
for that exact field id.
