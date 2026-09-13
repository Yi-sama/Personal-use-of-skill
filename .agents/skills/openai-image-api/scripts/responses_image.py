from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
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
DEFAULT_MODEL = "gpt-5.5"
DEFAULT_OUT = "outputs/response-image.png"
AUTH_FILE_NAME = "auth.json"
CONFIG_FILE_NAME = "config.toml"
KEY_FIELD = "OPENAI_API_KEY"
IMAGE_KEY_FIELD = "OPENAI_IMAGE_API_KEY"
BASE_URL_FIELD = "OPENAI_BASE_URL"
IMAGE_BASE_URL_FIELD = "OPENAI_IMAGE_BASE_URL"
MAX_IMAGE_BYTES = 50 * 1024 * 1024


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
    parser = argparse.ArgumentParser(description="Generate or iterate images with the Responses API image_generation tool.")
    parser.add_argument("--prompt", required=True, help="Prompt text.")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Final output image path.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Responses model that supports image_generation.")
    parser.add_argument("--codex-home", help="Override Codex root directory for auth.json/config.toml.")
    parser.add_argument("--base-url", help="Temporary provider base_url override.")
    parser.add_argument("--base-url-env", help="Environment variable containing a temporary provider base_url override.")
    parser.add_argument("--api-key-env", help="Environment variable containing a temporary API key override.")
    parser.add_argument("--api-key", help="Temporary direct API key override; prefer --api-key-env.")
    parser.add_argument("--previous-response-id", help="Continue a prior Responses API image conversation.")
    parser.add_argument(
        "--image-call-id",
        action="append",
        default=[],
        help="Prior image_generation_call id to include in input context; repeatable.",
    )
    parser.add_argument("--file-id", action="append", default=[], help="Vision file_id to include as an input_image; repeatable.")
    parser.add_argument("--image", action="append", default=[], help="Local image to upload with purpose=vision and include as input_image; repeatable.")
    parser.add_argument("--mask-file-id", help="Vision file_id to use as the image_generation tool input_image_mask.")
    parser.add_argument("--mask", help="Local mask image to upload with purpose=vision and use as input_image_mask.")
    parser.add_argument("--action", choices=["auto", "generate", "edit"], default="auto")
    parser.add_argument("--size", help="Image output size, such as auto, 1024x1024, 2048x1152, or 3840x2160.")
    parser.add_argument("--quality", choices=["low", "medium", "high", "auto"], help="Image rendering quality.")
    parser.add_argument("--background", choices=["auto", "opaque", "transparent"], help="Image background behavior.")
    parser.add_argument("--output-format", choices=["png", "jpeg", "webp"], help="Requested output format.")
    parser.add_argument("--output-compression", type=int, help="0-100 for jpeg/webp.")
    parser.add_argument("--stream", action="store_true", help="Stream partial images and final response.")
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


def validate_args(args: argparse.Namespace) -> None:
    if args.api_key and args.api_key_env:
        raise ValueError("Use only one of --api-key or --api-key-env.")
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
    if not 1 <= args.resize_quality <= 100:
        raise ValueError("--resize-quality must be between 1 and 100.")
    if args.mask and args.mask_file_id:
        raise ValueError("Use only one of --mask or --mask-file-id.")
    if args.size:
        validate_size(args.size)
    if args.expected_size:
        parse_plain_size(args.expected_size, "--expected-size")
    if args.output_compression is not None and not 0 <= args.output_compression <= 100:
        raise ValueError("--output-compression must be between 0 and 100.")
    if args.output_compression is not None and args.output_format not in {"jpeg", "webp"}:
        raise ValueError("--output-compression only applies to jpeg or webp output.")
    if args.action == "edit" and not (args.previous_response_id or args.image_call_id or args.file_id or args.image):
        raise ValueError("--action edit requires --previous-response-id, --image-call-id, --file-id, or --image context.")
    for path in [*args.image, args.mask]:
        if path:
            validate_file(path)
    if args.mask and args.image:
        validate_local_mask(args.image[0], args.mask)


def validate_file(path: str) -> None:
    file_path = Path(path).expanduser()
    if not file_path.is_file():
        raise ValueError(f"File not found: {path}")
    if file_path.stat().st_size >= MAX_IMAGE_BYTES:
        raise ValueError(f"File must be under 50MB: {path}")


def validate_local_mask(source_path: str, mask_path: str) -> None:
    # 复用 Image API 脚本里的轻量图片探测，避免在 Responses 脚本里复制 PNG/JPEG/WebP 解析器。
    from image_api import inspect_image

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


def parse_plain_size(size: str, option_name: str) -> tuple[int, int]:
    import re

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


def request_timeout(timeout: int) -> int | None:
    return None if timeout == 0 else timeout


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


def clean_base_url(base_url: str) -> str:
    base_url = base_url.strip().rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        raise ValueError("base URL must start with http:// or https://")
    return base_url


