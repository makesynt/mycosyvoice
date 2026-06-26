#!/usr/bin/env python3
"""Call CosyVoice FastAPI server and save response as WAV."""

import argparse
import os
import sys
import wave

import requests


MODES = {
    "sft": "inference_sft",
    "zero_shot": "inference_zero_shot",
    "cross_lingual": "inference_cross_lingual",
    "instruct": "inference_instruct",
    "instruct2": "inference_instruct2",
}


def parse_args():
    parser = argparse.ArgumentParser(description="CosyVoice FastAPI TTS client")
    default_host = os.environ.get("COSYVOICE_HOST", "")
    default_port = int(os.environ.get("COSYVOICE_PORT", "56786"))
    parser.add_argument(
        "--host",
        default=default_host,
        required=not default_host,
        help="server IP/hostname (or set COSYVOICE_HOST)",
    )
    parser.add_argument("--port", type=int, default=default_port)
    parser.add_argument(
        "--mode",
        required=True,
        choices=list(MODES.keys()),
        help="inference mode",
    )
    parser.add_argument("--tts-text", required=True, help="text to synthesize")
    parser.add_argument("--spk-id", default="中文女", help="speaker id (sft/instruct)")
    parser.add_argument("--prompt-text", default="", help="prompt text (zero_shot)")
    parser.add_argument("--prompt-wav", default="", help="prompt wav path")
    parser.add_argument("--instruct-text", default="", help="instruct text")
    parser.add_argument("--output", default="output.wav", help="output wav path")
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=22050,
        help="PCM sample rate for WAV header",
    )
    return parser.parse_args()


def build_request(args):
    path = MODES[args.mode]
    url = f"http://{args.host}:{args.port}/{path}"
    data = {"tts_text": args.tts_text}
    files = None

    if args.mode == "sft":
        data["spk_id"] = args.spk_id
    elif args.mode == "zero_shot":
        if not args.prompt_text or not args.prompt_wav:
            sys.exit("zero_shot requires --prompt-text and --prompt-wav")
        data["prompt_text"] = args.prompt_text
        files = {"prompt_wav": open(args.prompt_wav, "rb")}
    elif args.mode == "cross_lingual":
        if not args.prompt_wav:
            sys.exit("cross_lingual requires --prompt-wav")
        files = {"prompt_wav": open(args.prompt_wav, "rb")}
    elif args.mode == "instruct":
        data["spk_id"] = args.spk_id
        if not args.instruct_text:
            sys.exit("instruct requires --instruct-text")
        data["instruct_text"] = args.instruct_text
    elif args.mode == "instruct2":
        if not args.instruct_text or not args.prompt_wav:
            sys.exit("instruct2 requires --instruct-text and --prompt-wav")
        data["instruct_text"] = args.instruct_text
        files = {"prompt_wav": open(args.prompt_wav, "rb")}

    return url, data, files


def pcm_to_wav(pcm_bytes, wav_path, sample_rate):
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)


def main():
    args = parse_args()
    url, data, files = build_request(args)

    try:
        resp = requests.post(url, data=data, files=files, stream=True, timeout=600)
        resp.raise_for_status()
        pcm = b"".join(resp.iter_content(chunk_size=16000))
    finally:
        if files:
            files["prompt_wav"].close()

    if not pcm:
        sys.exit("empty response: check server logs and request parameters")

    pcm_to_wav(pcm, args.output, args.sample_rate)
    print(f"saved {len(pcm)} bytes PCM -> {args.output} ({args.sample_rate} Hz)")


if __name__ == "__main__":
    main()
