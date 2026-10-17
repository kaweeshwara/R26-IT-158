from __future__ import annotations

import argparse
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPOSITORY_ROOT = HERE.parents[1]
SOURCE_FILES = {
    REPOSITORY_ROOT / "sinhalacheck" / "services" / "fusion" / "main.py": "main.py",
    REPOSITORY_ROOT / "sinhalacheck" / "services" / "fusion" / "weights.json": "weights.json",
    HERE / "Dockerfile": "Dockerfile",
    HERE / "requirements.txt": "requirements.txt",
    HERE / "README.md": "README.md",
}


def prepare_space(destination: Path, force: bool = False) -> list[Path]:
    destination = destination.expanduser().resolve()
    if destination == REPOSITORY_ROOT or REPOSITORY_ROOT in destination.parents:
        raise ValueError("Choose an output folder outside the source repository.")
    if destination.exists() and not destination.is_dir():
        raise ValueError(f"Output path is not a directory: {destination}")

    conflicts = [destination / name for name in SOURCE_FILES.values()
                 if (destination / name).exists()]
    if conflicts and not force:
        names = ", ".join(str(path) for path in conflicts)
        raise FileExistsError(f"Refusing to overwrite existing Space files: {names}")

    destination.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for source, name in SOURCE_FILES.items():
        if not source.is_file():
            raise FileNotFoundError(f"Required deployment source is missing: {source}")
        target = destination / name
        shutil.copy2(source, target)
        created.append(target)
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Hugging Face Docker Space folder.")
    parser.add_argument("destination", type=Path)
    parser.add_argument("--force", action="store_true", help="Replace generated files in destination.")
    args = parser.parse_args()
    for path in prepare_space(args.destination, args.force):
        print(f"Prepared {path}")
    print("Next: configure MODULE1_URL and MODULE2_URL in Space Settings, then deploy.")


if __name__ == "__main__":
    main()