def build_payload(args: argparse.Namespace, file_ids: list[str], mask_file_id: str | None) -> dict[str, Any]:
    tool: dict[str, Any] = {"type": "image_generation"}
    if args.action != "auto":
        tool["action"] = args.action
    optional_tool_fields = {
        "size": args.size,
        "quality": args.quality,
        "background": args.background,
        "output_format": args.output_format,
        "output_compression": args.output_compression,
    }
    tool.update({key: value for key, value in optional_tool_fields.items() if value is not None})
    if args.stream and args.partial_images:
        tool["partial_images"] = args.partial_images
    if mask_file_id:
        tool["input_image_mask"] = {"file_id": mask_file_id}

    payload: dict[str, Any] = {
        "model": args.model,
        "input": build_input(args.prompt, args.image_call_id, file_ids),
        "tools": [tool],
    }
    if args.previous_response_id:
        payload["previous_response_id"] = args.previous_response_id
    if args.stream:
        payload["stream"] = True
    return payload


def build_input(prompt: str, image_call_ids: list[str], file_ids: list[str]) -> str | list[dict[str, Any]]:
    if not image_call_ids and not file_ids:
        return prompt
    input_items: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                *({"type": "input_image", "file_id": file_id} for file_id in file_ids),
            ],
        }
    ]
    input_items.extend({"type": "image_generation_call", "id": image_call_id} for image_call_id in image_call_ids)
    return input_items


def create_request(url: str, api_key: str, payload: dict[str, Any], user_agent: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": user_agent,
        },
    )


def post_json(
    url: str,
    api_key: str,
    payload: dict[str, Any],
    timeout: int,
    user_agent: str,
    max_retries: int,
    retry_delay: float,
) -> dict[str, Any]:
    def send_once() -> dict[str, Any]:
        request = create_request(url, api_key, payload, user_agent)
        try:
            with urllib.request.urlopen(request, timeout=request_timeout(timeout)) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise_runtime_http_error(exc)
        except urllib.error.URLError as exc:
            raise RequestError(f"Failed to connect to provider: {exc.reason}") from exc
        except TimeoutError as exc:
            raise RequestError("Provider request timed out.") from exc

    return with_retries(send_once, max_retries, retry_delay, "Responses API request")


def upload_vision_file(
    url: str,
    api_key: str,
    path: Path,
    timeout: int,
    user_agent: str,
    max_retries: int,
    retry_delay: float,
) -> str:
    def send_once() -> str:
        response = post_multipart(
            url,
            api_key,
            {"purpose": "vision"},
            [("file", path)],
            timeout,
            user_agent,
        )
        file_id = response.get("id")
        if not isinstance(file_id, str) or not file_id:
            raise RuntimeError(f"Files API response did not include id for {path}.")
        return file_id

    return with_retries(send_once, max_retries, retry_delay, f"Files API upload for {path.name}")


