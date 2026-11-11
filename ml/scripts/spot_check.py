"""Run DatasetRecognizer over a folder of photos listed in a manifest and print a table.

manifest.json: [{"file": "x.jpg", "expected": "taj-mahal" | null, "monument": "name"}, ...]
expected=null means the photo is outside the recognised set and must come back "uncertain".
Pass several --artifact dirs (e.g. a backup and the new build) to compare them side by side.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from raahein_ml.config import load_config
from raahein_ml.dataset_pipeline import DatasetRecognizer


def verdict(expected: str | None, status: str, top: str) -> str:
    if status == "uncertain":
        return "ok" if expected is None else "missed"
    return "ok" if expected == top else "WRONG"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--artifact", required=True, type=Path, nargs="+")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    config = load_config()
    results = []  # per artifact: list of (status, top, score)
    for path in args.artifact:
        recognizer = DatasetRecognizer(config, path)
        recognizer.load()
        rows = []
        for item in manifest:
            with Image.open(args.manifest.parent / item["file"]) as image:
                result = recognizer.identify(image.convert("RGB"))
            top = result.candidates[0]
            rows.append((result.status, top.monument_id, top.score))
        results.append(rows)
        print(f"artifact {path}: strategy={recognizer._strategy}")
    for i, item in enumerate(manifest):
        cells = " | ".join(
            f"{s:<10} {t:<28} {sc:.3f} {verdict(item['expected'], s, t)}"
            for s, t, sc in (r[i] for r in results)
        )
        print(f"{item['file']:<22} expect={item['expected'] or 'none':<14} | {cells}")
    for path, rows in zip(args.artifact, results, strict=True):
        pairs = [(m["expected"], r) for m, r in zip(manifest, rows, strict=True)]
        out = [(e, r) for e, r in pairs if e is None]
        tgt = [(e, r) for e, r in pairs if e is not None]
        wrong = sum(r[0] == "identified" for _, r in out)
        right = sum(r[0] == "identified" and r[1] == e for e, r in tgt)
        bad = sum(r[0] == "identified" and r[1] != e for e, r in tgt)
        print(
            f"{path}: out-of-set wrongly identified {wrong}/{len(out)}; targets identified "
            f"correctly {right}/{len(tgt)}, wrongly {bad}, uncertain {len(tgt) - right - bad}"
        )


if __name__ == "__main__":
    main()
