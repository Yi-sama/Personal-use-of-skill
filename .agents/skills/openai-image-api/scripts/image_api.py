from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import struct
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-image-2"
DEFAULT_SIZE = "2048x1152"
DEFAULT_QUALITY = "high"
DEFAULT_OUT = "outputs/image.png"
MAX_IMAGE_BYTES = 50 * 1024 * 1024
AUTH_FILE_NAME = "auth.json"
CONFIG_FILE_NAME = "config.toml"
KEY_FIELD = "OPENAI_API_KEY"
IMAGE_KEY_FIELD = "OPENAI_IMAGE_API_KEY"
BASE_URL_FIELD = "OPENAI_BASE_URL"
IMAGE_BASE_URL_FIELD = "OPENAI_IMAGE_BASE_URL"


@dataclass(frozen=True)
class ImageInfo:
    format: str
    width: int
    height: int
    has_alpha: bool


@dataclass(frozen=True)
class ProviderConfig:
    api_key: str
    base_url: str
    codex_home: Path


class RequestError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, code: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate or edit images with the OpenAI Image API.")
    parser.add_argument("--prompt", help="Prompt text.")
    parser.add_argument("--prompt-file", help="UTF-8 text file with one prompt per non-empty line.")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Output file path.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Image model.")
    parser.add_argument("--mode", choices=["auto", "generate", "edit"], default="auto")
    parser.add_argument("--codex-home", help="Override Codex root directory for auth.json/config.toml.")
    parser.add_argument("--base-url", help="Temporary provider base_url override.")
    parser.add_argument("--base-url-env", help="Environment variable containing a temporary provider base_url override.")
    parser.add_argument("--api-key-env", help="Environment variable containing a temporary API key override.")
    parser.add_argument("--api-key", help="Temporary direct API key override; prefer --api-key-env.")
    parser.add_argument("--size", default=DEFAULT_SIZE, help="auto or WIDTHxHEIGHT.")
    parser.add_argument("--quality", default=DEFAULT_QUALITY, help="auto, low, medium, or high.")
    parser.add_argument("--n", type=int, default=1, help="Number of images per prompt.")
    parser.add_argument("--image", action="append", default=[], help="Input/reference image path.")
    parser.add_argument("--image-role", action="append", default=[], help="Role label for the matching input image.")
    parser.add_argument("--mask", help="Mask path for localized edits.")
    parser.add_argument("--background", choices=["auto", "opaque", "transparent"], help="auto or opaque for gpt-image-2.")
    parser.add_argument("--output-format", choices=["png", "jpeg", "webp"], help="Requested output format.")
    parser.add_argument("--output-compression", type=int, help="0-100 for jpeg/webp.")
    parser.add_argument("--moderation", choices=["auto", "low"], help="Moderation strictness.")
    parser.add_argument("--input-fidelity", choices=["low", "high"], help="Supported by some models; omit for gpt-image-2.")
    parser.add_argument("--stream", action="store_true", help="Stream Image API partial images for text-only generations.")
    parser.add_argument("--partial-images", type=int, default=0, help="1-3 partial images when --stream is set; 0 omits the field.")
    parser.add_argument("--timeout", type=int, default=1800, help="HTTP timeout seconds; 0 disables the client-side timeout.")
    parser.add_argument("--max-retries", type=int, default=2, help="Retry transient 429/5xx/network failures this many times.")
    parser.add_argument("--retry-delay", type=float, default=1.0, help="Initial retry delay in seconds; doubles after each retry.")
    parser.add_argument("--dry-run", action="store_true", help="Print the request shape without sending it or resolving API keys.")
    parser.add_argument("--user-agent", default="OpenAI-Image-API-Skill/1.0")
    parser.add_argument(
        "--expected-size",
        help='Expected output dimensions as WIDTHxHEIGHT; defaults to --size when --size is not "auto".',
    )
    parser.add_argument(
        "--size-policy",
        choices=["ignore", "warn", "error", "resize"],
        default="warn",
        help="What to do when the returned image dimensions do not match the expected size.",
    )
    parser.add_argument(
        "--allow-upscale",
        action="store_true",
        help="Allow --size-policy resize to enlarge a smaller provider image; use only after explicit user approval.",
    )
    parser.add_argument("--resize-quality", type=int, default=95, help="JPEG quality used by --size-policy resize.")
    return parser.parse_args()


