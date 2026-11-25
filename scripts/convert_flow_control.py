#!/usr/bin/env python
"""Convert a manifest's flow control from the earlier form to roles and destinations.

The earlier form of flow control wrote three element types under ``type``:
``jump_from`` with a ``target``, ``jump_to`` and ``flow_marker``. The format
writes five roles under ``role``, and a jump holds its destinations
(``targets``). An element is of the earlier form exactly where the
validators of ``timetoshare`` say so (``flow_control_form``): it states one of
the three words under ``type`` or under ``role``, or it holds a ``target``
and no ``role``. :func:`convert` rewrites a manifest, timeline by timeline,
reading one of the three words under ``role`` as it reads it under ``type``:

* ``jump_to`` becomes the role ``jump_target``, its manifestation kept;
* a ``flow_marker`` becomes, by its manifestation, a ``break`` (``fine``,
  with ``ends.after`` naming the destination of the timeline's one ``…_al_fine``
  jump), a ``section_break`` (the manifestation dropped: the format defines
  none for a section break) or a ``barline`` (``double_barline``,
  ``final_barline``);
* a ``jump_from`` becomes a ``jump`` with one destination: ``to`` its
  ``target``, its manifestation, and for a ``repeat_end`` its
  ``repeat_count`` (1 where it stated none), for every da capo and dal segno
  form ``repeat_count: 1`` and ``reset: false``, for a ``to_coda`` an
  ``after`` naming the destination of the timeline's one ``…_al_coda`` jump.
  A ``repeat_end`` and every da capo form without a ``target`` went to the
  timeline's start: their destination names the timeline itself (``to`` the
  timeline's ID), never no place, which would land at the nearest section
  break before the jump;
* two ``jump_from`` at one coordinate of a timeline become one jump holding
  both destinations under the ID that comes first by code point; the other
  element's label moves to its destination, every address naming its ID is
  rewritten to the kept ID, and its name and meta are dropped;
* a drawing rule selecting the element type ``jump_from`` selects ``jump``,
  and one selecting ``flow_marker`` becomes three rules in its place, for
  ``break``, ``section_break`` and ``barline``.

The converter never guesses: a ``fine`` or a ``to_coda`` on a timeline with
no or several jumps of the form it waits for, a merge that would give one
jump two destinations at one place, a jump without a ``target`` that is
neither a ``repeat_end`` nor a da capo, an element holding a ``target`` and
none of the three words, one stating two different words under ``type`` and
``role``, one mixing the earlier form with ``targets`` or ``ends``, and an
element it cannot read are reported, and the manifest is left unconverted
(:class:`ConversionRefused`).

Run it on manifest files, each rewritten in place in the form it was read
in (serialization, minimal or complete)::

    python scripts/convert_flow_control.py score.yaml other.json
    python scripts/convert_flow_control.py --check score.yaml   # report only

Exit status 0 when every file is converted or needs nothing; 1 when one is
refused. The package ``timetoshare`` must be importable.
"""

from __future__ import annotations

import argparse
import copy
import sys
from collections.abc import Iterator
from fractions import Fraction
from pathlib import Path
from typing import Any

EARLIER_TYPES = ("jump_from", "jump_to", "flow_marker")
TO_THE_START = ("repeat_end", "da_capo", "da_capo_al_fine", "da_capo_al_coda")
"""The manifestations of a ``jump_from`` that went to the timeline's start
where it stated no ``target``."""
AL_FINE = ("da_capo_al_fine", "dal_segno_al_fine")
AL_CODA = ("da_capo_al_coda", "dal_segno_al_coda")
LEAPS = (
    "da_capo",
    "da_capo_al_fine",
    "da_capo_al_coda",
    "dal_segno",
    "dal_segno_al_fine",
    "dal_segno_al_coda",
)
MARKER_ROLES = {
    "fine": "break",
    "section_break": "section_break",
    "double_barline": "barline",
    "final_barline": "barline",
}
MARKER_ELEMENTS = ("break", "section_break", "barline")


class ConversionRefused(ValueError):
    """Raised when a manifest cannot be converted without guessing.

    Attributes:
        problems: One sentence per element the converter cannot convert.
    """

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("; ".join(problems))


def _value(number: Any) -> Fraction:
    """The exact value of a coordinate: a JSON number or a Fraction pair."""
    if isinstance(number, list) and len(number) == 2:
        return Fraction(number[0]) / Fraction(number[1])
    if isinstance(number, bool) or not isinstance(number, int | float):
        raise TypeError(f"not a coordinate: {number!r}")
    return Fraction(number)


