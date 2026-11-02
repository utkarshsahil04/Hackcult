"""Command-line entry point for the recognition artifact lifecycle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

from raahein_ml.config import MLConfig, load_config
from raahein_ml.encoders import fetch_models
from raahein_ml.evaluate import (
    evaluate_frozen_artifact,
    update_readme,
    validate_report_path,
    verify_readme_report,
    write_report,
)
from raahein_ml.manifest import ManifestError, read_manifest
from raahein_ml.schemas import RecognitionError
from raahein_ml.service import RecognitionService, resolve_artifact_path
from raahein_ml.workflow import (
    build_gallery_indexes,
    calibrate_staged_artifact,
    validate_final_artifact,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="path to models.yaml")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("fetch-models", help="download all immutable checkpoints")

    build = commands.add_parser("build", help="embed the gallery and stage three indexes")
    build.add_argument("--staging", type=Path)

    calibrate = commands.add_parser("calibrate", help="calibrate gates and finalize artifact")
    calibrate.add_argument("--staging", type=Path)

    validate = commands.add_parser("validate", help="validate a finalized artifact")
    validate.add_argument("--artifact", type=Path)

    smoke = commands.add_parser("smoke", help="warm real models and identify one local image")
    smoke.add_argument("--artifact", type=Path)
    smoke.add_argument("--image", type=Path)

    evaluate = commands.add_parser("evaluate", help="run the untouched final evaluation")
    evaluate.add_argument("--artifact", type=Path)
    evaluate.add_argument("--report", type=Path)
    evaluate.add_argument("--update-readme", action="store_true")
    return parser


def _smoke_image(config: MLConfig, configured_image: Path | None) -> Path:
    if configured_image is not None:
        return configured_image.resolve()
    rows = read_manifest(config.paths.manifest)
    gallery = [row for row in rows if row.status == "accepted" and row.split == "gallery"]
    if not gallery:
        raise ManifestError("smoke test needs an accepted gallery image")
    local = Path(*Path(gallery[0].local_path).parts)
    return (config.repository_root / local).resolve()


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        config = load_config(args.config)
        if args.command == "fetch-models":
            fetch_models(config)
        elif args.command == "build":
            path = build_gallery_indexes(config, args.staging)
            print(path)
        elif args.command == "calibrate":
            path = calibrate_staged_artifact(config, args.staging)
            print(path)
        elif args.command == "validate":
            artifact = resolve_artifact_path(args.artifact or config.paths.artifacts)
            bundle = validate_final_artifact(config, artifact)
            print(bundle.artifact_id)
        elif args.command == "smoke":
            artifact = resolve_artifact_path(args.artifact or config.paths.artifacts)
            service = RecognitionService(config, artifact_path=artifact)
            service.start()
            with Image.open(_smoke_image(config, args.image)) as image:
                image.load()
                print(json.dumps(service.identify(image).to_dict(), indent=2, sort_keys=True))
        else:
            artifact = resolve_artifact_path(args.artifact or config.paths.artifacts)
            report_path = validate_report_path(
                args.report
                or config.repository_root / "ml" / "reports" / "evaluation.json",
                config,
                artifact,
            )
            report = evaluate_frozen_artifact(config, artifact)
            write_report(report_path, report)
            if args.update_readme:
                readme = config.repository_root / "README.md"
                update_readme(readme, report)
                verify_readme_report(readme, report)
            print(report_path)
    except (ManifestError, RecognitionError, OSError, ValueError) as exc:
        print(f"ML workflow error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
