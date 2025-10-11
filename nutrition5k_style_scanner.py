#!/usr/bin/env python3
"""
Nutrition5k スタイル食材スキャナー

Nutrition5k データセットの撮像プロトコルに基づいた実装：
- オーバーヘッド（真上）からの撮影
- RGB + 深度データの保存
- 16ビット深度エンコーディング（1m = 10,000ユニット）
- Nutrition5k互換のデータフォーマット

使い方: sudo /Users/moei/program/D405/venv/bin/python3 nutrition5k_style_scanner.py [食材名]

操作:
  's' キー: マルチフレーム平均撮影（高品質）
  'c' キー: 単一フレーム撮影（クイック）
  'q' キー: 終了
"""

import pyrealsense2 as rs
import numpy as np
import cv2
import os
import sys
from datetime import datetime

# Nutrition5k スタイルのディレクトリ構造
BASE_DIR = "/Users/moei/program/D405/nutrition5k_data"
OVERHEAD_DIR = os.path.join(BASE_DIR, "imagery", "realsense_overhead")
os.makedirs(OVERHEAD_DIR, exist_ok=True)

# Nutrition5k の深度エンコーディング定数
DEPTH_SCALE_FACTOR = 10000  # 1メートル = 10,000ユニット
MAX_DEPTH_METERS = 0.4      # 最大深度 0.4m（Nutrition5k仕様）
MAX_DEPTH_UNITS = int(MAX_DEPTH_METERS * DEPTH_SCALE_FACTOR)  # 4,000

def setup_filters():
    """ポストプロセッシングフィルター"""
    depth_to_disparity = rs.disparity_transform(True)
    spatial = rs.spatial_filter()
    spatial.set_option(rs.option.filter_magnitude, 2)
    spatial.set_option(rs.option.filter_smooth_alpha, 0.5)
    spatial.set_option(rs.option.filter_smooth_delta, 20)

    temporal = rs.temporal_filter()
    temporal.set_option(rs.option.filter_smooth_alpha, 0.4)
    temporal.set_option(rs.option.filter_smooth_delta, 20)

    disparity_to_depth = rs.disparity_transform(False)
    hole_filling = rs.hole_filling_filter()

    return {
        'depth_to_disparity': depth_to_disparity,
        'spatial': spatial,
        'temporal': temporal,
        'disparity_to_depth': disparity_to_depth,
        'hole_filling': hole_filling
    }

def apply_filters(depth_frame, filters):
    """フィルター適用"""
    frame = depth_frame
    frame = filters['depth_to_disparity'].process(frame)
    frame = filters['spatial'].process(frame)
    frame = filters['temporal'].process(frame)
    frame = filters['disparity_to_depth'].process(frame)
    frame = filters['hole_filling'].process(frame)
    return frame

def capture_multi_frame_average(pipeline, filters, align_to_color, num_frames=20):
    """複数フレーム平均（中央値フィルター）"""
    print(f"\n中央値フィルター適用中（{num_frames}フレーム）...")

    depth_frames = []
    color_frames = []

    for i in range(num_frames):
        frames = pipeline.wait_for_frames()
        aligned_frames = align_to_color.process(frames)
        aligned_depth = aligned_frames.get_depth_frame()
        aligned_color = aligned_frames.get_color_frame()

        if not aligned_depth or not aligned_color:
            continue

        filtered_depth = apply_filters(aligned_depth, filters)
        depth_frames.append(np.asanyarray(filtered_depth.get_data()))
        color_frames.append(np.asanyarray(aligned_color.get_data()))

        if (i + 1) % 5 == 0:
            print(f"  {i + 1}/{num_frames} フレーム...")

    # 中央値フィルター
    depth_stack = np.stack(depth_frames, axis=0)
    masked_depth = np.ma.masked_equal(depth_stack, 0)
    depth_image = np.ma.median(masked_depth, axis=0).filled(0).astype(np.uint16)
    color_image = color_frames[-1]

    print("✓ フレーム平均化完了")
    return color_image, depth_image