def _timelines(manifest: Any) -> Iterator[dict[str, Any]]:
    def visit(timeline: Any) -> Iterator[dict[str, Any]]:
        if not isinstance(timeline, dict):
            return
        yield timeline
        children = timeline.get("children")
        for child in children if isinstance(children, list) else []:
            yield from visit(child)

    roots = manifest.get("timelines") if isinstance(manifest, dict) else None
    for root in roots if isinstance(roots, list) else []:
        yield from visit(root)


def _word(element: dict[str, Any], key: str) -> str | None:
    """The word of the earlier form an element states under ``key``, else None."""
    word = element.get(key)
    return word if isinstance(word, str) and word in EARLIER_TYPES else None


def _is_earlier(element: Any) -> bool:
    """Whether an element is of the earlier form, as the validators decide it."""
    if not isinstance(element, dict):
        return False
    return (
        _word(element, "type") is not None
        or _word(element, "role") is not None
        or ("target" in element and "role" not in element)
    )


def _kind(element: dict[str, Any], owner: Any, problems: list[str]) -> str | None:
    """The earlier type of an element of the earlier form, else None and a problem."""
    named = f"'{element.get('id')}' of '{owner}'"
    kind, role = _word(element, "type"), _word(element, "role")
    if kind is None and role is None:
        stated = (
            f"the type {element['type']!r}, which is none of the earlier form"
            if "type" in element
            else "no type"
        )
        problems.append(
            f"{named} has a target and {stated}: an element of the earlier form "
            "states jump_from, jump_to or flow_marker; nothing is guessed"
        )
        return None
    if kind is not None and "role" in element and element["role"] != kind:
        problems.append(
            f"{named} states the type {kind!r} and the role {element['role']!r}: "
            "nothing is guessed"
        )
        return None
    mixed = [key for key in ("targets", "ends") if key in element]
    if mixed:
        problems.append(
            f"{named} mixes the earlier form ({kind or role}) with "
            f"{' and '.join(mixed)}: nothing is guessed"
        )
        return None
    return kind or role


def needs_conversion(manifest: Any) -> bool:
    """Whether a manifest holds flow control or a drawing rule of the earlier form."""
    for timeline in _timelines(manifest):
        flow = timeline.get("flow_control")
        if isinstance(flow, list) and any(_is_earlier(entry) for entry in flow):
            return True
    return any(
        selector.get(key) in ("jump_from", "flow_marker")
        for selector in _selectors(manifest)
        for key in ("element", "inside")
    )


def _rules(manifest: Any) -> list[Any]:
    graphical = manifest.get("graphical") if isinstance(manifest, dict) else None
    rules = graphical.get("rules") if isinstance(graphical, dict) else None
    return rules if isinstance(rules, list) else []


def _selectors(manifest: Any) -> Iterator[dict[str, Any]]:
    for rule in _rules(manifest):
        selector = rule.get("select") if isinstance(rule, dict) else None
        if isinstance(selector, dict):
            yield selector


def _kept(element: dict[str, Any], *dropped: str) -> dict[str, Any]:
    """The members of an earlier element that its converted element keeps."""
    return {
        key: copy.deepcopy(value)
        for key, value in element.items()
        if key
        not in ("type", "role", "target", "repeat_count", "manifestation", *dropped)
    }


def _reference(jump: dict[str, Any], destination: dict[str, Any]) -> dict[str, Any]:
    """The ``after`` naming one destination of a converted jump."""
    reference = {"jump": jump["id"]}
    if len(jump["targets"]) > 1:
        for key in ("to", "by"):
            if key in destination:
                reference[key] = copy.deepcopy(destination[key])
    return reference


