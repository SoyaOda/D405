#!/usr/bin/env python3
"""
キャプチャしたRGBDデータでの体積推定テスト
"""

import numpy as np
import open3d as o3d
import cv2
import sys
sys.path.insert(0, '/Users/moei/program/D405')

from src.volume_calculation import VolumeCalculator
from src.bowl_fitting import BowlFitter


def test_captured_data():
    """キャプチャデータでテスト"""

    print("=" * 70)
    print("キャプチャデータでの体積推定テスト")
    print("=" * 70)

    # データパス
    base_path = "alignment_test/color_raw_20251010_230711"
    color_path = f"{base_path}.npy"
    depth_path = base_path.replace("color_raw", "depth_raw") + ".npy"

    bowl_mesh_path = "data/mesh_output/001_bowl_mesh.ply"
    bowl_real_diameter_mm = 165.0

    print(f"\nデータ:")
    print(f"  Color: {color_path}")
    print(f"  Depth: {depth_path}")
    print(f"  Bowl mesh: {bowl_mesh_path}")
    print(f"  Bowl diameter: {bowl_real_diameter_mm} mm")

    # 1. データ読み込み
    print("\n" + "=" * 70)
    print("[1] データ読み込み")
    print("=" * 70)

    try:
        color = np.load(color_path)
        depth = np.load(depth_path)
    except Exception as e:
        print(f"❌ データの読み込みに失敗: {e}")
        return None

    print(f"  Color: {color.shape}, dtype={color.dtype}")
    print(f"  Depth: {depth.shape}, dtype={depth.dtype}")
    print(f"  深度範囲: {depth.min():.1f} - {depth.max():.1f} mm")

    # 2. 簡易的な食品マスク作成
    print("\n" + "=" * 70)
    print("[2] 食品マスク作成")
    print("=" * 70)

    # 深度が有効な領域（中央付近、適度な深度）
    h, w = depth.shape

    # 中央領域
    center_mask = np.zeros((h, w), dtype=bool)
    cy_start, cy_end = h//4, 3*h//4
    cx_start, cx_end = w//4, 3*w//4
    center_mask[cy_start:cy_end, cx_start:cx_end] = True

    # 有効な深度範囲（データに合わせて調整）
    # 検査結果: 1871-2830mm, 中央値2364mm
    valid_depth = (depth > 1800) & (depth < 2900)

    # 組み合わせ
    food_mask = center_mask & valid_depth

    print(f"  食品ピクセル数: {food_mask.sum():,}")
    print(f"  画像全体: {depth.size:,}")
    print(f"  割合: {food_mask.sum()/depth.size*100:.1f}%")

    if food_mask.sum() < 100:
        print("⚠️ 食品ピクセルが少なすぎます")
        # より緩い条件
        food_mask = valid_depth
        print(f"  条件を緩和: {food_mask.sum():,} ピクセル")

    # 3. カメラ内部パラメータ（RealSense D405）
    camera_intrinsics = {
        'fx': 424.0,
        'fy': 424.0,
        'cx': 424.0,
        'cy': 240.0
    }

    # 4. お椀メッシュロードとICP
    print("\n" + "=" * 70)
    print("[3] お椀メッシュロードとICP")
    print("=" * 70)

    fitter = BowlFitter(
        bowl_model_path=bowl_mesh_path,
        bowl_real_diameter_mm=bowl_real_diameter_mm
    )

    # 深度画像から点群生成（食品領域のみ）
    print("\n深度画像から点群生成...")
    fx = camera_intrinsics['fx']
    fy = camera_intrinsics['fy']
    cx = camera_intrinsics['cx']
    cy = camera_intrinsics['cy']

    v_coords, u_coords = np.where(food_mask)
    z = depth[v_coords, u_coords]
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

    # 深度スケール: データが既にmm単位なので 1.0/1000 = 0.001
    result = calculator.calculate_volume_depth_difference(
        depth_image=depth.astype(np.uint16),
        food_mask=food_mask,
        bowl_mesh_aligned=bowl_mesh_aligned,
        camera_intrinsics=camera_intrinsics,
        depth_scale=0.001  # mm -> m
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
    print(f"  標準偏差: {result.get('std_height_mm', 0):.1f} mm")

    # ICP情報
    print(f"\nICP:")
    print(f"  Fitness: {icp_result['fitness']:.4f}")
    print(f"  RMSE: {icp_result['rmse']:.2f} mm")
    print(f"  Scale factor: {icp_result['scale_factor']:.4f}")
    print(f"  測定直径: {icp_result['measured_diameter_mm']:.1f} mm")

    # 可視化オプション
    try:
        visualize = input("\n可視化しますか？ (y/n): ").lower() == 'y'
        if visualize:
            # 深度点群
            target_pcd = o3d.geometry.PointCloud()
            target_pcd.points = o3d.utility.Vector3dVector(depth_points)
            target_pcd.paint_uniform_color([1, 0, 0])  # 赤

            # 位置合わせ済みお椀
            bowl_mesh_aligned.paint_uniform_color([0, 1, 0])  # 緑

            o3d.visualization.draw_geometries(
                [target_pcd, bowl_mesh_aligned],
                window_name="Volume Estimation Result",
                width=1024,
                height=768
            )
    except:
        pass

    return result


if __name__ == "__main__":
    print("キャプチャデータでの体積推定テスト")
    print("=" * 70)
    print("実際のRealSense D405キャプチャデータを使用")
    print("=" * 70)

    try:
        result = test_captured_data()

        if result:
            print("\n" + "=" * 70)
            print("✓ テスト完了")
            print("=" * 70)

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
