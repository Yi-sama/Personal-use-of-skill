---
name: openai-image-api
description: Default raster image skill for Codex image generation and editing through the official OpenAI Image API or an OpenAI-compatible /v1 relay provider. Use this instead of the system imagegen built-in path when images must route through configured API credentials, BYOK providers, base_url overrides, Codex config.toml/auth.json provider resolution, gpt-image-2, /v1/images/generations, /v1/images/edits, Responses API image_generation, local file-path image inputs, reference images, masks, transparent-background workflows, streaming, custom size/quality/output-format controls, or strict output-dimension validation.
---

# OpenAI Image API

Use this skill as the default API/BYOK raster image workflow. It replaces the system `imagegen` built-in path in environments where image requests must use configured OpenAI-compatible `/v1` relay providers, and it also replaces the older provider-specific `api-image` flow and the minimal `imagegen-byok` fork.

Use this skill for ordinary image generation and editing requests unless the user explicitly asks for the system `imagegen` built-in tool or the task is better handled as repo-native SVG/vector/code/HTML/CSS/canvas output. Do not route a normal image task away from this skill merely because the user did not mention API, BYOK, provider routing, masks, streaming, or file paths.

Primary scripts:

- `scripts/image_api.py`: Image API generation, reference-image generation, edits, masks, partial streaming, provider overrides, Codex root provider resolution, and output size policy. Default output: `outputs/image.png`.
- `scripts/responses_image.py`: Responses API `image_generation` one-shot, multi-turn continuation, file_id inputs, local image upload, masks, partial streaming, and output size policy. Default output: `outputs/response-image.png`.
- `scripts/remove_chroma_key.py`: local transparent-background post-processing for flat chroma-key images.
- `scripts/resize_image.py`: exact resize helper used by `--size-policy resize`.

Prompt guidance:

- `references/prompting.md`: concise prompting rules, taxonomy, text, edits, references, and transparency.
- `references/sample-prompts.md`: copy/paste prompt recipes.
- `references/official-image-api.md`: official Image API parameter notes.

## Routing Rules

- Use this as the primary image-generation/editing path for raster outputs, including posters, social screenshots, phone screenshots, UI mockup images, thumbnails, product mockups, reference-driven images, and text-bearing images.
- Use repo-native SVG/vector/code/HTML/CSS/canvas instead only when the user asks for deterministic editable UI, pixel-perfect typography, exact reusable layout code, an existing vector/icon system, or a non-raster artifact.
- Chinese text, large text blocks, or "text and image integrated" requirements are not reasons to switch to local HTML/CSS overlays by default. Generate the complete raster image through the API path, validate the text, and retry with tighter constraints when needed.
- Mention local/programmatic text overlay only when the user explicitly asks for editable typography, pixel-perfect copy, exact font/brand control, separately composited text, or accepts that tradeoff after direct generation fails text validation.

## Workflow

1. Decide whether research or visual references are needed.
   - Research or use references for named places, named structures, products, people, historical scenes, technical diagrams, branded objects, current facts, and niche visual styles.
   - Prefer reference images when shape, terrain, product details, architecture, identity, or composition must be accurate.
   - If references are unavailable, say accuracy is limited instead of pretending.
2. Choose the execution path.
   - No input image: start with `scripts/image_api.py` and `/images/generations` when the provider exposes the requested GPT Image model.
   - Any `--image`, reference image, or `--mask`: `scripts/image_api.py` uses `/images/edits`.
   - Multi-turn image iteration or File ID image inputs: use `scripts/responses_image.py`.
   - Image API partial images: use `scripts/image_api.py --stream --partial-images 1..3`.
   - Responses API partial images: use `scripts/responses_image.py --stream --partial-images 1..3`.
   - If Image API returns `model_not_found` or reports no available channel for the requested image model, do not retry the same request unchanged. Check the provider's `/models` response. If it exposes a mainline model that supports the Responses `image_generation` tool, switch to `scripts/responses_image.py --model <supported-model> --stream`; otherwise report that the provider has no usable image channel.
   - Prefer Responses streaming for relays that buffer or time out non-streaming image responses. Treat saved partial images as progress artifacts and use the final response image as the deliverable.