def _convert_timeline(
    timeline: dict[str, Any],
    report: list[str],
    problems: list[str],
    renamed: dict[str, str],
) -> None:
    flow = timeline.get("flow_control")
    if not isinstance(flow, list) or not any(_is_earlier(entry) for entry in flow):
        return
    owner = timeline.get("id")
    # The earlier type of each element of the earlier form, by its index;
    # None where the element is refused.
    kinds = {
        index: _kind(entry, owner, problems)
        for index, entry in enumerate(flow)
        if _is_earlier(entry)
    }
    origins = [flow[index] for index, kind in kinds.items() if kind == "jump_from"]
    # Jumps: one per coordinate, the earlier elements in ID order. ``made``
    # maps an earlier jump's ID to the jump it became, None where it was
    # merged into another's or refused.
    jumps: dict[Fraction, dict[str, Any]] = {}
    made: dict[str, dict[str, Any] | None] = {}
    destination_of: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    waiting: list[tuple[dict[str, Any], str, tuple[str, ...]]] = []
    for entry in flow:
        if (
            isinstance(entry, dict)
            and not _is_earlier(entry)
            and entry.get("role") == "jump"
        ):
            try:
                jumps[_value(entry.get("coordinate"))] = entry
            except (TypeError, ValueError, ZeroDivisionError):
                pass
    for entry in sorted(origins, key=lambda entry: str(entry.get("id"))):
        manifestation = entry.get("manifestation")
        try:
            coordinate = _value(entry.get("coordinate"))
        except (TypeError, ValueError, ZeroDivisionError):
            problems.append(
                f"'{entry.get('id')}' of '{owner}' has no coordinate that can be read"
            )
            continue
        destination: dict[str, Any] = {}
        if "target" in entry:
            destination["to"] = entry["target"]
        elif manifestation in TO_THE_START and isinstance(owner, str):
            destination["to"] = owner
        else:
            problems.append(
                f"'{entry.get('id')}' of '{owner}' has no target and the "
                f"manifestation {manifestation!r}: only a repeat_end and a da capo "
                "of a timeline with an ID went to the timeline's start without one"
            )
            continue
        if manifestation is not None:
            destination["manifestation"] = manifestation
        if manifestation == "repeat_end":
            destination["repeat_count"] = entry.get("repeat_count", 1)
        elif manifestation in LEAPS:
            destination["repeat_count"] = 1
            destination["reset"] = False
        elif manifestation == "to_coda":
            waiting.append((destination, f"'{entry.get('id')}'", AL_CODA))
        jump = jumps.get(coordinate)
        made[entry["id"]] = None
        if jump is None:
            jump = _kept(entry)
            jump["role"] = "jump"
            jump["targets"] = [destination]
            jumps[coordinate] = jump
            made[entry["id"]] = jump
        elif not any(jump is other for other in made.values()):
            problems.append(
                f"'{entry.get('id')}' of '{owner}' lies at the coordinate of the "
                f"jump '{jump.get('id')}', which is not of the earlier form"
            )
            continue
        else:
            place = destination.get("to")
            if any(other.get("to") == place for other in jump["targets"]):
                problems.append(
                    f"'{entry.get('id')}' and '{jump['id']}' of '{owner}' lie at "
                    "one coordinate and lead to one place: one jump cannot hold "
                    "two destinations at one place"
                )
                continue
            first = jump["targets"][0]
            if "label" not in first and jump.get("label") is not None:
                first["label"] = jump["label"]
            if entry.get("label") is not None:
                destination["label"] = entry["label"]
            jump["targets"].append(destination)
            renamed[entry["id"]] = jump["id"]
            lost = [key for key in ("name", "meta") if entry.get(key) not in (None, {})]
            report.append(
                f"'{entry['id']}' and '{jump['id']}' of '{owner}' lie at one "
                f"coordinate: merged into the jump '{jump['id']}' with both "
                "destinations"
                + (
                    f"; the {' and '.join(lost)} of '{entry['id']}' dropped"
                    if lost
                    else ""
                )
            )
        destination_of[entry["id"]] = (jump, destination)

    def waited_for(
        words: tuple[str, ...], what: str, who: str
    ) -> dict[str, Any] | None:
        """The ``after`` naming the one jump of the manifestations ``words``."""
        found = [entry for entry in origins if entry.get("manifestation") in words]
        if len(found) != 1 or found[0]["id"] not in destination_of:
            problems.append(
                f"{who} of '{owner}' waits for {what}, and the timeline has "
                f"{len(found) or 'none'}: nothing is guessed"
            )
            return None
        return _reference(*destination_of[found[0]["id"]])

    for destination, who, words in waiting:
        after = waited_for(
            words, "one da capo or dal segno al coda", f"the to_coda {who}"
        )
        if after is not None:
            destination["after"] = after

    converted: list[Any] = []
    for index, entry in enumerate(flow):
        if index not in kinds:
            converted.append(entry)
            continue
        kind, manifestation = kinds[index], entry.get("manifestation")
        if kind is None:
            continue
        if kind == "jump_from":
            jump = made.get(entry.get("id"))
            if jump is not None:
                converted.append(jump)
            continue
        if kind == "jump_to":
            element = _kept(entry)
            element["role"] = "jump_target"
            if manifestation is not None:
                element["manifestation"] = manifestation
            converted.append(element)
            continue
        role = MARKER_ROLES.get(manifestation)
        if role is None:
            problems.append(
                f"the flow marker '{entry.get('id')}' of '{owner}' has the "
                f"manifestation {manifestation!r}, which names no role"
            )
            continue
        element = _kept(entry)
        element["role"] = role
        if role != "section_break":
            element["manifestation"] = manifestation
        if manifestation == "fine":
            after = waited_for(
                AL_FINE,
                "one da capo or dal segno al fine",
                f"the fine '{entry.get('id')}'",
            )
            if after is not None:
                element["ends"] = {"after": after}
        converted.append(element)
    timeline["flow_control"] = converted


