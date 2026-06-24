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

Use ``DelimitedTextArrayNormalizer`` for text fields that encode multiple values in one
string. The delimiter is explicit, and items are stripped with empty values dropped by
default.

.. code-block:: python

   from extractory.normalization import DelimitedTextArrayNormalizer, FieldNormalizerRegistry

   registry = FieldNormalizerRegistry()
   registry.register_field_id(
       "customfield_10030",
       DelimitedTextArrayNormalizer(delimiter=",", column="release_tags"),
   )

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
