from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

import raahein_ml.workflow as workflow
from raahein_ml.config import MODEL_NAMES, MLConfig, ModelSpec
from raahein_ml.manifest import ManifestRow


def _gallery_row(image_id: str, monument_id: str) -> ManifestRow:
    return ManifestRow(
        image_id=image_id,
        source_id=image_id,
        collection="curated",
        monument_id=monument_id,
        component="",
        local_path=f"data/raw/{image_id}",
        source_group=image_id,
        source_page_url=f"https://example.org/source/{image_id}",
        download_url=f"https://example.org/download/{image_id}",
        author="Author",
        license_id="CC-BY-4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        attribution="Author, CC BY 4.0",
        image_format="jpeg",
        width=300,
        height=300,
        file_size_bytes=100,
        sha256=hashlib.sha256(image_id.encode()).hexdigest(),
        phash=hashlib.sha256(f"phash-{image_id}".encode()).hexdigest()[:16],
        duplicate_group=f"dup-{image_id}",
        split_group=f"split-{image_id}",
        status="accepted",
        split="gallery",
    )


class _FakeEncoder:
    def __init__(self, spec: ModelSpec) -> None:
        self.name = spec.name
        self.spec = spec
        self.loaded = False
        self.warmed = False

    @property
    def extraction_config(self) -> dict[str, object]:
        return {"adapter": self.name}

    def load(self) -> None:
        self.loaded = True

    def warmup(self) -> None:
        self.warmed = True

    def encode(self, images: object) -> np.ndarray:
        raise AssertionError("cache fixture should avoid image decoding")


class _FakeCache:
    def __init__(self, _root: Path) -> None:
        pass

    def get_or_compute(
        self,
        *,
        spec: ModelSpec,
        compute: object,
        **_kwargs: object,
    ) -> np.ndarray:
        vector = np.zeros(spec.dimension, dtype=np.float32)
        vector[0] = 1.0
        return vector


def test_build_workflow_passes_sorted_gallery_to_all_indexes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cpu_config: MLConfig,
) -> None:
    gallery = [
        _gallery_row(f"{slug}-{index}", slug)
        for slug in reversed(cpu_config.canonical_monument_ids)
        for index in reversed(range(8))
    ]
    validations: list[tuple[bool, bool]] = []
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        workflow,
        "read_manifest",
        lambda path: [] if path.name == "independent_test.csv" else gallery,
    )
    monkeypatch.setattr(
        workflow,
        "validate_manifests",
        lambda *_args, rehash, require_independent_count: validations.append(
            (rehash, require_independent_count)
        ),
    )
    monkeypatch.setattr(
        workflow,
        "create_encoder",
        lambda spec, _config: _FakeEncoder(spec),
    )
    monkeypatch.setattr(workflow, "EmbeddingCache", _FakeCache)
    monkeypatch.setattr(workflow, "semantic_csv_hash", lambda path: path.name)

    def fake_build(path: Path, **kwargs: object) -> Path:
        captured.update(kwargs)
        return path

    monkeypatch.setattr(workflow, "build_staged_artifact", fake_build)
    staging = tmp_path / "staging"
    assert workflow.build_gallery_indexes(cpu_config, staging) == staging
    assert validations == [(True, True)]
    mapping = captured["mapping"]
    assert [row.image_id for row in mapping] == sorted(row.image_id for row in gallery)
    embeddings = captured["embeddings"]
    assert set(embeddings) == set(MODEL_NAMES)
    for name in MODEL_NAMES:
        assert embeddings[name].shape == (120, cpu_config.models[name].dimension)
