#!/usr/bin/env python3
"""
OCR Server - 基于 Qwen3-VL-8B 的PDF页面OCR识别服务
部署在多卡4090D上，通过HTTP API接收图片并返回识别文本。

启动: python server.py --port 8765
"""

import argparse
import base64
import io
import json
import logging
import time
from pathlib import Path

import torch
from flask import Flask, jsonify, request
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor
from qwen_vl_utils import process_vision_info

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global model reference
model = None
processor = None


def load_model(gpu_id: int = None):
    """Load Qwen3-VL-8B model on specified GPU."""
    global model, processor

    if gpu_id is not None:
        import os
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
        logger.info(f"Using GPU {gpu_id} only")

    model_name = "Qwen/Qwen3-VL-8B-Instruct"
    logger.info(f"Loading model {model_name}...")

    processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)

    # Load with INT4 quantization to reduce VRAM usage (~6GB instead of ~16GB)
    try:
        from transformers import BitsAndBytesConfig
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
        )
        model = AutoModelForImageTextToText.from_pretrained(
            model_name,
            quantization_config=quantization_config,
            device_map="auto",
            trust_remote_code=True,
        )
        logger.info("Model loaded with INT4 quantization")
    except ImportError:
        logger.warning("bitsandbytes not found, loading with FP16")
        model = AutoModelForImageTextToText.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )
    model.eval()

    gpu_count = torch.cuda.device_count()
    logger.info(f"Model loaded on {gpu_count} GPU(s)")
    for i in range(gpu_count):
        name = torch.cuda.get_device_name(i)
        mem = torch.cuda.get_device_properties(i).total_memory / 1024**3
        logger.info(f"  GPU {i}: {name} ({mem:.1f} GB)")

    return model, processor


def ocr_image(image_bytes: bytes, prompt: str = None) -> str:
    """Run OCR on a single image, return recognized text."""
    if prompt is None:
        prompt = (
            "请仔细识别这张图片中的所有中文文字内容，按照原文的段落格式输出。"
            "注意：1) 保持原文的段落分隔；2) 去掉页码数字；"
            "3) 去掉页眉页脚（如'加尔文文集'等）；"
            "4) 保留脚注标记（如①②等）；"
            "5) 如果有希腊文或希伯来文原文，也保留。"
            "只输出识别到的文字内容，不要添加任何解释。"
        )

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }
    ]

    text_input = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text_input],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    ).to(model.device)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=4096,
            do_sample=False,
            temperature=0.1,
        )

    # Decode only the generated part
    generated_ids = output_ids[0][inputs.input_ids.shape[1]:]
    result = processor.decode(generated_ids, skip_special_tokens=True)
    return result.strip()


@app.route("/ocr", methods=["POST"])
def handle_ocr():
    """API endpoint: receive base64-encoded image, return OCR text."""
    start = time.time()
    data = request.get_json()

    if not data or "image" not in data:
        return jsonify({"error": "Missing 'image' field (base64)"}), 400

    image_bytes = base64.b64decode(data["image"])
    prompt = data.get("prompt", None)

    try:
        text = ocr_image(image_bytes, prompt)
        elapsed = time.time() - start
        logger.info(f"OCR completed: {len(text)} chars in {elapsed:.1f}s")
        return jsonify({"text": text, "chars": len(text), "time": round(elapsed, 2)})
    except Exception as e:
        logger.error(f"OCR error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    gpu_count = torch.cuda.device_count()
    gpus = []
    for i in range(gpu_count):
        gpus.append({
            "id": i,
            "name": torch.cuda.get_device_name(i),
            "memory_total_gb": round(torch.cuda.get_device_properties(i).total_memory / 1024**3, 1),
            "memory_used_gb": round(torch.cuda.memory_allocated(i) / 1024**3, 1),
        })
    return jsonify({"status": "ok", "model": "Qwen2.5-VL-7B-Instruct", "gpus": gpus})


@app.route("/ocr_batch", methods=["POST"])
def handle_ocr_batch():
    """Batch OCR: receive list of base64 images, return list of texts."""
    start = time.time()
    data = request.get_json()

    if not data or "images" not in data:
        return jsonify({"error": "Missing 'images' field"}), 400

    results = []
    for i, img_b64 in enumerate(data["images"]):
        try:
            image_bytes = base64.b64decode(img_b64)
            text = ocr_image(image_bytes)
            results.append({"page": i, "text": text, "chars": len(text)})
            logger.info(f"  Batch page {i}: {len(text)} chars")
        except Exception as e:
            results.append({"page": i, "text": "", "error": str(e)})
            logger.error(f"  Batch page {i} error: {e}")

    elapsed = time.time() - start
    logger.info(f"Batch OCR: {len(results)} pages in {elapsed:.1f}s")
    return jsonify({"results": results, "total_time": round(elapsed, 2)})


def main():
    parser = argparse.ArgumentParser(description="OCR Server with Qwen3-VL")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--gpu", type=int, default=None, help="Specify GPU ID (e.g. 7)")
    args = parser.parse_args()

    load_model(gpu_id=args.gpu)
    logger.info(f"Starting server on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, threaded=False)


if __name__ == "__main__":
    main()