def load_prompts(prompt: str | None, prompt_file: str | None) -> list[str]:
    if bool(prompt) == bool(prompt_file):
        raise ValueError("Use exactly one of --prompt or --prompt-file.")
    if prompt:
        return [prompt]
    lines = Path(prompt_file).expanduser().read_text(encoding="utf-8").splitlines()
    prompts = [line.strip() for line in lines if line.strip()]
    if not prompts:
        raise ValueError(f"Prompt file contains no prompts: {prompt_file}")
    return prompts


def resolve_codex_home(explicit_path: str | None) -> Path:
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()
    env_path = os.environ.get("CODEX_HOME")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_toml_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle)


def active_provider_config(codex_home: Path) -> dict[str, Any]:
    config = load_toml_if_exists(codex_home / CONFIG_FILE_NAME)
    provider_name = config.get("model_provider")
    providers = config.get("model_providers", {})
    if isinstance(provider_name, str) and isinstance(providers, dict):
        provider = providers.get(provider_name)
        if isinstance(provider, dict):
            return provider
    return {}


def uses_active_provider(args: argparse.Namespace) -> bool:
    return not (
        args.base_url
        or args.base_url_env
        or os.environ.get(IMAGE_BASE_URL_FIELD)
        or os.environ.get(BASE_URL_FIELD)
    )


def resolve_api_key(args: argparse.Namespace, codex_home: Path) -> str:
    if args.api_key and args.api_key_env:
        raise ValueError("Use only one of --api-key or --api-key-env.")
    if args.api_key:
        api_key = args.api_key.strip()
        if not api_key:
            raise ValueError("--api-key must not be empty.")
        return api_key
    if args.api_key_env:
        env_name = args.api_key_env.strip()
        if not env_name:
            raise ValueError("--api-key-env must name a non-empty environment variable.")
        api_key = os.environ.get(env_name, "").strip()
        if not api_key:
            raise ValueError(f"Environment variable is empty or missing: {env_name}")
        return api_key
    image_env_api_key = os.environ.get(IMAGE_KEY_FIELD, "").strip()
    if image_env_api_key:
        return image_env_api_key
    env_api_key = os.environ.get(KEY_FIELD, "").strip()
    if env_api_key:
        return env_api_key
    auth = load_json_if_exists(codex_home / AUTH_FILE_NAME)
    image_api_key = auth.get(IMAGE_KEY_FIELD)
    if isinstance(image_api_key, str) and image_api_key.strip():
        return image_api_key.strip()
    api_key = auth.get(KEY_FIELD)
    if isinstance(api_key, str) and api_key.strip():
        return api_key.strip()
    provider_env_key = None
    if uses_active_provider(args):
        provider = active_provider_config(codex_home)
        provider_env_key = provider.get("env_key")
    if isinstance(provider_env_key, str) and provider_env_key.strip():
        provider_key_name = provider_env_key.strip()
        provider_api_key = os.environ.get(provider_key_name, "").strip()
        if provider_api_key:
            return provider_api_key
        provider_auth_key = auth.get(provider_key_name)
        if isinstance(provider_auth_key, str) and provider_auth_key.strip():
            return provider_auth_key.strip()
    raise ValueError(
        f"No API key found. Checked environment variables, {codex_home / AUTH_FILE_NAME}, "
        "then the active local provider env_key."
    )


