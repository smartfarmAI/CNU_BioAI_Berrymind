#!/usr/bin/env python3
import argparse
import json
import re
import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont
import numpy as np
import torch
from sam3.model_builder import build_sam3_image_model
from sam3.model.sam3_image_processor import Sam3Processor


def setup_model(bpe_path="sam3/sam3/assets/bpe_simple_vocab_16e6.txt.gz"):
    """모델 초기화"""
    if "HF_TOKEN" not in os.environ and Path("hf_token.txt").exists():
        with open("hf_token.txt", 'r') as f:
            os.environ["HF_TOKEN"] = f.read().strip()

    if torch.cuda.is_available():
        torch.autocast(device_type="cuda", dtype=torch.bfloat16).__enter__()

    model = build_sam3_image_model(bpe_path=bpe_path)
    processor = Sam3Processor(model, confidence_threshold=0.3)
    return processor


def extract_datetime(filename: str) -> Tuple[str, str]:
    """파일명에서 날짜/시간 추출"""
    match = re.search(r"(\d{8})(\d{6})", filename)
    if match:
        date_str, time_str = match.groups()
        date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        time = f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
        return date, time
    return "unknown", "unknown"


def draw_boxes_with_labels(
    pil_image: Image.Image, 
    all_boxes: Dict[str, np.ndarray],  
    all_scores: Dict[str, np.ndarray], 
    width: int = 3,
    font_size: int = 20
) -> Image.Image:
    """모든 프롬프트의 바운딩 박스를 하나의 이미지에 그립니다."""
    img = pil_image.copy()
    draw = ImageDraw.Draw(img)
    
    prompt_colors = {
        "FLOWER": (255, 0, 0),      # 빨강
        "GREEN_FRUIT": (0, 255, 0), # 초록
        "RED_FRUIT": (0, 0, 255),   # 파랑
    }
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # 각 프롬프트별 박스 그리기
    for prompt, boxes in all_boxes.items():
        if boxes is None or len(boxes) == 0:
            continue
            
        color = prompt_colors.get(prompt.upper().replace(" ", "_"), (128, 128, 128))
        scores = all_scores.get(prompt, np.array([]))
        
        for i, (box, score) in enumerate(zip(boxes, scores)):
            x1, y1, x2, y2 = [float(v) for v in box]
            
            # 바운딩 박스 그리기
            draw.rectangle([x1, y1, x2, y2], outline=color, width=width)
            
            # 신뢰도 라벨 그리기
            label = f"{prompt[:3].upper()} {score:.2f}"
            label_bbox = draw.textbbox((0, 0), label, font=font)
            label_width = label_bbox[2] - label_bbox[0]
            label_height = label_bbox[3] - label_bbox[1]
            
            # 라벨 배경
            label_bg_x1 = x1
            label_bg_y1 = y1 - label_height - 2
            label_bg_x2 = label_bg_x1 + label_width + 4
            label_bg_y2 = label_bg_y1 + label_height + 4
            draw.rectangle([label_bg_x1, label_bg_y1, label_bg_x2, label_bg_y2], 
                          fill=color + (100,))
            
            # 라벨 텍스트
            draw.text((label_bg_x1 + 2, label_bg_y1 + 2), label, fill=(255, 255, 255), font=font)

    return img


def process_image(
    image_path: Path, 
    processor: Sam3Processor, 
    prompts: List[str], 
    confidence_threshold: float = 0.5,
    boxed_output_dir: Path | None = None
) -> Dict:
    """이미지 처리 및 상세 JSON + 모든 박스 통합 이미지 생성"""
    image = Image.open(image_path).convert("RGB")
    filename = image_path.name

    detections = {}
    detailed_detections = {}
    all_valid_boxes = {}
    all_valid_scores = {}

    # 각 프롬프트별 탐지
    for prompt in prompts:
        prompt_upper = prompt.upper()
        
        state = processor.set_image(image)
        state = processor.set_text_prompt(state=state, prompt=prompt)

        scores = state["scores"].cpu().float().numpy()
        boxes = state.get("boxes")
        if boxes is not None:
            boxes = boxes.cpu().numpy()

        # 신뢰도 기준으로 필터링된 박스들
        valid_indices = scores > confidence_threshold
        valid_scores = scores[valid_indices]
        valid_boxes = boxes[valid_indices] if boxes is not None else np.empty((0, 4))

        detections[prompt_upper] = 1 if len(valid_scores) > 0 else 0
        
        detailed_detections[prompt_upper] = {
            "count": len(valid_scores),
            "scores": valid_scores.tolist(),
            "boxes": valid_boxes.tolist() if len(valid_boxes) > 0 else []
        }

        # 통합 이미지용으로 저장
        if len(valid_scores) > 0:
            all_valid_boxes[prompt_upper] = valid_boxes
            all_valid_scores[prompt_upper] = valid_scores

    # 모든 박스를 하나의 이미지에 그리기
    if boxed_output_dir and any(len(boxes) > 0 for boxes in all_valid_boxes.values()):
        boxed_output_dir.mkdir(parents=True, exist_ok=True)
        
        merged_img = draw_boxes_with_labels(
            image, all_valid_boxes, all_valid_scores, 
            width=3, font_size=20
        )
        boxed_path = boxed_output_dir / f"{image_path.stem}_all.png"
        merged_img.save(boxed_path)

    # 메타데이터
    date, time = extract_datetime(filename)

    return {
        "filename": filename,
        "date": date,
        "time": time,
        "detections": detections,  # FLOWER: 0/1, GREEN_FRUIT: 0/1, RED_FRUIT: 0/1
        "detailed_detections": detailed_detections
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image_folder", default="./images")
    parser.add_argument("--output_folder", default="./json_dir")
    parser.add_argument("--backup_folder", default="./processed_images")
    parser.add_argument("--boxed_folder", default="./boxed_images")
    parser.add_argument("--prompts", nargs="+", default=["GREEN FRUIT", "RED FRUIT", "FLOWER"])
    parser.add_argument("--confidence", type=float, default=0.5)
    parser.add_argument("--pattern", default="*.png")
    args = parser.parse_args()

    image_dir = Path(args.image_folder)
    json_dir = Path(args.output_folder)
    backup_dir = Path(args.backup_folder)
    boxed_dir = Path(args.boxed_folder)

    json_dir.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)
    boxed_dir.mkdir(parents=True, exist_ok=True)

    processor = setup_model()

    image_paths = list(image_dir.glob(args.pattern))

    for image_path in image_paths:
        try:
            result = process_image(
                image_path=image_path,
                processor=processor,
                prompts=args.prompts,
                confidence_threshold=args.confidence,
                boxed_output_dir=boxed_dir,
            )

            json_path = json_dir / f"{image_path.stem}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            # 원본 이미지를 백업 폴더로 이동
            backup_file = backup_dir / image_path.name
            shutil.move(str(image_path), str(backup_file))

        except Exception:
            pass

    print("완료")


if __name__ == "__main__":
    main()
