"""The TimeToShare! schema, its fixtures, a validator and the fonts.

A TimeToShare manifest is one JSON object holding the version marker
``timetoshare`` and an array of root timelines, each describing a musical
timeline as timetoalign serializes it, optionally named, optionally
attributing timelines to groups, optionally linking the manifest, its
timelines and its regions to external entities (``Link``, built from URLs
through the registry of known identifier schemes) and optionally styled for
drawing. An editor
can place many manifests on a canvas, but a manifest knows nothing about
where or how often it is placed.
"""

from __future__ import annotations

from .defaults import DEFAULTS, complete, minimal
from .description import (
    ABSENCE_REASONS,
    LEVELS,
    MATCHES,
    METHODS,
    PARTS_RELATIONS,
    RELATIONS,
    STATUSES,
    Assertion,
    Descriptor,
    Identifier,
    Link,
    PartOf,
    PartSlot,
    Scheme,
)
from .files import FileForm, dumps_file, file_form
from .fixtures import (
    RejectionCase,
    fixture_paths,
    rejection_case,
    rejection_paths,
    warning_paths,
)
from .font import FONT_FILES, font_metrics, font_paths
from .manifest import TIMESTAMP_DISPLAY, canonical_order
from .registry import KnownScheme, Recognition, SchemeRegistry, default_registry
from .serialization import SERIALIZATIONS, dumps, loads, serialization_of
from .styles import MissingStyleWarning, complete_styles
from .validate import (
    SCHEMA_VERSION,
    SchemaValidationError,
    UnsupportedVersionError,
    child_ends,
    description_problems,
    identity_problems,
    json_pointer,
    load_schema,
    number_type_of,
    schema_path,
    unknown_keys,
    unregistered_terms,
    validate,
)

__all__ = [
    "ABSENCE_REASONS",
    "DEFAULTS",
    "FONT_FILES",
    "LEVELS",
    "MATCHES",
    "METHODS",
    "PARTS_RELATIONS",
    "RELATIONS",
    "SCHEMA_VERSION",
    "SERIALIZATIONS",
    "STATUSES",
    "Assertion",
    "Descriptor",
    "FileForm",
    "Identifier",
    "KnownScheme",
    "Link",
    "PartOf",
    "PartSlot",
    "Recognition",
    "Scheme",
    "SchemaValidationError",
    "SchemeRegistry",
    "TIMESTAMP_DISPLAY",
    "MissingStyleWarning",
    "RejectionCase",
    "UnsupportedVersionError",
    "canonical_order",
    "child_ends",
    "complete",
    "complete_styles",
    "default_registry",
    "description_problems",
    "dumps",
    "dumps_file",
    "file_form",
    "font_metrics",
    "font_paths",
    "fixture_paths",
    "identity_problems",
    "json_pointer",
    "load_schema",
    "loads",
    "minimal",
    "number_type_of",
    "rejection_case",
    "rejection_paths",
    "schema_path",
    "serialization_of",
    "unknown_keys",
    "unregistered_terms",
    "validate",
    "warning_paths",
]
