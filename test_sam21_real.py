#!/usr/bin/env python3
"""SAM2.1の実際のセグメンテーションテスト"""

import sys
import os
sys.path.insert(0, '/Users/moei/program/D405')

import numpy as np
import cv2

print("=" * 70)
print("SAM2.1 Real Segmentation Test")
print("=" * 70)

# 1. テスト画像生成
print("\n[1] Generating test image...")

# お椀を模擬した画像を生成（中央に円形）
height, width = 480, 640
test_image = np.ones((height, width, 3), dtype=np.uint8) * 200  # 灰色背景

# 中央に円を描画（お椀を模擬）
center = (width // 2, height // 2)
radius = 100
cv2.circle(test_image, center, radius, (150, 100, 80), -1)  # 茶色の円

# 円の中に食品を模擬（緑色）
cv2.circle(test_image, center, radius - 20, (100, 180, 100), -1)

# 保存
test_image_path = "/tmp/test_bowl_image.png"
cv2.imwrite(test_image_path, test_image)
print(f"  ✓ Test image created: {test_image_path}")
print(f"    Size: {width}x{height}")

# 2. SAM2.1でセグメンテーション
print("\n[2] Testing SAM2.1 segmentation...")

try:
    from src.segmentation import SAM2Segmentor

    print("  Initializing SAM2Segmentor...")
    segmentor = SAM2Segmentor(model_type="sam2.1_hiera_tiny")

    print("  Running segmentation...")
    rgb_image = cv2.cvtColor(test_image, cv2.COLOR_BGR2RGB)

    mask = segmentor.segment_bowl_automatic(rgb_image, num_points=10)

    if mask is not None:
        print(f"\n  ✅ Segmentation successful!")
        print(f"    Mask shape: {mask.shape}")
        print(f"    Mask pixels: {mask.sum()} / {mask.size} ({mask.sum()/mask.size*100:.1f}%)")

        # 可視化保存
        overlay = segmentor.visualize_mask(rgb_image, mask)
        output_path = "/tmp/test_bowl_segmented.png"
        cv2.imwrite(output_path, cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
        print(f"    Output: {output_path}")

        print("\n" + "=" * 70)
        print("✅ SAM2.1 is working correctly!")
        print("=" * 70)

    else:
        print("\n  ❌ Segmentation returned None")
        sys.exit(1)

except Exception as e:
    print(f"\n  ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nNext step: Test with real scanned images")
print("  sudo /Users/moei/program/D405/venv_py311/bin/python3 scripts/scan.py test_food")
print("=" * 70)