3. Resolve provider credentials.
   - Default order for API key: explicit `--api-key` or `--api-key-env`; environment variables `OPENAI_IMAGE_API_KEY` then `OPENAI_API_KEY`; `$CODEX_HOME/auth.json` or `~/.codex/auth.json` fields `OPENAI_IMAGE_API_KEY` then `OPENAI_API_KEY`; finally the active local provider's `env_key` from its environment variable or matching `auth.json` field.
   - Default order for base URL: `--base-url`, `--base-url-env`, `OPENAI_IMAGE_BASE_URL`, `OPENAI_BASE_URL`, active provider in `$CODEX_HOME/config.toml` or `~/.codex/config.toml`, then `https://api.openai.com/v1`.
   - An active provider with `requires_openai_auth = true` uses the OpenAI key found in the environment or `auth.json` while retaining that provider's configured `base_url`.
   - Use `--codex-home` when the user points to a non-default Codex root.
   - Never print, persist, or write API keys into repo files. Prefer `--api-key-env` over `--api-key`.
4. Build a concrete prompt.
   - Include the user request, researched facts or visual observations, input image roles, style, composition, lighting, materials, exact text, constraints, and avoid list.
   - If the user asks for visible in-image text, typography, poster copy, invitation copy, labels, titles, Chinese layout, or complete text layout:
     - Treat the image as text-bearing.
     - Do not add `no text`, `leave room for UI/copy`, or text-free background constraints unless the user explicitly asks for a blank background.
     - Add a dedicated `Text (verbatim): ...` block with every required string.
     - State that the text must be rendered directly inside the image, exactly once, with no omitted, invented, or extra text.
     - Use `--quality high` for final text-bearing assets.
   - For platform screenshot style, social media screenshot, phone screenshot mockup, or UI mockup image requests:
     - If the user wants a generated raster mockup, generate the whole text-and-image asset through this skill.
     - If the user wants deterministic UI reconstruction, exact fonts, exact spacing, or reusable/editable UI code, use repo-native HTML/CSS/canvas instead.
   - Default to direct in-image rendering for text-bearing requests, including Chinese poster/layout requests. Do not switch to a text-free background plus local overlay solely for text clarity.
   - Mention a text-free image plus local/programmatic overlay only when the user explicitly asks for editable production typography, pixel-perfect copy, exact font/brand control, or separately composited text, or when direct generation fails text validation and the user accepts that tradeoff.
   - Do not invent extra characters, props, brands, logos, slogans, or factual details not implied by the request or references.
5. Run the script and save under `outputs/` unless the user requests another path.
6. Inspect the output before final response.
   - Verify subject, dimensions, text accuracy, no unwanted logos/watermarks, and mask/reference invariants.
   - For text-bearing outputs, compare every required string against the `Text (verbatim)` block. If required text is missing, duplicated, invented, or visibly garbled, make one targeted retry with stricter text constraints before offering local/programmatic overlay as an explicit tradeoff.
   - Report actual dimensions when the provider ignores requested size.
   - A successful Responses image call does not prove the requested dimensions were honored. Keep `--size-policy warn` or `error` enabled and report the saved image's actual dimensions.

## Commands

Text-free visual asset with native-size validation:

```powershell
$prompt = @'
Asset type: website hero background
Primary request: photorealistic dawn view of a quiet urban river with modern bridges
Style/medium: polished editorial photography
Composition/framing: wide landscape, clean negative space in the upper third
Lighting/mood: early morning light, natural color, light haze
Constraints: no text; no logos; no watermark; no people in the foreground
'@

python "<skill-dir>\scripts\image_api.py" `
  --prompt $prompt `
  --size "2048x1152" `
  --quality "medium" `
  --size-policy "error" `
  --out ".\outputs\river-hero.png"