def resolve_base_url(args: argparse.Namespace, codex_home: Path) -> str:
    if args.base_url:
        return clean_base_url(args.base_url)
    if args.base_url_env:
        env_name = args.base_url_env.strip()
        if not env_name:
            raise ValueError("--base-url-env must name a non-empty environment variable.")
        base_url = os.environ.get(env_name, "").strip()
        if not base_url:
            raise ValueError(f"Environment variable is empty or missing: {env_name}")
        return clean_base_url(base_url)
    image_env_base_url = os.environ.get(IMAGE_BASE_URL_FIELD)
    if image_env_base_url:
        return clean_base_url(image_env_base_url)
    env_base_url = os.environ.get(BASE_URL_FIELD)
    if env_base_url:
        return clean_base_url(env_base_url)
    provider = active_provider_config(codex_home)
    if isinstance(provider.get("base_url"), str):
        return clean_base_url(provider["base_url"])
    return DEFAULT_BASE_URL


def resolve_provider_config(args: argparse.Namespace) -> ProviderConfig:
    codex_home = resolve_codex_home(args.codex_home)
    return ProviderConfig(
        api_key=resolve_api_key(args, codex_home),
        base_url=resolve_base_url(args, codex_home),
        codex_home=codex_home,
    )


def determine_mode(args: argparse.Namespace) -> str:
    if args.mode != "auto":
        return args.mode
    if args.image or args.mask:
        return "edit"
    return "generate"


def validate_args(args: argparse.Namespace) -> None:
    mode = determine_mode(args)
    if args.api_key and args.api_key_env:
        raise ValueError("Use only one of --api-key or --api-key-env.")
    if args.quality not in {"auto", "low", "medium", "high"}:
        raise ValueError("--quality must be auto, low, medium, or high.")
    if args.n < 1:
        raise ValueError("--n must be at least 1.")
    if args.timeout < 0:
        raise ValueError("--timeout must be 0 or a positive number of seconds.")
    if args.max_retries < 0:
        raise ValueError("--max-retries must be 0 or a positive integer.")
    if args.retry_delay < 0:
        raise ValueError("--retry-delay must be 0 or a positive number of seconds.")
    if not 0 <= args.partial_images <= 3:
        raise ValueError("--partial-images must be between 0 and 3.")
    if args.partial_images and not args.stream:
        raise ValueError("--partial-images requires --stream.")
    if args.stream and mode != "generate":
        raise ValueError("--stream currently supports text-only /images/generations requests.")
    if args.stream and args.n != 1:
        raise ValueError("--stream currently requires --n 1.")
    if not 1 <= args.resize_quality <= 100:
        raise ValueError("--resize-quality must be between 1 and 100.")
    if args.image_role and len(args.image_role) > len(args.image):
        raise ValueError("--image-role count must not exceed --image count.")
    if args.mask and not args.image:
        raise ValueError("--mask requires at least one --image edit target.")
    if mode == "edit" and not args.image:
        raise ValueError("Edit/reference mode requires at least one --image.")
    if mode == "generate" and (args.image or args.mask):
        raise ValueError("--image and --mask require edit mode or auto mode.")
    if args.background == "transparent" and args.model == "gpt-image-2":
        raise ValueError('gpt-image-2 does not support background="transparent".')
    if args.input_fidelity and args.model == "gpt-image-2":
        raise ValueError("Do not send --input-fidelity with gpt-image-2.")
    if args.output_compression is not None and not 0 <= args.output_compression <= 100:
        raise ValueError("--output-compression must be between 0 and 100.")
    if args.output_compression is not None and args.output_format not in {"jpeg", "webp"}:
        raise ValueError("--output-compression only applies to jpeg or webp output.")
    validate_size(args.size)
    if args.expected_size:
        parse_plain_size(args.expected_size, "--expected-size")
    for path in [*args.image, args.mask]:
        if path:
            validate_file(path)
    if args.mask:
        validate_mask(args.image[0], args.mask)


def parse_plain_size(size: str, option_name: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)x(\d+)", size)
    if not match:
        raise ValueError(f"{option_name} must be WIDTHxHEIGHT.")
    width, height = map(int, match.groups())
    if width < 1 or height < 1:
        raise ValueError(f"{option_name} width and height must be positive.")
    return width, height


