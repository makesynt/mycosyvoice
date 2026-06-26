---
name: cosyvoice-fastapi
description: >-
  Call CosyVoice text-to-speech via the FastAPI HTTP server (runtime/python/fastapi).
  Use when synthesizing speech, calling /inference_* endpoints, or integrating TTS into
  agent workflows. Ask the user for server host/IP and port before calling the API.
---

# CosyVoice FastAPI

CosyVoice exposes TTS over standard HTTP. Prefer **POST** with form fields; endpoints also accept GET.

## Server address (do not hardcode)

**Before calling the API, obtain the server host from the user** if they have not already provided it.

Ask: 「CosyVoice FastAPI 服务地址是什么？（IP 或域名，例如 192.168.1.100）」

Also confirm port if unclear; default port is `56786`.

Resolution order:

1. User-provided host/port in the current task
2. Environment variables `COSYVOICE_HOST` / `COSYVOICE_PORT`
3. Ask the user — **do not assume** a fixed IP

Build base URL as: `http://{host}:{port}`

| Setting | Default | Notes |
|---------|---------|-------|
| Host | *(ask user)* | IP or hostname of the machine running `server.py` |
| Port | `56786` | Override if user says otherwise |
| OpenAPI | `http://{host}:{port}/docs` | Health check |
| Response audio | int16 PCM stream | Not WAV |
| Output sample rate | `22050` Hz | CosyVoice1/2; model config may differ for CosyVoice3 |
| Prompt audio | `16000` Hz min | Server resamples if higher |

## Agent workflow

```
- [ ] Ask user for server host (and port if not 56786)
- [ ] Verify server: GET http://{host}:{port}/docs → 200
- [ ] Pick inference mode from user intent
- [ ] POST with form fields (+ multipart file if needed)
- [ ] Stream response to .pcm or convert to .wav
- [ ] Verify output file size > 0
```

## Choose inference mode

```
Need preset speaker only?          → /inference_sft
Clone voice from prompt audio?     → /inference_zero_shot
Cross-lingual with prompt audio?   → /inference_cross_lingual
Style instruct + preset speaker?   → /inference_instruct
Style instruct + prompt audio?     → /inference_instruct2  (CosyVoice2+)
```

CosyVoice-300M cross-lingual: prefix target language, e.g. `<|zh|>` for Chinese, `<|en|>` for English.

## Endpoints

All return `StreamingResponse` of int16 PCM bytes. Collect full body before playback.

### POST /inference_sft

| Field | Type | Required | Example |
|-------|------|----------|---------|
| `tts_text` | form | yes | `你好，世界` |
| `spk_id` | form | yes | `中文女` |

### POST /inference_zero_shot

| Field | Type | Required |
|-------|------|----------|
| `tts_text` | form | yes |
| `prompt_text` | form | yes |
| `prompt_wav` | file | yes |

### POST /inference_cross_lingual

| Field | Type | Required |
|-------|------|----------|
| `tts_text` | form | yes |
| `prompt_wav` | file | yes |

### POST /inference_instruct

| Field | Type | Required |
|-------|------|----------|
| `tts_text` | form | yes |
| `spk_id` | form | yes |
| `instruct_text` | form | yes |

### POST /inference_instruct2

| Field | Type | Required |
|-------|------|----------|
| `tts_text` | form | yes |
| `instruct_text` | form | yes |
| `prompt_wav` | file | yes |

## Helper script

Pass host explicitly (required unless `COSYVOICE_HOST` is set):

```bash
python skills/cosyvoice-fastapi/scripts/tts_request.py \
  --host "${COSYVOICE_HOST}" \
  --port 56786 \
  --mode cross_lingual \
  --tts-text "<|zh|>你好，世界" \
  --prompt-wav stup20s.wav \
  --output demo.wav
```

Script flags: `--host`, `--port`, `--prompt-text`, `--prompt-wav`, `--instruct-text`, `--sample-rate`.

## Quick curl

Replace `{host}` with the address the user provided:

```bash
curl -s -o /dev/null -w "%{http_code}" "http://{host}:56786/docs"

curl -X POST "http://{host}:56786/inference_cross_lingual" \
  -F "tts_text=<|zh|>你好，这是一次跨语言测试。" \
  -F "prompt_wav=@stup20s.wav" \
  --output out.pcm
```

`prompt_wav=@file` uploads the **entire wav file** to the server (not a local path reference).

Convert PCM to WAV:

```bash
python -c "
import wave
pcm = open('out.pcm','rb').read()
with wave.open('out.wav','wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050); w.writeframes(pcm)
"
```

## Python (requests)

```python
import os, requests, wave

host = os.environ["COSYVOICE_HOST"]  # or value from user
port = os.environ.get("COSYVOICE_PORT", "56786")
url = f"http://{host}:{port}/inference_cross_lingual"

with open("stup20s.wav", "rb") as f:
    resp = requests.post(
        url,
        data={"tts_text": "<|zh|>你好，世界"},
        files={"prompt_wav": ("stup20s.wav", f, "audio/wav")},
        stream=True,
        timeout=600,
    )
resp.raise_for_status()
pcm = b"".join(resp.iter_content(chunk_size=16000))
with wave.open("out.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050); w.writeframes(pcm)
```

## Start server (on the GPU machine)

```bash
cd runtime/python/fastapi
python3 server.py --port 56786 --model_dir pretrained_models/CosyVoice-300M
```

Or from repo root: `./start_fastapi.sh`

## Common errors

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Connection refused | Wrong host/port or server down | Confirm address with user; start service |
| 422 Unprocessable | Missing form field or file | Match endpoint parameter table |
| Empty/silent output | Wrong PCM sample rate on decode | Use 22050 Hz unless model differs |
| instruct fails | Wrong model type | Use Instruct model for `/inference_instruct` |
| CUDA OOM | GPU memory | Reduce concurrency or use smaller model |

## Notes

- Server source: `runtime/python/fastapi/server.py`
- Official client: `runtime/python/fastapi/client.py`
- More examples: [examples.md](examples.md)