```

Text-bearing Chinese event poster:

```powershell
$prompt = @'
Asset type: text-bearing community event poster
Primary request: 社区读书会活动海报，温和、清爽、适合公共公告栏
Scene/backdrop: quiet library corner, wooden table, open books, soft afternoon light
Style/medium: clean modern poster design, crisp Chinese typography, balanced spacing
Composition/framing: vertical poster; large centered title; event details below; host line at the bottom
Text (verbatim):
- "社区读书会"
- "周六下午 3:00"
- "城市图书馆二楼"
- "一起阅读，一起交流"
- "社区文化中心"
Constraints: render the listed Chinese text directly inside the image; preserve every character; each listed string appears exactly once; no omitted text; no invented text; no extra captions; no garbled characters; no watermark
'@

python "<skill-dir>\scripts\image_api.py" `
  --prompt $prompt `
  --size "1024x1536" `
  --quality "high" `
  --size-policy "warn" `
  --out ".\outputs\community-reading-poster.png"
```

Use image-specific BYOK provider settings:

```powershell
$env:OPENAI_IMAGE_BASE_URL = "https://provider.example/v1"
$env:OPENAI_IMAGE_API_KEY = "..."

python "<skill-dir>\scripts\image_api.py" `
  --prompt "Premium product photo of a matte black bottle on a clean studio surface; no logos; no watermark" `
  --size "1024x1024" `
  --quality "medium" `
  --timeout 0 `
  --size-policy "warn" `
  --out ".\outputs\product.png"
```

Generate with references that are not edit targets:

```powershell
$prompt = @'
Primary request: generate a new realistic aerial promotional image inspired by the references
Input images:
- Image 1: building shape reference
- Image 2: surrounding terrain and lighting reference
Style/medium: realistic aerial photography
Constraints: do not copy either source image exactly; preserve the building's recognizable shape language; no text; no logos; no watermark
'@

python "<skill-dir>\scripts\image_api.py" `
  --prompt $prompt `
  --image ".\inputs\building-reference.jpg" `
  --image-role "building shape reference" `
  --image ".\inputs\terrain-reference.jpg" `
  --image-role "terrain and lighting reference" `
  --size "2048x1152" `
  --quality "high" `
  --out ".\outputs\aerial-reference.png"
```

Localized edit with a mask:

```powershell
python "<skill-dir>\scripts\image_api.py" `
  --prompt "Change only the masked area into one red paper lantern; keep the room layout, lighting, shadows, walls, and all unmasked pixels unchanged" `
  --image ".\inputs\room.png" `
  --mask ".\inputs\lantern-mask.png" `
  --quality "high" `
  --out ".\outputs\room-lantern.png"
```

Transparent cutout using chroma-key removal:

```powershell
$prompt = @'
Primary request: clean product cutout of one ceramic coffee mug
Scene/backdrop: perfectly flat solid #00ff00 chroma-key background for local background removal
Style/medium: realistic product photography
Composition/framing: centered object with generous padding
Constraints: background must be one uniform color with no shadows, gradients, texture, reflections, floor plane, or lighting variation; crisp silhouette; no halos; do not use #00ff00 anywhere in the mug; no text; no watermark
'@

python "<skill-dir>\scripts\image_api.py" `
  --prompt $prompt `
  --size "1024x1024" `
  --quality "high" `
  --out ".\outputs\mug-key.png"

python "<skill-dir>\scripts\remove_chroma_key.py" `
  --input ".\outputs\mug-key.png" `
  --out ".\outputs\mug-transparent.png" `
  --auto-key border `
  --soft-matte `
  --transparent-threshold 12 `
  --opaque-threshold 220 `
  --despill
```

Batch from a prompt file:

```powershell
python "<skill-dir>\scripts\image_api.py" `
  --prompt-file ".\inputs\asset-prompts.txt" `
  --size "1024x1024" `
  --quality "low" `
  --out ".\outputs\asset.png"
```