def convert_to_nutrition5k_depth(depth_mm, camera_depth_scale):
    """
    RealSense深度データをNutrition5k形式に変換

    Args:
        depth_mm: RealSense深度データ（ミリメートル単位）
        camera_depth_scale: カメラの深度スケール

    Returns:
        Nutrition5k形式の深度データ（16-bit、10,000 units/meter）
    """
    # RealSenseの深度をメートルに変換
    depth_meters = depth_mm * camera_depth_scale

    # Nutrition5k形式に変換（1m = 10,000ユニット）
    depth_n5k = (depth_meters * DEPTH_SCALE_FACTOR).astype(np.uint16)

    # 最大値でクリップ（Nutrition5k仕様: 0.4m = 4,000ユニット）
    depth_n5k = np.clip(depth_n5k, 0, MAX_DEPTH_UNITS)

    return depth_n5k

def create_colorized_depth(depth_n5k):
    """
    Nutrition5kスタイルの深度カラーマップ作成

    青 = 近い（0m）
    赤 = 遠い（0.4m）
    """
    # 正規化（0-255）
    normalized = (depth_n5k.astype(np.float32) / MAX_DEPTH_UNITS * 255).astype(np.uint8)

    # JETカラーマップ適用（青→緑→黄→赤）
    colorized = cv2.applyColorMap(normalized, cv2.COLORMAP_JET)

    return colorized

def save_nutrition5k_format(color_image, depth_raw, depth_colorized, dish_id, metadata):
    """Nutrition5k形式で保存"""

    # RGB画像
    rgb_path = os.path.join(OVERHEAD_DIR, f"rgb_{dish_id}.png")
    cv2.imwrite(rgb_path, color_image)

    # Raw深度画像（16-bit PNG）
    depth_raw_path = os.path.join(OVERHEAD_DIR, f"depth_raw_{dish_id}.png")
    cv2.imwrite(depth_raw_path, depth_raw)

    # Colorized深度画像
    depth_color_path = os.path.join(OVERHEAD_DIR, f"depth_colorized_{dish_id}.png")
    cv2.imwrite(depth_color_path, depth_colorized)

    # メタデータ
    metadata_path = os.path.join(OVERHEAD_DIR, f"metadata_{dish_id}.txt")
    with open(metadata_path, 'w') as f:
        f.write(f"Dish ID: {dish_id}\n")
        f.write(f"Timestamp: {metadata['timestamp']}\n")
        f.write(f"Food Name: {metadata['food_name']}\n")
        f.write(f"Resolution: {color_image.shape[1]}x{color_image.shape[0]}\n")
        f.write(f"Depth Encoding: 16-bit, {DEPTH_SCALE_FACTOR} units/meter\n")
        f.write(f"Max Depth: {MAX_DEPTH_METERS}m ({MAX_DEPTH_UNITS} units)\n")
        f.write(f"Frames Averaged: {metadata['frames_averaged']}\n")
        f.write(f"\n[Depth Statistics (meters)]\n")
        valid_depths = depth_raw[depth_raw > 0] / DEPTH_SCALE_FACTOR
        if len(valid_depths) > 0:
            f.write(f"  Min: {valid_depths.min():.4f}m\n")
            f.write(f"  Max: {valid_depths.max():.4f}m\n")
            f.write(f"  Mean: {valid_depths.mean():.4f}m\n")
            f.write(f"  Median: {np.median(valid_depths):.4f}m\n")
            f.write(f"  Valid pixels: {len(valid_depths)} / {depth_raw.size} ({100*len(valid_depths)/depth_raw.size:.1f}%)\n")

    print(f"\n✓ Nutrition5k形式で保存:")
    print(f"  RGB: {rgb_path}")
    print(f"  Depth (raw): {depth_raw_path}")
    print(f"  Depth (colorized): {depth_color_path}")
    print(f"  Metadata: {metadata_path}")
    print(f"  → {OVERHEAD_DIR}/\n")

    return dish_id

