#!/usr/bin/env python3
"""Test SAM2.1 segmentation on real captured images"""

import sys
sys.path.insert(0, '/Users/moei/program/D405')

import numpy as np
import cv2
from src.segmentation import SAM2Segmentor

# Load the captured image
image_path = "/Users/moei/program/D405/captured_images/color_20251010_223706.png"
print(f"Loading image: {image_path}")

rgb_image = cv2.imread(image_path)
if rgb_image is None:
    print(f"Error: Failed to load image")
    sys.exit(1)

rgb_image = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2RGB)
print(f"Image shape: {rgb_image.shape}")

# Initialize SAM2.1
print("\nInitializing SAM2.1...")
segmentor = SAM2Segmentor(model_type="sam2.1_hiera_tiny", device="cpu")

# Run segmentation
print("\nRunning segmentation...")
mask = segmentor.segment_bowl_automatic(rgb_image, num_points=10)

if mask is not None:
    print(f"\n✅ Segmentation successful!")
    print(f"  Mask shape: {mask.shape}")
    print(f"  Mask pixels: {mask.sum()} / {mask.size} ({mask.sum()/mask.size*100:.1f}%)")

    # Visualize
    overlay = segmentor.visualize_mask(rgb_image, mask)
    output_path = "/tmp/real_segmented.png"
    cv2.imwrite(output_path, cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
    print(f"  Visualization saved: {output_path}")

    # Also save the mask
    mask_path = "/tmp/real_mask.png"
    cv2.imwrite(mask_path, (mask * 255).astype(np.uint8))
    print(f"  Mask saved: {mask_path}")
else:
    print("\n❌ Segmentation failed")
    sys.exit(1)