Stream Image API partial previews:

```powershell
python "<skill-dir>\scripts\image_api.py" `
  --prompt "Cinematic sunset river scene for a title-free background; no text; no logos; no watermark" `
  --size "2048x1152" `
  --quality "medium" `
  --stream `
  --partial-images 2 `
  --out ".\outputs\river-stream.png"
```

Responses API with a local image input:

```powershell
python "<skill-dir>\scripts\responses_image.py" `
  --prompt "Edit this room image so the pool contains one inflatable flamingo; keep the room layout, camera angle, lighting, and all other furniture unchanged" `
  --image ".\inputs\sunlit_lounge.png" `
  --action edit `
  --size "1024x1024" `
  --quality "high" `
  --out ".\outputs\lounge-edit.png"
```

Continue a prior Responses image turn:

```powershell
python "<skill-dir>\scripts\responses_image.py" `
  --prompt "Keep the same composition, but change the image style to a restrained Song dynasty ink painting; no text; no watermark" `
  --previous-response-id "<response-id>" `
  --quality "high" `
  --out ".\outputs\river-response-followup.png"
```

## Common Options

- `--model gpt-image-2`
- `--mode auto|generate|edit`
- `--size auto|1024x1024|1536x1024|1024x1536|2048x2048|2048x1152|3840x2160|2160x3840`
- `--quality low|medium|high|auto`
- `--n 1`
- `--prompt-file <path>` for one prompt per non-empty line
- `--image <path>` repeated up to 16 images
- `--image-role <role>` repeated to label input images inside the prompt
- `--mask <path>` for localized edits
- `--background auto|opaque`; do not use `transparent` with `gpt-image-2`
- `--output-format png|jpeg|webp`
- `--output-compression 0-100` for jpeg/webp
- `--input-fidelity low|high` only for models that support it; do not send it for `gpt-image-2`
- `--moderation auto|low`
- `--codex-home <path>`
- `--base-url <https://provider.example/v1>`
- `--base-url-env <ENV_NAME>`
- `--api-key-env <ENV_NAME>`
- `--api-key <key>` only for explicit one-off user-provided keys
- `--timeout 1800`; use `--timeout 0` for long provider jobs
- `--max-retries 2` and `--retry-delay 1.0` retry transient `429`, `5xx`, and network failures
- Stable request/configuration failures such as `invalid_api_key`, `insufficient_quota`, `model_not_found`, `image_generation_user_error`, and `moderation_blocked` are not retried unchanged
- `--expected-size <WIDTHxHEIGHT>` to validate a provider return size independent of `--size`
- `--size-policy ignore|warn|error|resize`; use `warn` or `error` before claiming native 2K/4K
- `--allow-upscale` only after explicit user approval or when the user already requested upscaling
- `--resize-quality 1..100`
- `--dry-run` prints the request shape without sending it or resolving API keys
- `--user-agent <value>` for compatible providers that require specific request headers

Responses API options:

- `--model gpt-5.5` or another model that supports the `image_generation` tool
- `--previous-response-id <id>` to continue a prior Responses turn
- `--image-call-id <id>` to include a previous `image_generation_call` in context
- `--file-id <file_id>` to include an existing vision file as `input_image`
- `--image <path>` to upload a local image with `purpose=vision` and include it as `input_image`
- `--mask-file-id <file_id>` or `--mask <path>` to set the tool `input_image_mask`
- `--action auto|generate|edit`
- `--size auto|1024x1024|1536x1024|1024x1536|2048x2048|2048x1152|3840x2160|2160x3840`
- `--quality low|medium|high|auto`
- `--background auto|opaque|transparent`; do not use true transparent background without explicit user confirmation
- `--output-format png|jpeg|webp`
- `--output-compression 0-100` for jpeg/webp
- `--stream --partial-images 1..3`; omit `--partial-images` to stream without requesting partial image previews
- `--expected-size <WIDTHxHEIGHT>` to validate a provider return size independent of `--size`
- `--size-policy ignore|warn|error|resize`; use `warn` or `error` before claiming native 2K/4K
- `--allow-upscale` only after explicit user approval or when the user already requested upscaling
- `--resize-quality 1..100`

