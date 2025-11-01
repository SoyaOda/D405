#!/usr/bin/env python3
"""
深度データの内容を確認
"""

import numpy as np
import matplotlib.pyplot as plt

# データ読み込み
depth_path = "alignment_test/depth_raw_20251010_230711.npy"
depth = np.load(depth_path)

print("=" * 70)
print("深度データ検査")
print("=" * 70)

print(f"\nShape: {depth.shape}")
print(f"Dtype: {depth.dtype}")
print(f"最小値: {depth.min()}")
print(f"最大値: {depth.max()}")
print(f"平均値: {depth.mean():.2f}")
print(f"中央値: {np.median(depth):.2f}")

# ゼロでない値の統計
nonzero = depth[depth > 0]
print(f"\nゼロでない値:")
print(f"  個数: {len(nonzero):,} / {depth.size:,} ({len(nonzero)/depth.size*100:.1f}%)")
if len(nonzero) > 0:
    print(f"  範囲: {nonzero.min()} - {nonzero.max()}")
    print(f"  平均: {nonzero.mean():.2f}")
    print(f"  中央値: {np.median(nonzero):.2f}")

    # パーセンタイル
    print(f"\nパーセンタイル:")
    for p in [5, 25, 50, 75, 95]:
        val = np.percentile(nonzero, p)
        print(f"  {p:2d}%: {val:.1f}")

# ヒストグラム
print("\nヒストグラム（上位10ビン）:")
hist, bins = np.histogram(nonzero, bins=50)
sorted_indices = np.argsort(hist)[::-1][:10]
for idx in sorted_indices:
    print(f"  {bins[idx]:.1f} - {bins[idx+1]:.1f}: {hist[idx]:,} pixels")

# 画像として表示（中央部分）
h, w = depth.shape
center_region = depth[h//4:3*h//4, w//4:3*w//4]
center_nonzero = center_region[center_region > 0]

print(f"\n中央領域:")
print(f"  サイズ: {center_region.shape}")
print(f"  ゼロでない値: {len(center_nonzero):,}")
if len(center_nonzero) > 0:
    print(f"  範囲: {center_nonzero.min()} - {center_nonzero.max()}")
    print(f"  平均: {center_nonzero.mean():.2f}")
