"""Large valid manifests, built for the comparison and the timing of the validator."""

from __future__ import annotations

from typing import Any

from timetoshare import with_file_ids


def many_timestamps(roots: int = 500, per_root: int = 20) -> dict[str, Any]:
    """``roots`` root timelines of 20 quarters, each with ``per_root`` named timestamps.

    Every timestamp lies on a whole quarter of its timeline; 500 roots with
    20 each give 10,000 named timestamps. In the file form.
    """
    timelines = [
        {"id": f"clt_{n}", "unit": "quarters", "length": [per_root, 1]}
        for n in range(1, roots + 1)
    ]
    timestamps = [
        {
            "id": f"timestamp_{(n - 1) * per_root + k + 1}",
            "timeline": f"clt_{n}",
            "coordinate": [k, 1],
            "name": f"beat {k + 1} of {n}",
        }
        for n in range(1, roots + 1)
        for k in range(per_root)
    ]
    return with_file_ids(
        {
            "timetoshare": "0.2.0",
            "timelines": timelines,
            "graphical": {"timestamps": timestamps},
        }
    )


def long_tables(roots: int = 38, anchors: int = 340) -> dict[str, Any]:
    """``roots`` recordings, each with a ``LinearMap`` and a long ``TableMap``.

    The table maps seconds to measures through ``anchors`` Fraction pairs,
    its positions strictly increasing by 461/1000 of a second, its values
    by a quarter of a measure, as a DJ application's beat grid does. In the
    file form.
    """
    timelines = []
    for n in range(1, roots + 1):
        timelines.append(
            {
                "id": f"dpt_{n}",
                "unit": "seconds",
                "length": 600.0,
                "conversion_maps": [
                    {
                        "id": f"cmap_{n}",
                        "type": "LinearMap",
                        "source_unit": "seconds",
                        "target_unit": "samples",
                        "scalar": 48000,
                    },
                    {
                        "id": f"tmap_{n}",
                        "type": "TableMap",
                        "name": "beat grid",
                        "source_unit": "seconds",
                        "target_unit": "floating_measures",
                        "extrapolate": "linear",
                        "x_values": [[461 * k + n, 1000] for k in range(anchors)],
                        "y_values": [[k, 4] for k in range(anchors)],
                    },
                ],
            }
        )
    return with_file_ids({"timetoshare": "0.2.0", "timelines": timelines})