def validate_size(size: str) -> None:
    if size == "auto":
        return
    width, height = parse_plain_size(size, "--size")
    pixels = width * height
    if width % 16 or height % 16:
        raise ValueError("--size edges must be multiples of 16.")
    if max(width, height) > 3840:
        raise ValueError("--size max edge must be <= 3840.")
    if max(width, height) / min(width, height) > 3:
        raise ValueError("--size long-edge/short-edge ratio must be <= 3:1.")
    if not 655_360 <= pixels <= 8_294_400:
        raise ValueError("--size total pixels must be between 655,360 and 8,294,400.")


def validate_file(path: str) -> None:
    file_path = Path(path).expanduser()
    if not file_path.is_file():
        raise ValueError(f"File not found: {path}")
    if file_path.stat().st_size >= MAX_IMAGE_BYTES:
        raise ValueError(f"File must be under 50MB: {path}")


def validate_mask(source_path: str, mask_path: str) -> None:
    source = inspect_image(Path(source_path).expanduser())
    mask = inspect_image(Path(mask_path).expanduser())
    if source.format != mask.format:
        raise ValueError(
            "--mask format must match the first --image edit target "
            f"({source.format}); got {mask.format}: {mask_path}"
        )
    if (source.width, source.height) != (mask.width, mask.height):
        raise ValueError(
            "--mask dimensions must match the first --image edit target "
            f"({source.width}x{source.height}); got {mask.width}x{mask.height}: {mask_path}"
        )
    if not mask.has_alpha:
        raise ValueError(f"--mask must include an alpha channel: {mask_path}")


def prompt_with_roles(prompt: str, roles: list[str]) -> str:
    if not roles:
        return prompt
    lines = ["", "Input image roles:"]
    for index, role in enumerate(roles, start=1):
        lines.append(f"Image {index}: {role}")
    return prompt + "\n" + "\n".join(lines)


def clean_base_url(base_url: str) -> str:
    base_url = base_url.strip().rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        raise ValueError("base URL must start with http:// or https://")
    return base_url


def compact_json(data: dict[str, Any]) -> bytes:
    return json.dumps({k: v for k, v in data.items() if v is not None}, ensure_ascii=False).encode("utf-8")


def request_timeout(timeout: int) -> int | None:
    return None if timeout == 0 else timeout


def request_json(
    url: str,
    api_key: str,
    payload: dict[str, Any],
    timeout: int,
    user_agent: str,
    max_retries: int,
    retry_delay: float,
) -> dict[str, Any]:
    body = compact_json(payload)

    def send_once() -> dict[str, Any]:
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": user_agent,
            },
        )
        return read_json_response(req, timeout)

    return with_retries(send_once, max_retries, retry_delay, "Image API JSON request")


def request_multipart(
    url: str,
    api_key: str,
    fields: dict[str, str],
    files: list[tuple[str, Path]],
    timeout: int,
    user_agent: str,
    max_retries: int,
    retry_delay: float,
) -> dict[str, Any]:
    # 手写 multipart，避免给 skill 增加 requests 依赖。
    boundary = f"----openai-image-api-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        chunks.append(value.encode("utf-8"))
        chunks.append(b"\r\n")
    for field_name, path in files:
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{path.name}"\r\n'.encode()
        )
        chunks.append(f"Content-Type: {content_type}\r\n\r\n".encode())
        chunks.append(path.read_bytes())
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    body = b"".join(chunks)
    def send_once() -> dict[str, Any]:
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": user_agent,
            },
        )
        return read_json_response(req, timeout)

    return with_retries(send_once, max_retries, retry_delay, "Image API multipart request")


