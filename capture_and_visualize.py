#!/usr/bin/env python3
"""
RealSense D405 深度データ可視化・画像保存スクリプト

使い方: sudo /Users/moei/program/D405/venv/bin/python3 capture_and_visualize.py

操作方法:
  's' キー: 現在のフレームを保存
  'q' キー: 終了
"""

import pyrealsense2 as rs
import numpy as np
import cv2
import os
from datetime import datetime

# 保存先ディレクトリの作成
SAVE_DIR = "/Users/moei/program/D405/captured_images"
os.makedirs(SAVE_DIR, exist_ok=True)

def save_images(color_image, depth_image, depth_colormap):
    """画像を保存"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    color_path = os.path.join(SAVE_DIR, f"color_{timestamp}.png")
    depth_path = os.path.join(SAVE_DIR, f"depth_{timestamp}.png")
    depth_raw_path = os.path.join(SAVE_DIR, f"depth_raw_{timestamp}.npy")

    # カラー画像の保存
    cv2.imwrite(color_path, color_image)
    print(f"✓ カラー画像を保存: {color_path}")

    # 深度画像（可視化版）の保存
    cv2.imwrite(depth_path, depth_colormap)
    print(f"✓ 深度画像（カラーマップ）を保存: {depth_path}")

    # 深度データ（生データ）の保存
    np.save(depth_raw_path, depth_image)
    print(f"✓ 深度データ（生データ）を保存: {depth_raw_path}")

    print(f"  → 保存先: {SAVE_DIR}\n")

def main():
    print("=" * 60)
    print("RealSense D405 深度データ可視化・画像保存")
    print("=" * 60)
    print(f"保存先ディレクトリ: {SAVE_DIR}")
    print("\n操作方法:")
    print("  's' キー: 現在のフレームを保存")
    print("  'q' キー: 終了")
    print("=" * 60)

    # パイプラインの設定
    pipeline = rs.pipeline()
    config = rs.config()

    # ストリームの設定
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

    # パイプラインの開始
    print("\nパイプラインを開始中...")
    profile = pipeline.start(config)

    # 深度スケールの取得
    depth_sensor = profile.get_device().first_depth_sensor()
    depth_scale = depth_sensor.get_depth_scale()
    print(f"✓ パイプライン開始成功! (深度スケール: {depth_scale})")
    print("\nウィンドウが表示されます...\n")

    # 最初の数フレームは安定しないのでスキップ
    for _ in range(10):
        pipeline.wait_for_frames()

    try:
        frame_count = 0
        saved_count = 0

        while True:
            # フレームの取得
            frames = pipeline.wait_for_frames()
            depth_frame = frames.get_depth_frame()
            color_frame = frames.get_color_frame()

            if not depth_frame or not color_frame:
                continue

            # NumPy 配列に変換
            depth_image = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())

            # 深度画像を可視化用にカラーマップ適用
            depth_colormap = cv2.applyColorMap(
                cv2.convertScaleAbs(depth_image, alpha=0.03),
                cv2.COLORMAP_JET
            )

            # 画像を横に並べて表示
            images = np.hstack((color_image, depth_colormap))

            # 画面中央の深度を取得して表示
            h, w = depth_image.shape
            center_depth = depth_image[h//2, w//2] * depth_scale

            # テキストオーバーレイ
            cv2.putText(images, f"Center Depth: {center_depth:.3f} m",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(images, "Press 's' to save, 'q' to quit",
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            # 画像を表示
            cv2.imshow('RealSense D405 - Color | Depth', images)

            # キー入力の処理
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                print("\n終了します...")
                break
            elif key == ord('s'):
                save_images(color_image, depth_image, depth_colormap)
                saved_count += 1

            frame_count += 1

    finally:
        # 後処理
        pipeline.stop()
        cv2.destroyAllWindows()
        print("\n" + "=" * 60)
        print(f"✓ セッション終了")
        print(f"  総フレーム数: {frame_count}")
        print(f"  保存した画像セット: {saved_count}")
        print("=" * 60)

if __name__ == "__main__":
    main()
