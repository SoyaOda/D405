#!/usr/bin/env python3
"""
新しくスキャンした001お椀データでの体積推定テスト
"""

import numpy as np
import open3d as o3d
import cv2
import json
import sys
sys.path.insert(0, '/Users/moei/program/D405')

from src.volume_calculation import VolumeCalculator
from src.bowl_fitting import BowlFitter


def test_new_scan():
    """新スキャンデータでテスト"""

    print("=" * 70)
    print("新スキャンデータでの体積推定テスト")
    print("=" * 70)

    # データパス（最新）
    base_dir = "nutrition5k_data/imagery/realsense_overhead"
    timestamp = "20251101_121028"
    rgb_path = f"{base_dir}/rgb_test_food_{timestamp}.png"
    depth_path = f"{base_dir}/depth_raw_test_food_{timestamp}.png"
    metadata_path = f"{base_dir}/metadata_test_food_{timestamp}.json"

    bowl_mesh_path = "data/mesh_output/001_bowl_mesh.ply"
    bowl_real_diameter_mm = 165.0

    print(f"\nデータ:")
    print(f"  RGB: {rgb_path}")
    print(f"  Depth: {depth_path}")
    print(f"  Metadata: {metadata_path}")
    print(f"  Bowl mesh: {bowl_mesh_path}")
    print(f"  Bowl diameter: {bowl_real_diameter_mm} mm")

    # 1. データ読み込み
    print("\n" + "=" * 70)
    print("[1] データ読み込み")
    print("=" * 70)

    rgb = cv2.imread(rgb_path)
    depth_raw = cv2.imread(depth_path, cv2.IMREAD_UNCHANGED)

    with open(metadata_path) as f:
        metadata = json.load(f)

    # Nutrition5k形式: 10000 units/meter = 0.0001 m/unit
    depth_scale = 0.0001  # m/unit
    print(f"  RGB: {rgb.shape}")
    print(f"  Depth: {depth_raw.shape}, dtype={depth_raw.dtype}")
    print(f"  Depth encoding: {metadata.get('depth_encoding', 'Unknown')}")
    print(f"  Depth scale: {depth_scale} (m/unit)")
    print(f"  深度範囲: {depth_raw.min()} - {depth_raw.max()} units")
    print(f"  深度範囲(mm): {depth_raw.min()*depth_scale*1000:.1f} - {depth_raw.max()*depth_scale*1000:.1f} mm")

    # 深度をmm単位に変換
    depth_mm = (depth_raw * depth_scale * 1000).astype(np.float32)

    # 2. 食品マスク作成
    print("\n" + "=" * 70)
    print("[2] 食品マスク作成")
    print("=" * 70)

    # 有効な深度範囲（お椀が見える範囲）
    valid_depth = (depth_mm > 100) & (depth_mm < 400)

    # 中央領域
    h, w = depth_mm.shape
    center_mask = np.zeros((h, w), dtype=bool)
    center_mask[h//6:5*h//6, w//6:5*w//6] = True

    food_mask = valid_depth & center_mask

    print(f"  食品ピクセル数: {food_mask.sum():,}")
    print(f"  画像全体: {depth_mm.size:,}")
    print(f"  割合: {food_mask.sum()/depth_mm.size*100:.1f}%")

    if food_mask.sum() < 1000:
        print("⚠️ 食品ピクセルが少なすぎます、条件を緩和")
        food_mask = valid_depth
        print(f"  緩和後: {food_mask.sum():,} ピクセル")

    # 3. カメラ内部パラメータ（RealSense D405デフォルト値）
    camera_intrinsics = {
        'fx': 424.0,
        'fy': 424.0,
        'cx': 424.0,
        'cy': 240.0
    }

    print(f"\nカメラ内部パラメータ (RealSense D405):")
    print(f"  fx={camera_intrinsics['fx']:.1f}, fy={camera_intrinsics['fy']:.1f}")
    print(f"  cx={camera_intrinsics['cx']:.1f}, cy={camera_intrinsics['cy']:.1f}")

    # 4. お椀メッシュロードとICP
    print("\n" + "=" * 70)
    print("[3] お椀メッシュロードとICP")
    print("=" * 70)

    fitter = BowlFitter(
        bowl_model_path=bowl_mesh_path,
        bowl_real_diameter_mm=bowl_real_diameter_mm
    )

    # 深度画像から点群生成
    print("\n深度画像から点群生成...")
    fx = camera_intrinsics['fx']
    fy = camera_intrinsics['fy']
    cx = camera_intrinsics['cx']
    cy = camera_intrinsics['cy']

    v_coords, u_coords = np.where(food_mask)
    z = depth_mm[v_coords, u_coords]
    x = (u_coords - cx) * z / fx
    y = (v_coords - cy) * z / fy
    depth_points = np.column_stack([x, y, z])

    print(f"  点群数: {len(depth_points):,}")
    print(f"  X範囲: {x.min():.1f} - {x.max():.1f} mm")
    print(f"  Y範囲: {y.min():.1f} - {y.max():.1f} mm")
    print(f"  Z範囲: {z.min():.1f} - {z.max():.1f} mm")

    # ICP実行
    print("\nICP実行...")
    icp_result = fitter.fit_to_depth_points(
        depth_points,
        max_iterations=100,
        voxel_size=2.0
    )

    bowl_mesh_aligned = o3d.geometry.TriangleMesh(fitter.bowl_mesh)
    bowl_mesh_aligned.transform(icp_result['transformation'])

    # 5. 深度差分積分法で体積計算
    print("\n" + "=" * 70)
    print("[4] 体積計算（深度差分積分法）")
    print("=" * 70)

    calculator = VolumeCalculator(voxel_size_mm=1.0)

    # depth_rawを使用（units単位）
    result = calculator.calculate_volume_depth_difference(
        depth_image=depth_raw,
        food_mask=food_mask,
        bowl_mesh_aligned=bowl_mesh_aligned,
        camera_intrinsics=camera_intrinsics,
        depth_scale=depth_scale  # units -> m
    )

    # 6. 結果表示
    print("\n" + "=" * 70)
    print("結果")
    print("=" * 70)

    print(f"\n📊 体積: {result['volume_ml']:.1f} ml")
    print(f"\n詳細:")
    print(f"  総ピクセル数: {result['num_pixels']:,}")
    print(f"  有効ピクセル: {result['num_valid_pixels']:,}")
    print(f"  有効率: {result['num_valid_pixels']/result['num_pixels']*100:.1f}%")
    print(f"  平均高さ: {result['mean_height_mm']:.1f} mm")
    print(f"  最大高さ: {result['max_height_mm']:.1f} mm")
    print(f"  最小高さ: {result['min_height_mm']:.1f} mm")
    print(f"  標準偏差: {result.get('std_height_mm', 0):.1f} mm")

    # ICP情報
    print(f"\nICP:")
    print(f"  Fitness: {icp_result['fitness']:.4f}")
    print(f"  RMSE: {icp_result['rmse']:.2f} mm")
    print(f"  Scale factor: {icp_result['scale_factor']:.4f}")
    print(f"  測定直径: {icp_result['measured_diameter_mm']:.1f} mm")
    print(f"  実寸直径: {bowl_real_diameter_mm:.1f} mm")

    # 評価
    print("\n" + "=" * 70)
    print("評価")
    print("=" * 70)

    if icp_result['fitness'] > 0.3:
        print(f"✅ ICP収束: 良好 (Fitness {icp_result['fitness']:.3f} > 0.3)")
    elif icp_result['fitness'] > 0.1:
        print(f"⚠️ ICP収束: 許容 (Fitness {icp_result['fitness']:.3f})")
    else:
        print(f"❌ ICP収束: 失敗 (Fitness {icp_result['fitness']:.3f} < 0.1)")

    if result['num_valid_pixels'] / result['num_pixels'] > 0.5:
        print(f"✅ 有効ピクセル率: 良好 ({result['num_valid_pixels']/result['num_pixels']*100:.1f}% > 50%)")
    else:
        print(f"⚠️ 有効ピクセル率: 低い ({result['num_valid_pixels']/result['num_pixels']*100:.1f}% < 50%)")

    # 可視化オプション
    try:
        visualize = input("\n可視化しますか？ (y/n): ").lower() == 'y'
        if visualize:
            # 深度点群
            target_pcd = o3d.geometry.PointCloud()
            target_pcd.points = o3d.utility.Vector3dVector(depth_points)
            target_pcd.paint_uniform_color([1, 0, 0])  # 赤

            # 位置合わせ済みお椀（緑）
            bowl_mesh_aligned.paint_uniform_color([0, 1, 0])

            # 座標軸
            coord_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(
                size=100, origin=[0, 0, 0]
            )

            print("\n可視化:")
            print("  赤: 深度点群（食品領域）")
            print("  緑: 位置合わせ済みお椀メッシュ")
            print("  RGB軸: 座標フレーム (100mm)")

            o3d.visualization.draw_geometries(
                [target_pcd, bowl_mesh_aligned, coord_frame],
                window_name="Volume Estimation Result",
                width=1200,
                height=800
            )
    except:
        pass

    return result, icp_result


if __name__ == "__main__":
    print("新スキャンデータでの体積推定テスト")
    print("=" * 70)
    print("001お椀を使用した最新スキャンデータ")
    print("=" * 70)

    try:
        result, icp_result = test_new_scan()

        print("\n" + "=" * 70)
        print("✓ テスト完了")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