def read_json_response(req: urllib.request.Request, timeout: int) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(req, timeout=request_timeout(timeout)) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise_runtime_http_error(exc)
    except urllib.error.URLError as exc:
        raise RequestError(f"Failed to connect to provider: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RequestError("Provider request timed out.") from exc
    return json.loads(raw.decode("utf-8"))


def raise_runtime_http_error(exc: urllib.error.HTTPError) -> None:
    body = exc.read().decode("utf-8", errors="replace")
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        raise RequestError(f"HTTP {exc.code}: {redact_secret_text(body)}", status=exc.code) from exc
    error = parsed.get("error") if isinstance(parsed, dict) else None
    if isinstance(error, dict):
        request_id = exc.headers.get("x-request-id") or error.get("request_id")
        raw_code = error.get("code") or error.get("type")
        code = raw_code if isinstance(raw_code, str) else None
        raw_message = error.get("message")
        message = redact_secret_text(raw_message if isinstance(raw_message, str) else body)
        details = f"HTTP {exc.code}: {code}: {message}"
        if request_id:
            details += f" (request_id={request_id})"
        if error.get("moderation_details"):
            details += f" moderation_details={json.dumps(error['moderation_details'], ensure_ascii=False)}"
        raise RequestError(details, status=exc.code, code=code) from exc
    raise RequestError(f"HTTP {exc.code}: {redact_secret_text(body)}", status=exc.code) from exc


def redact_secret_text(text: str) -> str:
    text = re.sub(r"\bsk-[A-Za-z0-9_*\-]{8,}\b", "sk-REDACTED", text)
    return re.sub(r"Bearer\s+[A-Za-z0-9._*\-]{8,}", "Bearer REDACTED", text, flags=re.IGNORECASE)


def is_retryable_error(exc: RequestError) -> bool:
    non_retryable_codes = {
        "invalid_api_key",
        "invalid_request_error",
        "insufficient_quota",
        "image_generation_user_error",
        "model_not_found",
        "moderation_blocked",
    }
    if exc.code in non_retryable_codes:
        return False
    if exc.status is None:
        return True
    return exc.status in {408, 409, 429} or exc.status >= 500


def with_retries(
    operation: Any,
    max_retries: int,
    retry_delay: float,
    label: str,
) -> Any:
    for attempt in range(max_retries + 1):
        try:
            return operation()
        except RequestError as exc:
            if attempt >= max_retries or not is_retryable_error(exc):
                raise
            delay = retry_delay * (2**attempt)
            print(f"WARNING: {label} failed transiently; retrying in {delay:.1f}s: {exc}", file=sys.stderr)
            if delay:
                time.sleep(delay)
    raise RuntimeError("Retry loop exited unexpectedly.")


def build_generation_payload(args: argparse.Namespace, prompt: str) -> dict[str, Any]:
    return {
        "model": args.model,
        "prompt": prompt,
        "size": args.size,
        "quality": args.quality,
        "n": args.n,
        "background": args.background,
        "output_format": args.output_format,
        "output_compression": args.output_compression,
        "moderation": args.moderation,
        "stream": True if args.stream else None,
        "partial_images": args.partial_images if args.stream and args.partial_images else None,
    }


def build_edit_parts(args: argparse.Namespace, prompt: str) -> tuple[dict[str, str], list[tuple[str, Path]]]:
    fields: dict[str, str] = {
        "model": args.model,
        "prompt": prompt,
        "size": args.size,
        "quality": args.quality,
        "n": str(args.n),
    }
    optional = {
        "background": args.background,
        "output_format": args.output_format,
        "output_compression": None if args.output_compression is None else str(args.output_compression),
        "moderation": args.moderation,
        "input_fidelity": args.input_fidelity,
    }
    fields.update({k: v for k, v in optional.items() if v is not None})
    files = [("image[]", Path(image).expanduser()) for image in args.image]
    if args.mask:
        files.append(("mask", Path(args.mask).expanduser()))
    return fields, files


def extract_image_bytes(response: dict[str, Any], args: argparse.Namespace) -> list[bytes]:
    data = response.get("data")
    if not isinstance(data, list) or not data:
        raise RuntimeError("Response did not include data[].")
    images: list[bytes] = []
    for item in data:
        if isinstance(item, dict) and item.get("revised_prompt"):
            print(f"revised_prompt={item['revised_prompt']}", file=sys.stderr)
        if isinstance(item, dict) and item.get("b64_json"):
            images.append(base64.b64decode(item["b64_json"]))
        elif isinstance(item, dict) and item.get("url"):
            images.append(download_image_url(item["url"], args))
        else:
            raise RuntimeError("Response image item has neither b64_json nor url.")
    return images


def download_image_url(url: str, args: argparse.Namespace) -> bytes:
    def send_once() -> bytes:
        try:
            with urllib.request.urlopen(url, timeout=request_timeout(args.timeout)) as remote:
                return remote.read()
        except urllib.error.HTTPError as exc:
            raise_runtime_http_error(exc)
        except urllib.error.URLError as exc:
            raise RequestError(f"Failed to download provider image URL: {exc.reason}") from exc
        except TimeoutError as exc:
            raise RequestError("Provider image URL download timed out.") from exc

    return with_retries(send_once, args.max_retries, args.retry_delay, "Provider image URL download")


def request_stream(
    url: str,
    api_key: str,
    payload: dict[str, Any],
    timeout: int,
    user_agent: str,
    out: Path,
    args: argparse.Namespace,
) -> list[Path]:
    body = compact_json(payload)

    def send_once() -> list[Path]:
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": user_agent,
            },
        )
        saved_paths: list[Path] = []
        try:
            with urllib.request.urlopen(req, timeout=request_timeout(timeout)) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    event = json.loads(data)
                    event_type = event.get("type")
                    if event_type == "image_generation.partial_image":
                        path = write_stream_image(event.get("b64_json"), stream_partial_path(out, event), args, enforce_size=False)
                        if path:
                            saved_paths.append(path)
                    elif event_type in {"image_generation.completed", "image_generation.done"} or event.get("b64_json"):
                        path = write_stream_image(event.get("b64_json"), out, args, enforce_size=True)
                        if path:
                            saved_paths.append(path)
                    elif event_type in {"error", "image_generation.failed"}:
                        raise RuntimeError(json.dumps(event, ensure_ascii=False))
        except urllib.error.HTTPError as exc:
            raise_runtime_http_error(exc)
        except urllib.error.URLError as exc:
            raise RequestError(f"Failed to connect to provider: {exc.reason}") from exc
        except TimeoutError as exc:
            raise RequestError("Provider request timed out.") from exc
        if not saved_paths:
            raise RuntimeError("Stream ended without image data.")
        return saved_paths

    return with_retries(send_once, args.max_retries, args.retry_delay, "Image API stream request")


