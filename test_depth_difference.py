#!/usr/bin/env python3
"""
深度差分積分法のテスト

お椀の3D形状を基準とした体積計算が正しく動作するか検証
"""

import numpy as np
import open3d as o3d
import sys
sys.path.insert(0, '/Users/moei/program/D405')

from src.volume_calculation import VolumeCalculator
from src.raycast_utils import validate_bowl_mesh


def create_synthetic_test_data():
    """
    テスト用の合成データを作成

    お椀（球の一部）と食品（円柱）をシミュレート
    """
    print("=" * 70)
    print("合成テストデータ作成")
    print("=" * 70)

    # 1. お椀メッシュ作成（半球）
    print("\n[1] お椀メッシュ作成")

    bowl_radius = 60.0  # mm
    bowl_center_z = 250.0  # カメラから250mm離す

    # 球を作成
    bowl_mesh = o3d.geometry.TriangleMesh.create_sphere(radius=bowl_radius, resolution=30)

    # 頂点を取得
    vertices = np.asarray(bowl_mesh.vertices)
    triangles = np.asarray(bowl_mesh.triangles)

    # 下半分のみ保持（お椀の形）
    # Z > 0の頂点のみ保持
    valid_vertex_mask = vertices[:, 2] > 0

    # 頂点インデックスマッピング作成
    old_to_new = -np.ones(len(vertices), dtype=int)
    valid_indices = np.where(valid_vertex_mask)[0]
    old_to_new[valid_indices] = np.arange(len(valid_indices))

    # 新しい頂点リスト
    new_vertices = vertices[valid_vertex_mask]

    # カメラから離す
    new_vertices[:, 2] += bowl_center_z

    # 有効な三角形のみ保持（3頂点すべてが有効）
    valid_triangles = []
    for tri in triangles:
        if all(valid_vertex_mask[tri]):
            new_tri = [old_to_new[v] for v in tri]
            valid_triangles.append(new_tri)

    # 新しいメッシュ作成
    bowl_mesh = o3d.geometry.TriangleMesh()
    bowl_mesh.vertices = o3d.utility.Vector3dVector(new_vertices)
    bowl_mesh.triangles = o3d.utility.Vector3iVector(valid_triangles)
    bowl_mesh.compute_vertex_normals()

    print(f"  お椀半径: {bowl_radius} mm")
    print(f"  中心Z座標: {bowl_center_z} mm")
    print(f"  頂点数: {len(bowl_mesh.vertices):,}")
    print(f"  面数: {len(bowl_mesh.triangles):,}")

    # メッシュ品質確認
    validation = validate_bowl_mesh(bowl_mesh)
    print(f"\nお椀メッシュ品質:")
    print(f"  有効: {validation['is_valid']}")
    if validation['issues']:
        print(f"  問題: {', '.join(validation['issues'])}")

    # 2. 深度画像作成（お椀 + 食品）
    print("\n[2] 合成深度画像作成")

    h, w = 480, 848
    depth_image = np.zeros((h, w), dtype=np.uint16)

    # カメラ内部パラメータ
    camera_intrinsics = {
        'fx': 424.0,
        'fy': 424.0,
        'cx': 424.0,
        'cy': 240.0
    }

    # 食品領域（中心の円形領域）
    food_radius_px = 80  # ピクセル単位
    center_u, center_v = 424, 240

    food_mask = np.zeros((h, w), dtype=bool)

    # 食品の高さ（お椀の底から）
    food_height_mm = 30.0  # mm

    for v in range(h):
        for u in range(w):
            # 中心からの距離
            dist = np.sqrt((u - center_u)**2 + (v - center_v)**2)

            if dist < food_radius_px:
                # 食品領域
                food_mask[v, u] = True

                # 食品表面の深度（お椀底面 - 食品高さ）
                # お椀底面 ≈ 250mm（中心）
                # 食品は底から30mm上
                food_depth_m = (bowl_center_z - food_height_mm) / 1000.0

                # Nutrition5k形式（10,000 units/m）
                depth_image[v, u] = int(food_depth_m * 10000)

    print(f"  画像サイズ: {w} x {h}")
    print(f"  食品ピクセル: {food_mask.sum():,}")
    print(f"  食品高さ: {food_height_mm} mm")
    print(f"  深度範囲: {depth_image[food_mask].min()} - {depth_image[food_mask].max()} units")

    # 理論体積（円柱）
    food_radius_mm = food_radius_px * ((bowl_center_z - food_height_mm) / camera_intrinsics['fx'])
    theoretical_volume_ml = np.pi * food_radius_mm**2 * food_height_mm / 1000

    print(f"\n[3] 理論値")
    print(f"  食品半径: {food_radius_mm:.1f} mm")
    print(f"  食品高さ: {food_height_mm} mm")
    print(f"  理論体積: {theoretical_volume_ml:.1f} ml")

    return {
        'bowl_mesh': bowl_mesh,
        'depth_image': depth_image,
        'food_mask': food_mask,
        'camera_intrinsics': camera_intrinsics,
        'theoretical_volume_ml': theoretical_volume_ml,
        'food_height_mm': food_height_mm
    }


