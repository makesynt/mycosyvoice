# Copyright (c) 2024 Alibaba Inc (authors: Xiang Lyu)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import sys
import argparse
import logging
import tempfile
logging.getLogger('matplotlib').setLevel(logging.WARNING)
from fastapi import FastAPI, UploadFile, Form, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import numpy as np
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append('{}/../../..'.format(ROOT_DIR))
sys.path.append('{}/../../../third_party/Matcha-TTS'.format(ROOT_DIR))
from cosyvoice.cli.cosyvoice import AutoModel
from cosyvoice.utils.common import set_all_random_seed

# Align with webui.py defaults: fixed seed and Gradio-like peak normalization.
INFERENCE_SEED = 0
TARGET_PEAK = 0.88

app = FastAPI()
# set cross region allowance
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"])


def normalize_peak(speech: np.ndarray, target_peak: float = TARGET_PEAK) -> np.ndarray:
    speech = np.asarray(speech, dtype=np.float32)
    peak = np.max(np.abs(speech))
    if peak > 1e-9:
        speech = speech / peak * target_peak
    return speech


def collect_inference(infer_fn, *args, **kwargs):
    set_all_random_seed(INFERENCE_SEED)
    return list(infer_fn(*args, **kwargs))


def generate_data(model_output):
    for i in model_output:
        speech = normalize_peak(i['tts_speech'].numpy())
        tts_audio = (speech * (2 ** 15)).astype(np.int16).tobytes()
        yield tts_audio


async def save_upload_wav(upload: UploadFile) -> str:
    suffix = os.path.splitext(upload.filename or '')[1] or '.wav'
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    with open(path, 'wb') as f:
        f.write(await upload.read())
    return path


def infer_with_prompt_wav(infer_fn, prompt_path, *args):
    try:
        return collect_inference(infer_fn, *args, prompt_path)
    finally:
        if os.path.exists(prompt_path):
            os.unlink(prompt_path)


@app.get("/inference_sft")
@app.post("/inference_sft")
async def inference_sft(tts_text: str = Form(), spk_id: str = Form()):
    model_output = collect_inference(cosyvoice.inference_sft, tts_text, spk_id)
    return StreamingResponse(generate_data(model_output))


@app.get("/inference_zero_shot")
@app.post("/inference_zero_shot")
async def inference_zero_shot(tts_text: str = Form(), prompt_text: str = Form(), prompt_wav: UploadFile = File()):
    prompt_path = await save_upload_wav(prompt_wav)
    model_output = infer_with_prompt_wav(cosyvoice.inference_zero_shot, prompt_path, tts_text, prompt_text)
    return StreamingResponse(generate_data(model_output))


@app.get("/inference_cross_lingual")
@app.post("/inference_cross_lingual")
async def inference_cross_lingual(tts_text: str = Form(), prompt_wav: UploadFile = File()):
    prompt_path = await save_upload_wav(prompt_wav)
    model_output = infer_with_prompt_wav(cosyvoice.inference_cross_lingual, prompt_path, tts_text)
    return StreamingResponse(generate_data(model_output))


@app.get("/inference_instruct")
@app.post("/inference_instruct")
async def inference_instruct(tts_text: str = Form(), spk_id: str = Form(), instruct_text: str = Form()):
    model_output = collect_inference(cosyvoice.inference_instruct, tts_text, spk_id, instruct_text)
    return StreamingResponse(generate_data(model_output))


@app.get("/inference_instruct2")
@app.post("/inference_instruct2")
async def inference_instruct2(tts_text: str = Form(), instruct_text: str = Form(), prompt_wav: UploadFile = File()):
    prompt_path = await save_upload_wav(prompt_wav)
    model_output = infer_with_prompt_wav(cosyvoice.inference_instruct2, prompt_path, tts_text, instruct_text)
    return StreamingResponse(generate_data(model_output))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',
                        type=int,
                        default=50000)
    parser.add_argument('--model_dir',
                        type=str,
                        default='iic/CosyVoice2-0.5B',
                        help='local path or modelscope repo id')
    args = parser.parse_args()
    cosyvoice = AutoModel(model_dir=args.model_dir)
    uvicorn.run(app, host="0.0.0.0", port=args.port)