def stream_partial_path(out: Path, event: dict[str, Any]) -> Path:
    suffix = out.suffix or ".png"
    index = event.get("partial_image_index")
    return out.with_name(f"{out.stem}-partial-{index}{suffix}")


def write_stream_image(b64_json: Any, path: Path, args: argparse.Namespace, enforce_size: bool) -> Path | None:
    if not isinstance(b64_json, str) or not b64_json:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(b64_json))
    if enforce_size:
        enforce_size_policy(path, args)
    print(path)
    return path


def extension_for(args: argparse.Namespace, out: Path) -> str:
    if out.suffix:
        return out.suffix
    if args.output_format == "jpeg":
        return ".jpg"
    if args.output_format == "webp":
        return ".webp"
    return ".png"


def output_path(base: Path, args: argparse.Namespace, prompt_count: int, prompt_index: int, image_count: int, image_index: int) -> Path:
    suffix = extension_for(args, base)
    stem = base.stem if base.suffix else base.name
    parts: list[str] = []
    if prompt_count > 1:
        parts.append(str(prompt_index + 1))
    if image_count > 1:
        parts.append(str(image_index + 1))
    if parts:
        name = f"{stem}-{'-'.join(parts)}{suffix}"
    else:
        name = f"{stem}{suffix}"
    return base.with_name(name)


def write_outputs(images: list[bytes], base: Path, args: argparse.Namespace, prompt_count: int, prompt_index: int) -> list[Path]:
    base.parent.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for image_index, image in enumerate(images):
        path = output_path(base, args, prompt_count, prompt_index, len(images), image_index)
        path.write_bytes(image)
        enforce_size_policy(path, args)
        paths.append(path)
    return paths


def expected_dimensions(args: argparse.Namespace) -> tuple[int, int] | None:
    if args.expected_size:
        return parse_plain_size(args.expected_size, "--expected-size")
    if args.size == "auto":
        return None
    return parse_plain_size(args.size, "--size")