def main():
    food_name = sys.argv[1] if len(sys.argv) > 1 else "unknown_food"
    num_frames_to_average = int(sys.argv[2]) if len(sys.argv) > 2 else 20

    print("=" * 70)
    print("Nutrition5k スタイル食材スキャナー")
    print("=" * 70)
    print(f"食材名: {food_name}")
    print(f"保存先: {OVERHEAD_DIR}")
    print(f"平均化フレーム数: {num_frames_to_average}")
    print("\n[Nutrition5k 互換設定]")
    print(f"  深度エンコーディング: 16-bit, {DEPTH_SCALE_FACTOR} units/meter")
    print(f"  最大深度: {MAX_DEPTH_METERS}m ({MAX_DEPTH_UNITS} units)")
    print(f"  解像度: 1280x720 (FOV最適)")
    print(f"  カラーマップ: 青(近) → 赤(遠)")
    print("\n操作:")
    print("  's' キー: マルチフレーム平均撮影（高品質）")
    print("  'c' キー: 単一フレーム撮影（クイック）")
    print("  'q' キー: 終了")
    print("=" * 70)

    # パイプライン設定
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)

    print("\nパイプライン開始...")
    profile = pipeline.start(config)

    # カメラ設定
    depth_sensor = profile.get_device().first_depth_sensor()
    if depth_sensor.supports(rs.option.visual_preset):
        depth_sensor.set_option(rs.option.visual_preset, 3)  # High Accuracy
    camera_depth_scale = depth_sensor.get_depth_scale()

    print(f"✓ RealSense深度スケール: {camera_depth_scale}")

    align_to_color = rs.align(rs.stream.color)
    filters = setup_filters()

    print("✓ 準備完了\n")

    # ウォームアップ
    for _ in range(30):
        pipeline.wait_for_frames()

    try:
        frame_count = 0
        saved_count = 0

        while True:
            frames = pipeline.wait_for_frames()
            aligned_frames = align_to_color.process(frames)
            aligned_depth = aligned_frames.get_depth_frame()
            aligned_color = aligned_frames.get_color_frame()

            if not aligned_depth or not aligned_color:
                continue

            # リアルタイムプレビュー用
            filtered_depth = apply_filters(aligned_depth, filters)
            depth_preview = np.asanyarray(filtered_depth.get_data())
            color_preview = np.asanyarray(aligned_color.get_data())

            # Nutrition5k形式に変換してプレビュー
            depth_n5k_preview = convert_to_nutrition5k_depth(depth_preview, camera_depth_scale)
            depth_colorized_preview = create_colorized_depth(depth_n5k_preview)

            # 横並び表示
            images = np.hstack([color_preview, depth_colorized_preview])

            # 中央深度表示
            h, w = depth_n5k_preview.shape
            center_depth_m = depth_n5k_preview[h//2, w//2] / DEPTH_SCALE_FACTOR

            # 距離チェック（D405推奨: 7-50cm）
            if 0.07 <= center_depth_m <= 0.50:
                status = "OPTIMAL (7-50cm)"
                color = (0, 255, 0)
            elif center_depth_m < 0.07:
                status = "TOO CLOSE"
                color = (0, 165, 255)
            else:
                status = "TOO FAR"
                color = (0, 0, 255)

            cv2.putText(images, f"Food: {food_name}",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(images, f"Center: {center_depth_m:.3f}m [{status}]",
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.putText(images, f"Saved: {saved_count} | 's'=Multi 'c'=Quick 'q'=Quit",
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            cv2.imshow('Nutrition5k Scanner - RGB | Depth', images)

            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                print("\n終了...")
                break

            elif key == ord('s'):
                # マルチフレーム平均撮影
                avg_color, avg_depth = capture_multi_frame_average(
                    pipeline, filters, align_to_color, num_frames_to_average
                )
                depth_n5k = convert_to_nutrition5k_depth(avg_depth, camera_depth_scale)
                depth_colorized = create_colorized_depth(depth_n5k)

                dish_id = f"{food_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                metadata = {
                    'timestamp': datetime.now().isoformat(),
                    'food_name': food_name,
                    'frames_averaged': num_frames_to_average
                }

                save_nutrition5k_format(avg_color, depth_n5k, depth_colorized, dish_id, metadata)
                saved_count += 1

            elif key == ord('c'):
                # 単一フレーム撮影（クイック）
                print("\n単一フレーム撮影...")
                depth_n5k = convert_to_nutrition5k_depth(depth_preview, camera_depth_scale)
                depth_colorized = create_colorized_depth(depth_n5k)

                dish_id = f"{food_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_quick"
                metadata = {
                    'timestamp': datetime.now().isoformat(),
                    'food_name': food_name,
                    'frames_averaged': 1
                }

                save_nutrition5k_format(color_preview, depth_n5k, depth_colorized, dish_id, metadata)
                saved_count += 1

            frame_count += 1

    finally:
        pipeline.stop()
        cv2.destroyAllWindows()
        print("\n" + "=" * 70)
        print("✓ スキャンセッション終了")
        print(f"  食材: {food_name}")
        print(f"  総フレーム数: {frame_count}")
        print(f"  保存数: {saved_count}")
        print(f"  保存先: {OVERHEAD_DIR}")
        print("=" * 70)

if __name__ == "__main__":
    main()
