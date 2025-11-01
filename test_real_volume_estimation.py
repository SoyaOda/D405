#!/usr/bin/env python3
"""
実際のRGBDデータでの体積推定テスト

Nutrition5kデータセットを使用して深度差分積分法を検証
"""

import numpy as np
import open3d as o3d
import cv2
import sys
sys.path.insert(0, '/Users/moei/program/D405')

from src.volume_calculation import VolumeCalculator
from src.bowl_fitting import BowlFitter


def test_real_rgbd_data():
    """実際のRGBDデータでテスト"""

    print("=" * 70)
    print("実際のRGBDデータでの体積推定テスト")
    print("=" * 70)

    # データパス
    dish_id = "plate_noodle_salad_beet_cheese"
    rgb_path = f"nutrition5k_data/imagery/realsense_overhead/dish_ids/{dish_id}/rgb.png"
    depth_path = f"nutrition5k_data/imagery/realsense_overhead/dish_ids/{dish_id}/depth.png"

    bowl_mesh_path = "data/mesh_output/001_bowl_mesh.ply"
    bowl_real_diameter_mm = 165.0

    print(f"\nデータ:")
    print(f"  RGB: {rgb_path}")
    print(f"  Depth: {depth_path}")
    print(f"  Bowl mesh: {bowl_mesh_path}")
    print(f"  Bowl diameter: {bowl_real_diameter_mm} mm")

    # 1. 画像読み込み
    print("\n" + "=" * 70)
    print("[1] 画像読み込み")
    print("=" * 70)

    rgb = cv2.imread(rgb_path)
    depth = cv2.imread(depth_path, cv2.IMREAD_UNCHANGED)

    if rgb is None or depth is None:
        print(f"❌ 画像の読み込みに失敗")
        return None

    print(f"  RGB: {rgb.shape}")
    print(f"  Depth: {depth.shape}, dtype={depth.dtype}")
    print(f"  深度範囲: {depth.min()} - {depth.max()} units")
    print(f"  深度範囲(m): {depth.min()*0.0001:.3f} - {depth.max()*0.0001:.3f} m")

    # 2. 簡易的な食品マスク作成（深度が有効な領域）
    print("\n" + "=" * 70)
    print("[2] 食品マスク作成")
    print("=" * 70)

    # 深度が有効な領域（0でない）
    food_mask = (depth > 0) & (depth < 4000)  # 0.4m以下

    print(f"  食品ピクセル数: {food_mask.sum():,}")
    print(f"  画像全体: {depth.size:,}")
    print(f"  割合: {food_mask.sum()/depth.size*100:.1f}%")

    # 3. カメラ内部パラメータ（RealSense D405）
    camera_intrinsics = {
        'fx': 424.0,
        'fy': 424.0,
        'cx': 424.0,
        'cy': 240.0
    }

    # 4. お椀メッシュロード
    print("\n" + "=" * 70)
    print("[3] お椀メッシュロードとICP")
    print("=" * 70)

    # BowlFitter使用
    fitter = BowlFitter(
        bowl_model_path=bowl_mesh_path,
        bowl_real_diameter_mm=bowl_real_diameter_mm
    )

    # 深度画像から点群生成（食品領域のみ）
    print("\n深度画像から点群生成...")
    h, w = depth.shape
    fx = camera_intrinsics['fx']
    fy = camera_intrinsics['fy']
    cx = camera_intrinsics['cx']
    cy = camera_intrinsics['cy']

    v_coords, u_coords = np.where(food_mask)
    z = depth[v_coords, u_coords] * 0.0001 * 1000  # units -> m -> mm
    x = (u_coords - cx) * z / fx
    y = (v_coords - cy) * z / fy
    depth_points = np.column_stack([x, y, z])

    print(f"  点群数: {len(depth_points):,}")
    print(f"  Z範囲: {z.min():.1f} - {z.max():.1f} mm")

    # ICP実行
    print("\nICP実行...")
    icp_result = fitter.fit_to_depth_points(
        depth_points,
        max_iterations=50,
        voxel_size=2.0
    )

    bowl_mesh_aligned = o3d.geometry.TriangleMesh(fitter.bowl_mesh)
    bowl_mesh_aligned.transform(icp_result['transformation'])

    # 5. 深度差分積分法で体積計算
    print("\n" + "=" * 70)
    print("[4] 体積計算（深度差分積分法）")
    print("=" * 70)

    calculator = VolumeCalculator(voxel_size_mm=1.0)

    result = calculator.calculate_volume_depth_difference(
        depth_image=depth,
        food_mask=food_mask,
        bowl_mesh_aligned=bowl_mesh_aligned,
        camera_intrinsics=camera_intrinsics,
        depth_scale=0.0001  # Nutrition5k形式
    )

    # 6. 結果表示
    print("\n" + "=" * 70)
    print("結果")
    print("=" * 70)

    print(f"\n体積: {result['volume_ml']:.1f} ml")
    print(f"\n詳細:")
    print(f"  総ピクセル数: {result['num_pixels']:,}")
    print(f"  有効ピクセル: {result['num_valid_pixels']:,}")
    print(f"  有効率: {result['num_valid_pixels']/result['num_pixels']*100:.1f}%")
    print(f"  平均高さ: {result['mean_height_mm']:.1f} mm")
    print(f"  最大高さ: {result['max_height_mm']:.1f} mm")
    print(f"  最小高さ: {result['min_height_mm']:.1f} mm")

    # ICP情報
    print(f"\nICP:")
    print(f"  Fitness: {icp_result['fitness']:.4f}")
    print(f"  RMSE: {icp_result['rmse']:.2f} mm")
    print(f"  Scale factor: {icp_result['scale_factor']:.4f}")

    return result


if __name__ == "__main__":
    print("実際のRGBDデータでの体積推定テスト")
    print("=" * 70)
    print("Nutrition5kデータセットを使用")
    print("=" * 70)

    try:
        result = test_real_rgbd_data()

        if result:
            print("\n" + "=" * 70)
            print("✓ テスト完了")
            print("=" * 70)

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