def test_depth_difference_method():
    """深度差分積分法のテスト"""

    print("\n" + "=" * 70)
    print("深度差分積分法テスト")
    print("=" * 70)

    # 1. 合成データ作成
    test_data = create_synthetic_test_data()

    bowl_mesh = test_data['bowl_mesh']
    depth_image = test_data['depth_image']
    food_mask = test_data['food_mask']
    camera_intrinsics = test_data['camera_intrinsics']
    theoretical_volume_ml = test_data['theoretical_volume_ml']

    # 2. VolumeCalculator初期化
    calculator = VolumeCalculator(voxel_size_mm=1.0)

    # 3. 深度差分積分法で体積計算
    print("\n" + "=" * 70)
    print("体積計算実行")
    print("=" * 70)

    result = calculator.calculate_volume_depth_difference(
        depth_image=depth_image,
        food_mask=food_mask,
        bowl_mesh_aligned=bowl_mesh,
        camera_intrinsics=camera_intrinsics,
        depth_scale=0.0001  # Nutrition5k形式
    )

    # 4. 結果比較
    print("\n" + "=" * 70)
    print("結果比較")
    print("=" * 70)

    calculated_volume_ml = result['volume_ml']
    error_ml = abs(calculated_volume_ml - theoretical_volume_ml)
    error_percent = (error_ml / theoretical_volume_ml) * 100

    print(f"\n理論値:   {theoretical_volume_ml:.1f} ml")
    print(f"計算値:   {calculated_volume_ml:.1f} ml")
    print(f"誤差:     {error_ml:.1f} ml ({error_percent:.1f}%)")

    # 5. 詳細統計
    print(f"\n詳細:")
    print(f"  総ピクセル数: {result['num_pixels']:,}")
    print(f"  有効ピクセル: {result['num_valid_pixels']:,}")
    print(f"  有効率: {result['num_valid_pixels']/result['num_pixels']*100:.1f}%")
    print(f"  平均高さ: {result['mean_height_mm']:.1f} mm")
    print(f"  最大高さ: {result['max_height_mm']:.1f} mm")
    print(f"  最小高さ: {result['min_height_mm']:.1f} mm")
    print(f"  標準偏差: {result['std_height_mm']:.1f} mm")

    # 6. 評価
    print("\n" + "=" * 70)
    print("評価")
    print("=" * 70)

    if error_percent < 5:
        print(f"✅ 優秀: 誤差 {error_percent:.1f}% < 5%")
    elif error_percent < 10:
        print(f"✅ 良好: 誤差 {error_percent:.1f}% < 10%")
    elif error_percent < 20:
        print(f"⚠️ 許容: 誤差 {error_percent:.1f}% < 20%")
    else:
        print(f"❌ 要改善: 誤差 {error_percent:.1f}% >= 20%")

    # 7. 可視化（オプション）
    try:
        visualize = input("\nメッシュを可視化しますか？ (y/n): ").lower() == 'y'
        if visualize:
            bowl_mesh.paint_uniform_color([0.7, 0.7, 0.7])
            o3d.visualization.draw_geometries(
                [bowl_mesh],
                window_name="Test Bowl Mesh",
                width=800,
                height=600
            )
    except:
        pass

    return result, theoretical_volume_ml


if __name__ == "__main__":
    print("深度差分積分法 実装テスト")
    print("=" * 70)
    print("このテストでは:")
    print("  1. 合成お椀メッシュ（半球）を作成")
    print("  2. 合成食品（円柱、高さ30mm）を配置")
    print("  3. 深度差分積分法で体積を計算")
    print("  4. 理論値と比較")
    print("=" * 70)

    try:
        result, theoretical = test_depth_difference_method()

        print("\n" + "=" * 70)
        print("✓ テスト完了")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