def image_dimensions(path: Path) -> tuple[int, int] | None:
    try:
        info = inspect_image(path)
    except ValueError:
        return None
    return info.width, info.height


def inspect_image(path: Path) -> ImageInfo:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return inspect_png(data, path)
    if data.startswith(b"\xff\xd8"):
        return inspect_jpeg(data, path)
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return inspect_webp(data, path)
    raise ValueError(f"Unsupported image format: {path}")


def inspect_png(data: bytes, path: Path) -> ImageInfo:
    if len(data) < 33 or data[12:16] != b"IHDR":
        raise ValueError(f"Invalid PNG image: {path}")
    width, height = struct.unpack(">II", data[16:24])
    color_type = data[25]
    has_alpha = color_type in {4, 6} or png_has_transparency_chunk(data)
    return ImageInfo("png", width, height, has_alpha)


def png_has_transparency_chunk(data: bytes) -> bool:
    offset = 8
    while offset + 8 <= len(data):
        chunk_length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        offset += 8
        if chunk_type == b"tRNS":
            return True
        offset += chunk_length + 4
    return False


def inspect_jpeg(data: bytes, path: Path) -> ImageInfo:
    index = 2
    sof_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    while index < len(data):
        while index < len(data) and data[index] != 0xFF:
            index += 1
        while index < len(data) and data[index] == 0xFF:
            index += 1
        if index >= len(data):
            return None
        marker = data[index]
        index += 1
        if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        if index + 2 > len(data):
            return None
        segment_length = struct.unpack(">H", data[index : index + 2])[0]
        if segment_length < 2 or index + segment_length > len(data):
            break
        if marker in sof_markers and segment_length >= 7:
            height, width = struct.unpack(">HH", data[index + 3 : index + 7])
            return ImageInfo("jpeg", width, height, False)
        index += segment_length
    raise ValueError(f"Unable to inspect JPEG dimensions: {path}")


def inspect_webp(data: bytes, path: Path) -> ImageInfo:
    index = 12
    while index + 8 <= len(data):
        chunk_type = data[index : index + 4]
        chunk_size = struct.unpack("<I", data[index + 4 : index + 8])[0]
        chunk_start = index + 8
        chunk_end = chunk_start + chunk_size
        if chunk_end > len(data):
            break
        chunk = data[chunk_start:chunk_end]
        if chunk_type == b"VP8X" and len(chunk) >= 10:
            flags = chunk[0]
            width = 1 + int.from_bytes(chunk[4:7], "little")
            height = 1 + int.from_bytes(chunk[7:10], "little")
            return ImageInfo("webp", width, height, bool(flags & 0x10))
        if chunk_type == b"VP8 " and len(chunk) >= 10:
            width = struct.unpack("<H", chunk[6:8])[0] & 0x3FFF
            height = struct.unpack("<H", chunk[8:10])[0] & 0x3FFF
            return ImageInfo("webp", width, height, False)
        if chunk_type == b"VP8L" and len(chunk) >= 5 and chunk[0] == 0x2F:
            bits = int.from_bytes(chunk[1:5], "little")
            width = (bits & 0x3FFF) + 1
            height = ((bits >> 14) & 0x3FFF) + 1
            has_alpha = bool((bits >> 28) & 0x01)
            return ImageInfo("webp", width, height, has_alpha)
        index = chunk_end + (chunk_size % 2)
    raise ValueError(f"Unable to inspect WebP dimensions: {path}")


def enforce_size_policy(path: Path, args: argparse.Namespace) -> None:
    expected = expected_dimensions(args)
    if args.size_policy == "ignore" or expected is None:
        return
    actual = image_dimensions(path)
    if actual is None:
        message = f"Could not determine output dimensions for {path}."
        if args.size_policy in {"error", "resize"}:
            raise RuntimeError(message)
        print(f"WARNING: {message}", file=sys.stderr)
        return
    if actual == expected:
        return
    message = f"Output size mismatch for {path}: expected {expected[0]}x{expected[1]}, got {actual[0]}x{actual[1]}."
    if args.size_policy == "warn":
        print(f"WARNING: {message}", file=sys.stderr)
        return
    if args.size_policy == "error":
        raise RuntimeError(message)
    if would_upscale(actual, expected) and not args.allow_upscale:
        raise RuntimeError(
            f"{message} Resizing would upscale the provider image. "
            "Ask the user before enlarging it, then rerun with --allow-upscale if approved."
        )
    resized_from = resize_to_expected(path, expected, args.resize_quality)
    print(f"Resized output to {expected[0]}x{expected[1]}: {path}", file=sys.stderr)
    print(f"Provider original kept at: {resized_from}", file=sys.stderr)


