#!/usr/bin/env python3
"""
RealSense D405 カメラ情報確認スクリプト

intrinsics（内部パラメータ）とFOVを確認
"""

import pyrealsense2 as rs
import math

def print_intrinsics(intrinsics, label):
    """Intrinsicsを表示"""
    print(f"\n[{label}]")
    print(f"  解像度: {intrinsics.width} x {intrinsics.height}")
    print(f"  焦点距離 (fx, fy): ({intrinsics.fx:.2f}, {intrinsics.fy:.2f})")
    print(f"  主点 (ppx, ppy): ({intrinsics.ppx:.2f}, {intrinsics.ppy:.2f})")
    print(f"  歪み係数: {intrinsics.coeffs}")

    # FOV計算
    fov_x = 2 * math.atan(intrinsics.width / (2 * intrinsics.fx)) * 180 / math.pi
    fov_y = 2 * math.atan(intrinsics.height / (2 * intrinsics.fy)) * 180 / math.pi
    print(f"  FOV (計算値): {fov_x:.1f}° x {fov_y:.1f}°")

def main():
    print("=" * 70)
    print("RealSense D405 カメラ情報確認")
    print("=" * 70)

    pipeline = rs.pipeline()
    config = rs.config()

    # 複数の解像度をテスト
    resolutions = [
        (640, 480),
        (640, 360),
        (1280, 720),
    ]

    for width, height in resolutions:
        print(f"\n{'=' * 70}")
        print(f"解像度テスト: {width}x{height}")
        print(f"{'=' * 70}")

        try:
            config.enable_stream(rs.stream.depth, width, height, rs.format.z16, 30)
            config.enable_stream(rs.stream.color, width, height, rs.format.bgr8, 30)

            profile = pipeline.start(config)

            # Depth intrinsics
            depth_profile = profile.get_stream(rs.stream.depth).as_video_stream_profile()
            depth_intrinsics = depth_profile.get_intrinsics()
            print_intrinsics(depth_intrinsics, "深度カメラ Intrinsics")

            # Color intrinsics
            color_profile = profile.get_stream(rs.stream.color).as_video_stream_profile()
            color_intrinsics = color_profile.get_intrinsics()
            print_intrinsics(color_intrinsics, "カラーカメラ Intrinsics")

            # Extrinsics（カメラ間の位置関係）
            depth_to_color = depth_profile.get_extrinsics_to(color_profile)
            print(f"\n[深度→カラー Extrinsics]")
            print(f"  平行移動: {depth_to_color.translation}")
            print(f"  回転: {depth_to_color.rotation}")

            pipeline.stop()
            config.disable_all_streams()

        except Exception as e:
            print(f"  エラー: {e}")
            try:
                pipeline.stop()
            except:
                pass
            config.disable_all_streams()

    print("\n" + "=" * 70)
    print("確認完了")
    print("=" * 70)

if __name__ == "__main__":
    main()
