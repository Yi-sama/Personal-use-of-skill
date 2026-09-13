from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resize an image to exact dimensions.")
    parser.add_argument("--input", required=True, help="Input image path.")
    parser.add_argument("--output", required=True, help="Output image path.")
    parser.add_argument("--width", type=int, required=True, help="Output width.")
    parser.add_argument("--height", type=int, required=True, help="Output height.")
    parser.add_argument("--quality", type=int, default=95, help="JPEG/WebP quality from 1 to 100.")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> tuple[Path, Path]:
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    if not input_path.is_file():
        raise ValueError(f"Input image not found: {input_path}")
    if args.width < 1 or args.height < 1:
        raise ValueError("--width and --height must be positive.")
    if not 1 <= args.quality <= 100:
        raise ValueError("--quality must be between 1 and 100.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return input_path, output_path


def resize_with_pillow(input_path: Path, output_path: Path, width: int, height: int, quality: int) -> bool:
    try:
        from PIL import Image  # type: ignore[import-not-found]
    except Exception:
        return False

    with Image.open(input_path) as image:
        resized = image.resize((width, height), Image.Resampling.LANCZOS)
        try:
            suffix = output_path.suffix.lower()
            if suffix in {".jpg", ".jpeg"} and resized.mode not in {"RGB", "L"}:
                resized = resized.convert("RGB")
            save_kwargs: dict[str, object] = {}
            if suffix in {".jpg", ".jpeg", ".webp"}:
                save_kwargs["quality"] = quality
            resized.save(output_path, **save_kwargs)
        finally:
            resized.close()
    return True


def resize_with_imagemagick(input_path: Path, output_path: Path, width: int, height: int, quality: int) -> bool:
    executable = shutil.which("magick")
    command: list[str]
    if executable:
        command = [executable, str(input_path), "-resize", f"{width}x{height}!", "-quality", str(quality), str(output_path)]
    else:
        executable = shutil.which("convert")
        if not executable:
            return False
        command = [executable, str(input_path), "-resize", f"{width}x{height}!", "-quality", str(quality), str(output_path)]
    run_checked(command)
    return True


def resize_with_sips(input_path: Path, output_path: Path, width: int, height: int) -> bool:
    if platform.system() != "Darwin":
        return False
    executable = shutil.which("sips")
    if not executable:
        return False
    run_checked([executable, "-z", str(height), str(width), str(input_path), "--out", str(output_path)])
    return True


def resize_with_windows_powershell(input_path: Path, output_path: Path, width: int, height: int, quality: int) -> bool:
    if platform.system() != "Windows":
        return False
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if not executable:
        return False
    script = Path(__file__).resolve().with_name("resize_image.ps1")
    if not script.is_file():
        return False
    run_checked(
        [
            executable,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-InputPath",
            str(input_path),
            "-OutputPath",
            str(output_path),
            "-Width",
            str(width),
            "-Height",
            str(height),
            "-Quality",
            str(quality),
        ]
    )
    return True


def run_checked(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(stderr or f"Command failed with exit code {completed.returncode}: {command[0]}")


def main() -> int:
    args = parse_args()
    input_path, output_path = validate_args(args)

    backends = [
        ("Pillow", lambda: resize_with_pillow(input_path, output_path, args.width, args.height, args.quality)),
        (
            "ImageMagick",
            lambda: resize_with_imagemagick(input_path, output_path, args.width, args.height, args.quality),
        ),
        ("macOS sips", lambda: resize_with_sips(input_path, output_path, args.width, args.height)),
        (
            "Windows PowerShell",
            lambda: resize_with_windows_powershell(input_path, output_path, args.width, args.height, args.quality),
        ),
    ]

    errors: list[str] = []
    for name, backend in backends:
        try:
            if backend():
                print(output_path)
                return 0
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: {exc}")

    details = "; ".join(errors) if errors else "no supported backend found"
    raise RuntimeError(
        "--size-policy resize requires one available image backend: Pillow, ImageMagick, macOS sips, "
        f"or Windows PowerShell/System.Drawing ({details})."
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