def would_upscale(actual: tuple[int, int], expected: tuple[int, int]) -> bool:
    return expected[0] > actual[0] or expected[1] > actual[1]


def resize_to_expected(path: Path, expected: tuple[int, int], quality: int) -> Path:
    script = Path(__file__).resolve().with_name("resize_image.py")
    if not script.is_file():
        raise RuntimeError(f"Resize helper not found: {script}")
    provider_path = unique_provider_path(path)
    path.replace(provider_path)
    command = [
        sys.executable,
        str(script),
        "--input",
        str(provider_path),
        "--output",
        str(path),
        "--width",
        str(expected[0]),
        "--height",
        str(expected[1]),
        "--quality",
        str(quality),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        if path.exists():
            path.unlink()
        provider_path.replace(path)
        stderr = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"Resize failed: {stderr}")
    return provider_path


def unique_provider_path(path: Path) -> Path:
    candidate = path.with_name(f"{path.stem}-provider{path.suffix}")
    if not candidate.exists():
        return candidate
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}-provider-{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not choose a provider-original filename for {path}")


def dry_run_payload(args: argparse.Namespace, out: Path, mode: str, endpoint: str, prompt: str) -> dict[str, Any]:
    if mode == "edit":
        fields, files = build_edit_parts(args, prompt)
        return {
            "endpoint": endpoint,
            "method": "multipart",
            "fields": fields,
            "files": [{"field": field_name, "path": str(path)} for field_name, path in files],
            "out": str(out),
        }
    return {
        "endpoint": endpoint,
        "method": "stream-json" if args.stream else "json",
        "payload": json.loads(compact_json(build_generation_payload(args, prompt)).decode("utf-8")),
        "out": str(out),
    }


def main() -> int:
    args = parse_args()
    validate_args(args)
    prompts = load_prompts(args.prompt, args.prompt_file)
    out = Path(args.out).expanduser()
    mode = determine_mode(args)
    is_edit = mode == "edit"
    endpoint = "/images/edits" if is_edit else "/images/generations"
    if args.dry_run:
        for raw_prompt in prompts:
            prompt = prompt_with_roles(raw_prompt, args.image_role)
            print(json.dumps(dry_run_payload(args, out, mode, endpoint, prompt), ensure_ascii=False, indent=2))
        return 0
    provider = resolve_provider_config(args)
    for prompt_index, raw_prompt in enumerate(prompts):
        prompt = prompt_with_roles(raw_prompt, args.image_role)
        print(f"Waiting for image {'edit' if is_edit else 'generation'} {prompt_index + 1}/{len(prompts)}...", file=sys.stderr)
        if is_edit:
            fields, files = build_edit_parts(args, prompt)
            response = request_multipart(
                f"{provider.base_url}{endpoint}",
                provider.api_key,
                fields,
                files,
                args.timeout,
                args.user_agent,
                args.max_retries,
                args.retry_delay,
            )
        else:
            payload = build_generation_payload(args, prompt)
            if args.stream:
                request_stream(f"{provider.base_url}{endpoint}", provider.api_key, payload, args.timeout, args.user_agent, out, args)
                continue
            response = request_json(
                f"{provider.base_url}{endpoint}",
                provider.api_key,
                payload,
                args.timeout,
                args.user_agent,
                args.max_retries,
                args.retry_delay,
            )
        images = extract_image_bytes(response, args)
        for path in write_outputs(images, out, args, len(prompts), prompt_index):
            print(path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
