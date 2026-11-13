"""Dataset-backed recognition: embed the local Indian-monuments dataset, calibrate, serve.

Reuses the frozen encoders, top-3 aggregation, RRF and rejection calibration from this
package. It skips the licence-manifest workflow (the dataset licence is unconfirmed, so
this artifact is for the hackathon demo only). Search is a numpy matmul, which is exactly
what IndexFlatIP computes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from raahein_ml.calibration import (
    LabeledTrace,
    calibrate,
    fusion_accept,
    gates_from_metadata,
    single_accept,
)
from raahein_ml.config import MODEL_NAMES, MLConfig, load_config
from raahein_ml.dedupe import phash_hamming_distance
from raahein_ml.encoders import create_encoder
from raahein_ml.fusion import aggregate_monument_scores, reciprocal_rank_fusion
from raahein_ml.manifest import _perceptual_hash
from raahein_ml.schemas import (
    ArtifactError,
    InferenceError,
    NotReadyError,
    PredictionTrace,
    RankedMonument,
)

ARTIFACT_NAME = "dataset-v1"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".jfif", ".png", ".webp"}
NEAR_DUPLICATE_DISTANCE = 6
CALIBRATION_FRACTION = 0.15
NEGATIVES_PER_CLASS = 20
MIN_EXTRA_IMAGES = 10  # fewer cannot be split into gallery / calibration / test sensibly
# Stricter than models.yaml (0.05, locked for the licensed pipeline): a wrong answer is worse.
MAX_OOD_FALSE_ACCEPT = 0.02

# Dataset folder -> canonical slug in backend seed data. Qutb components share one identity.
CLASS_TO_SLUG = {
    "tajmahal": "taj-mahal",
    "humayun_s tomb": "humayuns-tomb",
    "fatehpur sikri": "fatehpur-sikri",
    "qutub_minar": "qutb-complex",
    "alai_darwaza": "qutb-complex",
    "alai_minar": "qutb-complex",
    "iron_pillar": "qutb-complex",
    "jamali_kamali_tomb": "mehrauli-archaeological-park",
    "lotus_temple": "lotus-temple",
    "india gate pics": "india-gate",  # test/ spelling india_gate is aliased below
}
# Every other dataset folder is a non-target monument. Split by class so the calibration and
# test negatives never share a building.
NEGATIVE_CALIBRATION = {
    "ajanta caves", "charar-e- sharif", "chhota_imambara", "ellora caves",
    "gateway of india", "khajuraho", "sun temple konark",
    "basilica_of_bom_jesus", "golden temple", "tanjavur temple",
}  # fmt: skip
NEGATIVE_TEST = {"charminar", "hawa mahal pics", "mysore_palace", "victoria memorial"}
# test/ spells two folders differently from train/.
FOLDER_ALIASES = {"hawa mahal": "hawa mahal pics", "india_gate": "india gate pics"}


@dataclass(frozen=True, slots=True)
class Identification:
    status: str  # "identified" | "uncertain"
    strategy: str
    candidates: tuple[RankedMonument, ...]  # top 3 under the active strategy
    artifact_version: str


def artifact_dir(config: MLConfig) -> Path:
    return config.paths.artifacts / ARTIFACT_NAME


def _trace(vectors: dict[str, np.ndarray], gallery: dict[str, np.ndarray], labels: list[str],
           config: MLConfig) -> PredictionTrace:
    rankings = {
        name: aggregate_monument_scores(
            gallery[name] @ vectors[name], labels, top_n=config.index.aggregation_top_n
        )
        for name in vectors
    }
    fused = () if len(rankings) == 1 else reciprocal_rank_fusion(
        rankings, rrf_k=config.fusion.rrf_k, weights=config.fusion.weights
    )
    return PredictionTrace(model_rankings=rankings, fusion_ranking=fused)


def _scan(dataset: Path) -> list[tuple[Path, str, str | None]]:
    """(path, dataset split, folder key) for every image."""
    rows = []
    for split in ("train", "test"):
        for folder in sorted((dataset / split).iterdir()):
            if not folder.is_dir():
                continue
            key = FOLDER_ALIASES.get(folder.name.lower(), folder.name.lower())
            for path in sorted(folder.iterdir()):
                if path.suffix.lower() in IMAGE_SUFFIXES:
                    rows.append((path, split, key))
    return rows


def _load(path: Path) -> Image.Image | None:
    try:
        with Image.open(path) as image:
            image.load()
            return image.copy()
    except Exception as exc:
        print(f"skip unreadable image {path}: {exc}", file=sys.stderr)
        return None


def _plan_roles(dataset: Path, seed: int = 7, extra: Path | None = None) -> list[dict]:
    """Assign each usable image a role: gallery / calib / test / calib_neg / test_neg.

    `extra` holds one folder per canonical slug; it is split with the same calibration share
    and an equally sized test share, since it has no train/test folders of its own.
    """
    rng = random.Random(seed)
    rows = _scan(dataset)
    plan: list[dict] = []
    held: dict[str, list[Path]] = {}
    for path, split, key in rows:
        if key in CLASS_TO_SLUG:
            if split == "test":
                plan.append({"path": path, "role": "test", "slug": CLASS_TO_SLUG[key], "key": key})
            else:
                held.setdefault(key, []).append(path)
    for key, paths in sorted(held.items()):
        rng.shuffle(paths)
        calib_count = max(3, int(len(paths) * CALIBRATION_FRACTION))
        for index, path in enumerate(paths):
            role = "calib" if index < calib_count else "gallery"
            plan.append({"path": path, "role": role, "slug": CLASS_TO_SLUG[key], "key": key})
    pools: dict[str, list[Path]] = {}
    for path, _, key in rows:
        if key in NEGATIVE_CALIBRATION or key in NEGATIVE_TEST:
            pools.setdefault(key, []).append(path)
    for key, paths in sorted(pools.items()):
        rng.shuffle(paths)
        role = "calib_neg" if key in NEGATIVE_CALIBRATION else "test_neg"
        plan.extend(
            {"path": p, "role": role, "slug": None, "key": key}
            for p in paths[:NEGATIVES_PER_CLASS]
        )
    # After the negatives, so the dataset-only plan stays identical when extra is absent.
    for folder in sorted(f for f in extra.iterdir() if f.is_dir()) if extra else []:
        paths = [p for p in sorted(folder.iterdir()) if p.suffix.lower() in IMAGE_SUFFIXES]
        if len(paths) < MIN_EXTRA_IMAGES:
            print(f"skip extra {folder.name}: {len(paths)} images (< {MIN_EXTRA_IMAGES})",
                  file=sys.stderr)
            continue
        rng.shuffle(paths)
        held_out = max(3, int(len(paths) * CALIBRATION_FRACTION))
        for index, path in enumerate(paths):
            role = ("calib" if index < held_out
                    else "test" if index < 2 * held_out else "gallery")
            key = f"extra/{folder.name}"
            plan.append({"path": path, "role": role, "slug": folder.name, "key": key})
    return plan


def _embed(encoder, images: list[Image.Image], batch: int = 32) -> np.ndarray:
    chunks = [encoder.encode(images[i : i + batch]) for i in range(0, len(images), batch)]
    return np.concatenate(chunks)


def _strategy_report(traces: list[LabeledTrace], negatives: list[PredictionTrace], strategy: str,
                     accept) -> dict:
    top1 = top3 = accepted = correct_accepted = 0
    for sample in traces:
        ranking = sample.trace.ranking(strategy)
        hit = ranking[0].monument_id == sample.monument_id
        top1 += hit
        top3 += sample.monument_id in [item.monument_id for item in ranking[:3]]
        if accept(sample.trace):
            accepted += 1
            correct_accepted += hit
    n = len(traces)
    return {
        "top1": top1 / n,
        "top3": top3 / n,
        "coverage": accepted / n,
        "selective_accuracy": correct_accepted / max(1, accepted),
        "ood_false_accept": sum(accept(t) for t in negatives) / max(1, len(negatives)),
    }


def build(dataset: Path, config: MLConfig, out: Path | None = None,
          extra: Path | None = None) -> Path:
    started = time.time()
    plan = _plan_roles(dataset, extra=extra)
    images: list[Image.Image] = []
    kept: list[dict] = []
    for item in plan:
        image = _load(item["path"])
        if image is not None:
            images.append(image)
            kept.append(item)
    hashes = [_perceptual_hash(image) for image in images]

    gallery_hashes = [h for h, i in zip(hashes, kept, strict=False) if i["role"] == "gallery"]
    keep_mask = []
    dropped = 0
    for h, item in zip(hashes, kept, strict=False):
        leaks = item["role"] in {"calib", "test", "calib_neg", "test_neg"} and any(
            phash_hamming_distance(h, g) <= NEAR_DUPLICATE_DISTANCE for g in gallery_hashes
        )
        dropped += leaks
        keep_mask.append(not leaks)
    images = [i for i, k in zip(images, keep_mask, strict=False) if k]
    kept = [i for i, k in zip(kept, keep_mask, strict=False) if k]
    print(f"images: {len(kept)} usable, {dropped} dropped as near-duplicates of the gallery")

    matrices: dict[str, np.ndarray] = {}
    for name in MODEL_NAMES:
        encoder = create_encoder(config.models[name], config, local_files_only=False)
        encoder.load()
        matrices[name] = _embed(encoder, images)
        print(f"embedded {name}: {matrices[name].shape}")
        del encoder

    def rows(role: str) -> np.ndarray:
        return np.array([i["role"] == role for i in kept])

    gallery_mask = rows("gallery")
    labels = [i["slug"] for i, m in zip(kept, gallery_mask, strict=False) if m]
    gallery = {name: matrices[name][gallery_mask] for name in MODEL_NAMES}

    def traces(role: str) -> list[tuple[dict, PredictionTrace]]:
        mask = rows(role)
        selected = [i for i, m in zip(kept, mask, strict=False) if m]
        vectors = {name: matrices[name][mask] for name in MODEL_NAMES}
        return [
            (item, _trace({n: vectors[n][k] for n in MODEL_NAMES}, gallery, labels, config))
            for k, item in enumerate(selected)
        ]

    calib = [LabeledTrace(t, i["slug"]) for i, t in traces("calib")]
    calib_neg = [t for _, t in traces("calib_neg")]
    result = calibrate(
        calib,
        calib_neg,
        maximum_false_acceptance=MAX_OOD_FALSE_ACCEPT,
        single_margin=True,
        minimum_winner_models=config.calibration.minimum_winner_models,
    )
    print(f"active strategy: {result.active_strategy}")

    test = [LabeledTrace(t, i["slug"]) for i, t in traces("test")]
    test_neg = [t for _, t in traces("test_neg")]
    report = {
        "gallery_per_monument": {s: labels.count(s) for s in sorted(set(labels))},
        "samples": {"calibration": len(calib), "calibration_ood": len(calib_neg),
                    "test": len(test), "test_ood": len(test_neg)},
        "near_duplicates_dropped": dropped,
        "calibration": result.summary_dict(),
        "test": {},
    }
    for name in (*MODEL_NAMES, "fusion"):
        if name == "fusion":
            def accept(t, gate=result.fusion_gate):
                return fusion_accept(t, gate)
        else:
            def accept(t, n=name, gate=result.single_gates[name]):
                return single_accept(t, n, gate)
        report["test"][name] = _strategy_report(test, test_neg, name, accept)
        print(name, {k: round(v, 3) for k, v in report["test"][name].items()})

    out = out or artifact_dir(config)
    out.mkdir(parents=True, exist_ok=True)
    for name in MODEL_NAMES:
        np.save(out / f"{name}.npy", gallery[name])
    (out / "labels.json").write_text(json.dumps(labels), encoding="utf-8")
    gates = {"gates": result.gates_dict(), "active_strategy": result.active_strategy}
    (out / "gates.json").write_text(json.dumps(gates, indent=2), encoding="utf-8")
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {out} in {time.time() - started:.0f}s")
    return out


class DatasetRecognizer:
    """Loads the artifact and the encoders it needs once; thread-safe via the caller's lock."""

    def __init__(self, config: MLConfig, path: Path | None = None) -> None:
        self.config = config
        self.path = path or artifact_dir(config)
        self._encoders: dict = {}
        self._gallery: dict[str, np.ndarray] = {}
        self._labels: list[str] = []
        self._gates = None
        self._strategy = ""
        self.version = ""

    @property
    def ready(self) -> bool:
        return bool(self._encoders)

    def load(self) -> None:
        try:
            labels = json.loads((self.path / "labels.json").read_text(encoding="utf-8"))
            meta = json.loads((self.path / "gates.json").read_text(encoding="utf-8"))
            # Only fusion uses every model. Loading the others wastes memory and slows each photo.
            strategy = meta["active_strategy"]
            names = MODEL_NAMES if strategy == "fusion" else (strategy,)
            gallery = {n: np.load(self.path / f"{n}.npy") for n in names}
        except (OSError, ValueError, KeyError) as exc:
            raise ArtifactError(f"recognition artifact missing or corrupt: {self.path}") from exc
        if any(len(m) != len(labels) for m in gallery.values()):
            raise ArtifactError("artifact embeddings and labels disagree")
        self._single, self._fusion = gates_from_metadata(meta["gates"])
        self._strategy = meta["active_strategy"]
        self._labels, self._gallery = labels, gallery
        self.version = hashlib.sha256(
            json.dumps([labels, meta], sort_keys=True).encode()
        ).hexdigest()[:12]
        encoders = {}
        for name in names:
            encoder = create_encoder(self.config.models[name], self.config)
            encoder.load()
            encoder.warmup()
            encoders[name] = encoder
        self._encoders = encoders

    def identify(self, image: Image.Image) -> Identification:
        if not self.ready:
            raise NotReadyError("recognition pipeline is not loaded")
        try:
            vectors = {n: e.encode([image])[0] for n, e in self._encoders.items()}
            trace = _trace(vectors, self._gallery, self._labels, self.config)
        except Exception as exc:
            raise InferenceError("monument recognition inference failed") from exc
        if self._strategy == "fusion":
            accepted = fusion_accept(trace, self._fusion)
        else:
            accepted = single_accept(trace, self._strategy, self._single[self._strategy])
        return Identification(
            status="identified" if accepted else "uncertain",
            strategy=self._strategy,
            candidates=trace.ranking(self._strategy)[:3],
            artifact_version=self.version,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build", help="embed the dataset, calibrate, write the artifact")
    build_parser.add_argument("--dataset", required=True, type=Path, help="dir with train/ test/")
    build_parser.add_argument("--extra", type=Path, help="dir of <slug>/ photo folders to add")
    args = parser.parse_args()
    if args.command == "build":
        build(args.dataset, load_config(), extra=args.extra)


if __name__ == "__main__":
    main()