def post_multipart(
    url: str,
    api_key: str,
    fields: dict[str, str],
    files: list[tuple[str, Path]],
    timeout: int,
    user_agent: str,
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
    request = urllib.request.Request(
        url,
        data=b"".join(chunks),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": user_agent,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=request_timeout(timeout)) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise_runtime_http_error(exc)
    except urllib.error.URLError as exc:
        raise RequestError(f"Failed to connect to provider: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RequestError("Provider request timed out.") from exc


def stream_response(
    url: str,
    api_key: str,
    payload: dict[str, Any],
    timeout: int,
    user_agent: str,
    out: Path,
    max_retries: int,
    retry_delay: float,
) -> dict[str, Any] | None:
    def send_once() -> dict[str, Any] | None:
        request = create_request(url, api_key, payload, user_agent)
        completed_response: dict[str, Any] | None = None
        try:
            with urllib.request.urlopen(request, timeout=request_timeout(timeout)) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    event = json.loads(data)
                    event_type = event.get("type")
                    if event_type == "response.image_generation_call.partial_image":
                        save_partial_image(event, out)
                    elif event_type == "response.completed":
                        completed_response = event.get("response")
                    elif event_type in {"response.failed", "response.incomplete", "error"}:
                        raise RuntimeError(json.dumps(event, ensure_ascii=False))
        except urllib.error.HTTPError as exc:
            raise_runtime_http_error(exc)
        except urllib.error.URLError as exc:
            raise RequestError(f"Failed to connect to provider: {exc.reason}") from exc
        except TimeoutError as exc:
            raise RequestError("Provider request timed out.") from exc
        return completed_response

    return with_retries(send_once, max_retries, retry_delay, "Responses API stream request")


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


def save_partial_image(event: dict[str, Any], out: Path) -> None:
    b64 = event.get("partial_image_b64")
    if not isinstance(b64, str) or not b64:
        return
    index = event.get("partial_image_index")
    suffix = out.suffix or ".png"
    partial_path = out.with_name(f"{out.stem}-partial-{index}{suffix}")
    partial_path.parent.mkdir(parents=True, exist_ok=True)
    partial_path.write_bytes(base64.b64decode(b64))
    print(partial_path)


def extract_image_generation_outputs(response: dict[str, Any]) -> list[tuple[str | None, bytes]]:
    output = response.get("output")
    if not isinstance(output, list):
        raise RuntimeError("Responses API response did not include output[].")
    images: list[tuple[str | None, bytes]] = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "image_generation_call":
            continue
        result = item.get("result")
        if isinstance(result, str) and result:
            images.append((item.get("id") if isinstance(item.get("id"), str) else None, base64.b64decode(result)))
    if not images:
        raise RuntimeError("Responses API response did not include image_generation_call result data.")
    return images


def output_paths(base: Path, count: int) -> list[Path]:
    suffix = base.suffix or ".png"
    stem = base.stem if base.suffix else base.name
    if count == 1:
        return [base.with_suffix(suffix)]
    return [base.with_name(f"{stem}-{index + 1}{suffix}") for index in range(count)]


def enforce_response_size_policy(path: Path, args: argparse.Namespace) -> None:
    # 复用 Image API 脚本的尺寸探测和 resize 策略，保持两条 CLI 路径行为一致。
    if not args.expected_size and not args.size:
        return
    from image_api import enforce_size_policy

    enforce_size_policy(path, args)


def write_images(images: list[tuple[str | None, bytes]], out: Path, args: argparse.Namespace) -> list[Path]:
    paths = output_paths(out, len(images))
    for (image_call_id, image), path in zip(images, paths, strict=True):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image)
        enforce_response_size_policy(path, args)
        if image_call_id:
            print(f"image_generation_call_id={image_call_id}", file=sys.stderr)
        print(path)
    return paths


def print_response_metadata(response: dict[str, Any]) -> None:
    response_id = response.get("id")
    if isinstance(response_id, str) and response_id:
        print(f"response_id={response_id}", file=sys.stderr)


def uploaded_file_ids(args: argparse.Namespace, provider: ProviderConfig) -> tuple[list[str], str | None]:
    upload_url = f"{provider.base_url}/files"
    file_ids = list(args.file_id)
    for image in args.image:
        path = Path(image).expanduser()
        file_id = upload_vision_file(
            upload_url,
            provider.api_key,
            path,
            args.timeout,
            args.user_agent,
            args.max_retries,
            args.retry_delay,
        )
        print(f"uploaded_file_id={file_id} path={path}", file=sys.stderr)
        file_ids.append(file_id)
    mask_file_id = args.mask_file_id
    if args.mask:
        path = Path(args.mask).expanduser()
        mask_file_id = upload_vision_file(
            upload_url,
            provider.api_key,
            path,
            args.timeout,
            args.user_agent,
            args.max_retries,
            args.retry_delay,
        )
        print(f"uploaded_mask_file_id={mask_file_id} path={path}", file=sys.stderr)
    return file_ids, mask_file_id


def dry_run_payload(args: argparse.Namespace, out: Path) -> dict[str, Any]:
    placeholder_file_ids = [
        *args.file_id,
        *(f"<uploaded:{Path(image).expanduser()}>" for image in args.image),
    ]
    placeholder_mask_file_id = args.mask_file_id
    if args.mask:
        placeholder_mask_file_id = f"<uploaded:{Path(args.mask).expanduser()}>"
    return {
        "endpoint": "/responses",
        "uploads": [{"path": str(Path(image).expanduser()), "purpose": "vision"} for image in args.image]
        + ([{"path": str(Path(args.mask).expanduser()), "purpose": "vision", "role": "mask"}] if args.mask else []),
        "payload": build_payload(args, placeholder_file_ids, placeholder_mask_file_id),
        "out": str(out),
    }


def main() -> int:
    args = parse_args()
    validate_args(args)
    out = Path(args.out).expanduser()
    if args.dry_run:
        print(json.dumps(dry_run_payload(args, out), ensure_ascii=False, indent=2))
        return 0
    provider = resolve_provider_config(args)
    file_ids, mask_file_id = uploaded_file_ids(args, provider)
    payload = build_payload(args, file_ids, mask_file_id)
    url = f"{provider.base_url}/responses"
    if args.stream:
        response = stream_response(
            url,
            provider.api_key,
            payload,
            args.timeout,
            args.user_agent,
            out,
            args.max_retries,
            args.retry_delay,
        )
        if response is None:
            raise RuntimeError("Stream ended without response.completed.")
    else:
        response = post_json(
            url,
            provider.api_key,
            payload,
            args.timeout,
            args.user_agent,
            args.max_retries,
            args.retry_delay,
        )
    print_response_metadata(response)
    write_images(extract_image_generation_outputs(response), out, args)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
