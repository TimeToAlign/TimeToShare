"""Manifest files: the form a file writes its manifest in, and writing it back.

A manifest file is the text of one manifest in one serialization, in the
minimal or the complete form, with or without its ``graphical`` object.
:func:`file_form` reads that :class:`FileForm` off a text, and
:func:`dumps_file` writes a manifest in a given one, so that an editor or a
library writes a file back as it came: ``dumps_file(loads(text),
file_form(text))`` gives ``text`` for every text a writer of this package
wrote. The JavaScript package's ``fileForm`` and ``dumpsFile`` give the same
form and the same bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .defaults import complete, minimal
from .serialization import Serialization, dumps, loads, serialization_of

__all__ = ["FileForm", "dumps_file", "file_form"]


@dataclass(frozen=True)
class FileForm:
    """How a manifest file writes its manifest.

    Attributes:
        minimal: Whether the manifest is in the minimal form rather than the
            complete form.
        styling: Whether the manifest's ``graphical`` object is written.
        serialization: ``"yaml"`` (canonical YAML), ``"json"`` (pretty JSON)
            or ``"jcs"`` (RFC 8785 JSON).
    """

    minimal: bool
    styling: bool
    serialization: Serialization


def file_form(text: str) -> FileForm:
    """Read the form of a manifest file off its text.

    The manifest is minimal when its minimal form writes the same canonical
    YAML as the value the text holds: a key stated at its default makes a
    text not minimal, and the order canonical order sorts does not count.
    Defaults are recognized by exact value (``repeat_count: 1.0`` is the
    default ``1``) and own-axis values respelled by the declared number type
    on both sides, so an RFC 8785 JSON text, which writes an integral float
    as an integer, reads as the form it was written in. It holds its styling
    when it has a top-level ``graphical`` key; the serialization is the one
    :func:`~timetoshare.serialization.serialization_of` names. A text whose
    value states some defaults and leaves out others is not minimal. The
    value is not validated.

    Raises:
        ValueError: If :func:`~timetoshare.serialization.loads` refuses the
            text, or canonical YAML cannot write its value.
        TypeError: If ``text`` is not a ``str``.
    """
    value = loads(text)
    return FileForm(
        minimal=dumps(minimal(value)) == dumps(value),
        styling=isinstance(value, dict) and "graphical" in value,
        serialization=serialization_of(text),
    )


def dumps_file(value: Any, form: FileForm) -> str:
    """Return the text of a manifest as a file of the given form writes it.

    A top-level ``graphical`` is left out unless ``form.styling``; the rest
    is written in the minimal form if ``form.minimal``, else in the complete
    form, in ``form.serialization``. ``value`` is not changed.

    Raises:
        ValueError: If the serialization refuses the value or names no
            serialization (as :func:`~timetoshare.serialization.dumps`
            raises).
        TypeError: If the value is not JSON.
    """
    if not form.styling and isinstance(value, dict) and "graphical" in value:
        value = {key: member for key, member in value.items() if key != "graphical"}
    written = minimal(value) if form.minimal else complete(value)
    return dumps(written, serialization=form.serialization)
