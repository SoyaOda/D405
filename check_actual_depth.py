#!/usr/bin/env python3
"""
実際の深度測定値を確認するツール

カメラが測定している生の深度データを表示し、
定規測定値と比較します。
"""

import pyrealsense2 as rs
import numpy as np
import cv2

def main():
    print("=" * 70)
    print("深度測定確認ツール")
    print("=" * 70)
    print("定規で測定した距離を確認します")
    print("操作: 'q'キーで終了")
    print("=" * 70)

    # パイプライン設定
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)

    print("\nパイプライン開始...")
    profile = pipeline.start(config)

    # 深度スケール取得
    depth_sensor = profile.get_device().first_depth_sensor()
    depth_scale = depth_sensor.get_depth_scale()

    print(f"✓ 深度スケール: {depth_scale}")
    print(f"✓ 深度スケール (1/x): {1/depth_scale}")

    # ウォームアップ
    for _ in range(30):
        pipeline.wait_for_frames()

    print("\n✓ 準備完了")
    print("\n[情報]")
    print("  画面中央の深度を表示します")
    print("  ROI（緑の矩形）内の深度も表示します")
    print("=" * 70)

    try:
        while True:
            frames = pipeline.wait_for_frames()
            depth_frame = frames.get_depth_frame()
            color_frame = frames.get_color_frame()

            if not depth_frame or not color_frame:
                continue

            # 生データ取得（フィルターなし）
            depth_raw = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())

            # 深度カラーマップ
            depth_colormap = cv2.applyColorMap(
                cv2.convertScaleAbs(depth_raw, alpha=0.03),
                cv2.COLORMAP_JET
            )

            # 中央の深度
            h, w = depth_raw.shape
            center_depth_raw = depth_raw[h//2, w//2]
            center_depth_mm = center_depth_raw * depth_scale * 1000
            center_depth_m = center_depth_mm / 1000

            # ROI（左下20%x20%）の深度
            roi_x, roi_y = 0, int(h * 0.8)
            roi_w, roi_h = int(w * 0.2), int(h * 0.2)
            roi_region = depth_raw[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w]
            roi_valid = roi_region[roi_region > 0]

            if len(roi_valid) > 0:
                roi_median_raw = np.median(roi_valid)
                roi_median_mm = roi_median_raw * depth_scale * 1000
                roi_median_m = roi_median_mm / 1000
            else:
                roi_median_raw = 0
                roi_median_mm = 0
                roi_median_m = 0

            # ROI矩形を描画
            cv2.rectangle(depth_colormap, (roi_x, roi_y),
                         (roi_x+roi_w, roi_y+roi_h), (0, 255, 0), 2)

            # 横並び表示
            images = np.hstack([color_image, depth_colormap])

            # 情報表示
            cv2.putText(images, f"Center: {center_depth_mm:.1f}mm ({center_depth_m:.4f}m) [raw: {center_depth_raw}]",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(images, f"ROI: {roi_median_mm:.1f}mm ({roi_median_m:.4f}m) [raw: {roi_median_raw:.0f}]",
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(images, f"Depth Scale: {depth_scale}",
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(images, "Press 'q' to quit",
                       (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

            # ターミナルに出力
            print(f"\r中央: {center_depth_mm:6.1f}mm | ROI: {roi_median_mm:6.1f}mm | Raw値: 中央={center_depth_raw} ROI={roi_median_raw:.0f}", end='')

            cv2.imshow('Depth Check - Color | Depth', images)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n\n終了...")
                break

    finally:
        pipeline.stop()
        cv2.destroyAllWindows()

        print("\n" + "=" * 70)
        print("最終測定値:")
        print(f"  中央深度: {center_depth_mm:.1f}mm ({center_depth_m:.4f}m)")
        print(f"  ROI深度: {roi_median_mm:.1f}mm ({roi_median_m:.4f}m)")
        print(f"  深度スケール: {depth_scale}")
        print("=" * 70)

if __name__ == "__main__":
    main()
