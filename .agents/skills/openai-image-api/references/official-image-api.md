# Official Image API Notes

Source: https://developers.openai.com/api/docs/guides/image-generation

## API Choice

- Image API is best for one prompt that generates or edits one set of images.
- Responses API with the `image_generation` tool is best for conversational or multi-turn image workflows.
- Responses API can accept image inputs from File IDs, not only bytes or prior image calls.
- Both Image API and Responses API can stream partial images; use streaming when interactive progress matters.
- Image API endpoints:
  - `POST /v1/images/generations` for text-to-image.
  - `POST /v1/images/edits` for modifying or referencing input images.
- In this skill, `scripts/image_api.py` covers Image API generation, edits, masks, references, and Image API streaming; `scripts/responses_image.py` covers Responses API image generation, multi-turn iteration, File ID inputs, local vision uploads, and Responses masks.
- The Image API also has a variations endpoint for models that support it, such as DALL-E 2. This skill focuses on GPT Image generations/edits and does not implement variations.

## Model And Output

- Default Image API model: `gpt-image-2`.
- Other GPT Image models include `gpt-image-1.5`, `gpt-image-1`, and `gpt-image-1-mini`; choose them only when the user/provider explicitly requires that model path.
- Use `gpt-image-1.5` for true model-native transparent output only after explicit confirmation or user request.
- Responses API uses a mainline model such as `gpt-5.5` that supports the `image_generation` tool; the tool handles GPT Image model selection.
- Organization verification may be required before using GPT Image models.
- The Image API returns base64 image data in `data[].b64_json`.
- Save output by base64-decoding `data[0].b64_json`.
- `n` controls how many images are returned; default to one unless variants are requested.
- Streaming can emit partial images through `partial_images` values from 1 to 3. In the local CLI, the default `0` means omit that request field.

## Edits And Reference Images

- Use `/images/edits` when sending any input image, reference image, or mask.
- Send images as multipart `image[]=@file`.
- For reference-only generation, label the role in the prompt because image roles are not a separate API field.
- Use a mask only for localized edits. The first image is the edit target; extra images are references.
- With Responses API, upload local image inputs through the Files API with `purpose="vision"`, then include them in input content as `{"type": "input_image", "file_id": "<file_id>"}`.
- With Responses API masks, provide `input_image_mask: {"file_id": "<mask_file_id>"}` on the `image_generation` tool.

## Mask Requirements

- The image to edit and mask must have the same format and size.
- Each file must be below the API file-size limit.
- The mask must include an alpha channel.
- If starting from a black-and-white mask, convert it to RGBA and put the grayscale mask into alpha.

## Size And Quality

`gpt-image-2` accepts `auto` or custom sizes that satisfy all constraints:

- Both edges are multiples of 16.
- Maximum edge length is 3840 px.
- Long edge / short edge ratio is at most 3:1.
- Total pixels are at least 655,360 and no more than 8,294,400.

Common sizes:

- `1024x1024`
- `1536x1024`
- `1024x1536`
- `2048x2048`
- `2048x1152`
- `3840x2160`
- `2160x3840`
- `auto`

Quality values:

- `low`
- `medium`
- `high`
- `auto`

Use `low` for drafts and `high` for final assets.

Outputs larger than `2560x1440` total-pixel class are described as experimental in the official guide.

Compatible providers may accept the same parameters but still return a smaller image; verify the saved file dimensions before reporting a final 2K or 4K asset. If the provider returns a smaller image, do not silently upscale it. Report the actual dimensions and get explicit approval before post-processing it larger.

## Output Customization

- `output_format` can request `png`, `jpeg`, or `webp`.
- `output_compression` is only useful for `jpeg` and `webp`.
- `background` can be `auto` or `opaque` for `gpt-image-2`.
- `gpt-image-2` does not support `background: "transparent"`.
- Omit `input_fidelity` for `gpt-image-2`; the model always processes image inputs at high fidelity.

## Cost And Latency

- Complex prompts can take up to about two minutes.
- Larger sizes, higher quality values, and more input images can increase latency and cost.
- `gpt-image-2` cost is based on input text tokens, input image tokens when editing or using references, and image output tokens.
- Responses API image generation also includes mainline model token usage in addition to image generation costs.
- Each streamed partial image can add cost; request partial images only when interactive progress is useful.
- For edit requests, `gpt-image-2` always processes input images at high fidelity, so reference-heavy edits can use more input image tokens.

## Limitations And Error Handling

- Complex prompts can take up to about two minutes.
- Text rendering can still be imperfect; avoid relying on exact text inside generated images unless necessary.
- Layout-sensitive compositions can drift; verify generated results visually.
- Retry transient `429` and `5xx` errors, not user-correctable request errors.
- Retry network timeouts and connection failures when they are likely transient.
- Do not retry `image_generation_user_error` unchanged; revise the prompt, image inputs, mask, or request parameters.
- If `error.code` is `moderation_blocked`, revise the prompt or input images instead of retrying unchanged.
- Log or surface request IDs for provider support, but never print API keys.