## Model Choice

- Use `gpt-image-2` by default for Image API generation and edits.
- Use `gpt-image-1.5` only when the user explicitly wants true model-native transparent output or has already chosen that model path.
- Use `gpt-image-1` or `gpt-image-1-mini` only when the user/provider explicitly requires them.
- For Responses API, choose a mainline model that supports the `image_generation` tool; the image tool handles GPT Image model selection.
- When the provider does not expose a GPT Image model but does expose a compatible mainline model, use that model through `responses_image.py --stream` instead of repeatedly calling `/images/generations`.
- Do not silently downgrade models. If provider support requires a different image model name, override `--model` and say why.

## Size Policy

Use `--size-policy warn` or `--size-policy error` before claiming an image is native 2K/4K. This applies to both `scripts/image_api.py` and `scripts/responses_image.py`; Responses output is checked only when `--size` or `--expected-size` is provided.

- `ignore`: do nothing.
- `warn`: report mismatches. This is the default.
- `error`: fail when returned dimensions do not match expected size.
- `resize`: normalize to expected dimensions and keep the provider original as `*-provider.ext`.

Do not silently upscale a smaller provider image and present it as native 2K/4K. Use `--allow-upscale` only after explicit user approval or when the user already requested upscaling.

## Transparent Images

For `gpt-image-2`, use chroma-key generation plus local removal:

1. Prompt for a perfectly flat solid key background, usually `#00ff00`; use `#ff00ff` for green subjects.
2. Prohibit shadows, gradients, texture, reflections, floor planes, and key color inside the subject.
3. Generate the source image with `scripts/image_api.py`.
4. Run:
   ```powershell
   python "<skill-dir>\scripts\remove_chroma_key.py" `
     --input ".\outputs\source-key.png" `
     --out ".\outputs\source-transparent.png" `
     --auto-key border `
     --soft-matte `
     --transparent-threshold 12 `
     --opaque-threshold 220 `
     --despill
   ```
5. Validate alpha, transparent corners, subject coverage, and edge fringe.

Ask before switching to `gpt-image-1.5 --background transparent --output-format png` unless the user already explicitly requested that true transparency model path. Provider support varies.

## Rules

- Use `gpt-image-2` by default unless the provider or user explicitly requires another model.
- Start with `n=1`; create variants only when requested.
- Any input image, reference image, or mask means edit endpoint.
- Do not send `background=transparent` with `gpt-image-2`.
- Do not send `input_fidelity` with `gpt-image-2`.
- For masks, the script validates first image/mask format, dimensions, file size, and alpha channel.
- For streaming partial images, use `--stream --partial-images 1..3`; `--stream` without `--partial-images` omits the `partial_images` field and only requests streaming behavior. Streamed partials are saved as `*-partial-<index>.ext`.
- For Responses API image generation, choose a model that supports `image_generation`; if forcing `--action edit`, provide `--previous-response-id` or `--image-call-id`.
- Surface provider errors directly. Do not fabricate a success result.
- If the provider uses a different image model name, override `--model`.
- This skill does not implement the DALL-E 2 variations endpoint; it focuses on GPT Image generations/edits and Responses API image generation.
- Partial images are progress outputs and can add cost; use them when interactive progress is worth it.

## Resources

- `scripts/image_api.py`: main Image API CLI.
- `scripts/responses_image.py`: Responses API image_generation CLI.
- `scripts/remove_chroma_key.py`: local chroma-key to alpha helper.
- `scripts/resize_image.py`: cross-platform resize wrapper.
- `scripts/resize_image.ps1`: Windows resize fallback.
- `references/prompting.md`: prompt rules and taxonomy.
- `references/sample-prompts.md`: copy/paste recipes.
- `references/official-image-api.md`: official API facts.
