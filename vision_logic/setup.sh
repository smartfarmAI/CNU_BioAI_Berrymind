#!/bin/bash

set -e

# 1. HF 토큰 로드

if [ -f "hf_token.txt" ]; then
    export HF_TOKEN=$(cat hf_token.txt | tr -d '[:space:]')

else
    echo "⚠ hf_token.txt 파일을 찾을 수 없습니다"
    echo "  프로젝트 폴더에 hf_token.txt를 생성하세요"
fi

# 2. requirements.txt에서 패키지 설치

if [ -f "requirements.txt" ]; then
    pip install -q -r requirements.txt

else
    echo "❌ requirements.txt 파일을 찾을 수 없습니다"
    exit 1
fi

# 3. SAM3 클론 및 설치

if [ ! -d "sam3" ]; then
    git clone -q https://github.com/facebookresearch/sam3.git 2>/dev/null || {
        exit 1
    }
fi

cd sam3
pip install -q -e . 2>/dev/null || pip install -q -e .
cd ..

# 4. 설치 확인

python -c "from sam3.model_builder import build_sam3_image_model; print('✓ SAM3 import 성공')" || {
    echo "❌ SAM3 import 실패"
    exit 1
}

echo "OK"