def _convert_rules(manifest: dict[str, Any], report: list[str]) -> None:
    rules = _rules(manifest)
    converted: list[Any] = []
    for rule in rules:
        selector = rule.get("select") if isinstance(rule, dict) else None
        if not isinstance(selector, dict):
            converted.append(rule)
            continue
        for key in ("element", "inside"):
            if selector.get(key) == "jump_from":
                selector[key] = "jump"
        variants = [rule]
        for key in ("element", "inside"):
            if selector.get(key) == "flow_marker":
                variants = [
                    {**variant, "select": {**variant["select"], key: word}}
                    for variant in variants
                    for word in MARKER_ELEMENTS
                ]
        if len(variants) > 1:
            report.append(
                "a drawing rule selecting the element type 'flow_marker' became "
                f"{len(variants)} rules, for 'break', 'section_break' and 'barline'"
            )
            variants = [copy.deepcopy(variant) for variant in variants]
        converted.extend(variants)
    if rules:
        manifest["graphical"]["rules"] = converted


def _rename_addresses(manifest: dict[str, Any], renamed: dict[str, str]) -> None:
    for selector in _selectors(manifest):
        addresses = selector.get("addresses")
        for address in addresses if isinstance(addresses, list) else []:
            if isinstance(address, dict) and address.get("id") in renamed:
                address["id"] = renamed[address["id"]]


def convert(manifest: Any) -> tuple[Any, list[str]]:
    """Return a manifest with its flow control in roles and destinations, and a report.

    The manifest is taken in either form of its IDs (``#id`` as a file writes
    them, or bare) and is not changed; elements already written with a
    ``role`` are kept as they are. The report lists every merge of two
    earlier jumps into one and every drawing rule that became several; it is
    empty where nothing of the kind happened.

    Raises:
        ConversionRefused: If an element cannot be converted without
            guessing; its ``problems`` name each such element.
    """
    result = copy.deepcopy(manifest)
    report: list[str] = []
    problems: list[str] = []
    renamed: dict[str, str] = {}
    for timeline in _timelines(result):
        _convert_timeline(timeline, report, problems, renamed)
    if problems:
        raise ConversionRefused(problems)
    if isinstance(result, dict):
        _convert_rules(result, report)
        _rename_addresses(result, renamed)
    return result, report


def convert_text(text: str) -> tuple[str, list[str]]:
    """Convert the text of a manifest file, written back in the form it was read in.

    Raises:
        ConversionRefused: As :func:`convert` raises.
        ValueError: If the text is no manifest file ``timetoshare`` reads.
    """
    from timetoshare import dumps_file, file_form, loads

    value = loads(text)
    if not needs_conversion(value):
        return text, []
    form = file_form(text)
    result, report = convert(value)
    return dumps_file(result, form), report


def main(arguments: list[str] | None = None) -> int:
    """Convert the files named on the command line; return the exit status."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("files", nargs="+", type=Path, help="manifest files")
    parser.add_argument(
        "--check",
        action="store_true",
        help="report what would be done and write nothing",
    )
    options = parser.parse_args(arguments)
    status = 0
    for path in options.files:
        text = path.read_text(encoding="utf-8")
        try:
            converted, report = convert_text(text)
        except ConversionRefused as refused:
            status = 1
            for problem in refused.problems:
                print(f"{path}: refused: {problem}")
            continue
        for line in report:
            print(f"{path}: {line}")
        if converted == text:
            print(f"{path}: nothing to convert")
        elif options.check:
            print(f"{path}: would be converted")
        else:
            path.write_text(converted, encoding="utf-8")
            print(f"{path}: converted")
    return status


if __name__ == "__main__":
    sys.exit(main())
