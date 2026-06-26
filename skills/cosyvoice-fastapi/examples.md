# CosyVoice FastAPI Examples

Replace `{host}` with the server IP/hostname from the user. Default port: `56786`.

## Health check

```bash
curl -s -o /dev/null -w "%{http_code}" "http://{host}:56786/docs"
```

## Cross-lingual — English ref audio, Chinese output

```bash
curl -X POST "http://{host}:56786/inference_cross_lingual" \
  -F "tts_text=<|zh|>你好，这是一次跨语言语音合成测试。" \
  -F "prompt_wav=@stup20s.wav" \
  --output cross_lingual_zh.pcm
```

## SFT — preset speaker

```bash
curl -X POST "http://{host}:56786/inference_sft" \
  -F "tts_text=你好，我是 CosyVoice" \
  -F "spk_id=中文女" \
  --output sft.pcm
```

## Zero-shot — voice cloning

```bash
curl -X POST "http://{host}:56786/inference_zero_shot" \
  -F "tts_text=收到好友从远方寄来的生日礼物。" \
  -F "prompt_text=希望你以后能够做的比我还好呦。" \
  -F "prompt_wav=@asset/zero_shot_prompt.wav" \
  --output zero_shot.pcm
```

## Helper script

```bash
export COSYVOICE_HOST="{host}"

python skills/cosyvoice-fastapi/scripts/tts_request.py \
  --host "${COSYVOICE_HOST}" \
  --mode cross_lingual \
  --tts-text "<|zh|>你好，世界" \
  --prompt-wav stup20s.wav \
  --output demo.wav
```

## Docker deployment

```bash
cd runtime/python
docker build -t cosyvoice:v1.0 .
docker run -d --runtime=nvidia -p 56786:56786 cosyvoice:v1.0 \
  /bin/bash -c "cd /opt/CosyVoice/CosyVoice/runtime/python/fastapi && \
  python3 server.py --port 56786 --model_dir iic/CosyVoice-300M && sleep infinity"
```

Then call `http://{host}:56786/...` where `{host}` is the Docker host IP.
