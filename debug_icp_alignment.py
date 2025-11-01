#!/usr/bin/env python3
"""
ICP位置合わせのデバッグ
"""

import numpy as np
import open3d as o3d
import sys
sys.path.insert(0, '/Users/moei/program/D405')

def debug_icp():
    """ICP位置合わせをデバッグ"""

    print("=" * 70)
    print("ICP位置合わせのデバッグ")
    print("=" * 70)

    # 1. データ読み込み
    print("\n[1] データ読み込み")

    depth = np.load("alignment_test/depth_raw_20251010_230711.npy")
    print(f"  Depth: {depth.shape}, 範囲: {depth.min():.1f} - {depth.max():.1f} mm")

    # 食品マスク
    h, w = depth.shape
    center_mask = np.zeros((h, w), dtype=bool)
    center_mask[h//4:3*h//4, w//4:3*w//4] = True
    valid_depth = (depth > 1800) & (depth < 2900)
    food_mask = center_mask & valid_depth

    # カメラパラメータ
    fx, fy, cx, cy = 424.0, 424.0, 424.0, 240.0

    # 深度点群生成
    v_coords, u_coords = np.where(food_mask)
    z = depth[v_coords, u_coords]
    x = (u_coords - cx) * z / fx
    y = (v_coords - cy) * z / fy
    depth_points = np.column_stack([x, y, z])

    print(f"  深度点群: {len(depth_points):,} points")
    print(f"  X範囲: {x.min():.1f} - {x.max():.1f} mm")
    print(f"  Y範囲: {y.min():.1f} - {y.max():.1f} mm")
    print(f"  Z範囲: {z.min():.1f} - {z.max():.1f} mm")

    # 2. お椀メッシュロード
    print("\n[2] お椀メッシュロード")

    bowl_mesh = o3d.io.read_triangle_mesh("data/mesh_output/001_bowl_mesh.ply")
    bowl_vertices = np.asarray(bowl_mesh.vertices)

    print(f"  お椀頂点: {len(bowl_vertices):,}")
    print(f"  X範囲: {bowl_vertices[:, 0].min():.1f} - {bowl_vertices[:, 0].max():.1f} mm")
    print(f"  Y範囲: {bowl_vertices[:, 1].min():.1f} - {bowl_vertices[:, 1].max():.1f} mm")
    print(f"  Z範囲: {bowl_vertices[:, 2].min():.1f} - {bowl_vertices[:, 2].max():.1f} mm")

    # 3. スケール比較
    print("\n[3] スケール比較")

    depth_size = np.array([x.max() - x.min(), y.max() - y.min(), z.max() - z.min()])
    bowl_size = np.array([
        bowl_vertices[:, 0].max() - bowl_vertices[:, 0].min(),
        bowl_vertices[:, 1].max() - bowl_vertices[:, 1].min(),
        bowl_vertices[:, 2].max() - bowl_vertices[:, 2].min()
    ])

    print(f"  深度点群サイズ: [{depth_size[0]:.1f}, {depth_size[1]:.1f}, {depth_size[2]:.1f}] mm")
    print(f"  お椀サイズ:     [{bowl_size[0]:.1f}, {bowl_size[1]:.1f}, {bowl_size[2]:.1f}] mm")
    print(f"  サイズ比: {depth_size / bowl_size}")

    # 4. 点群作成して可視化
    print("\n[4] 点群可視化準備")

    # 深度点群
    target_pcd = o3d.geometry.PointCloud()
    target_pcd.points = o3d.utility.Vector3dVector(depth_points)
    target_pcd.paint_uniform_color([1, 0, 0])  # 赤

    # お椀点群（サンプリング）
    bowl_pcd = bowl_mesh.sample_points_uniformly(number_of_points=10000)
    bowl_pcd.paint_uniform_color([0, 1, 0])  # 緑

    print(f"  深度点群: {len(target_pcd.points):,} (赤)")
    print(f"  お椀点群: {len(bowl_pcd.points):,} (緑)")

    # 座標軸
    coord_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=500, origin=[0, 0, 0])

    print("\n可視化ウィンドウを開きます...")
    print("  赤: 深度点群")
    print("  緑: お椀メッシュ")
    print("  RGB軸: 座標フレーム (500mm)")
    print("\nスケールと位置の問題を確認してください")

    o3d.visualization.draw_geometries(
        [target_pcd, bowl_pcd, coord_frame],
        window_name="ICP Alignment Debug",
        width=1200,
        height=800
    )

    # 5. スケール正規化してICPテスト
    print("\n" + "=" * 70)
    print("[5] スケール正規化してICPテスト")
    print("=" * 70)

    # 深度点群を中心に正規化
    depth_center = depth_points.mean(axis=0)
    depth_normalized = depth_points - depth_center
    depth_scale = np.max(np.abs(depth_normalized))
    depth_normalized /= depth_scale

    # お椀も正規化
    bowl_center = bowl_vertices.mean(axis=0)
    bowl_normalized = bowl_vertices - bowl_center
    bowl_scale = np.max(np.abs(bowl_normalized))
    bowl_normalized /= bowl_scale

    print(f"深度点群: center={depth_center}, scale={depth_scale:.2f}")
    print(f"お椀:     center={bowl_center}, scale={bowl_scale:.2f}")

    # 正規化後の点群でICP
    target_norm_pcd = o3d.geometry.PointCloud()
    target_norm_pcd.points = o3d.utility.Vector3dVector(depth_normalized)

    source_norm_pcd = o3d.geometry.PointCloud()
    source_norm_pcd.points = o3d.utility.Vector3dVector(bowl_normalized)

    # ダウンサンプリング
    target_down = target_norm_pcd.voxel_down_sample(0.01)
    source_down = source_norm_pcd.voxel_down_sample(0.01)

    print(f"\nダウンサンプリング後:")
    print(f"  target: {len(target_down.points):,}")
    print(f"  source: {len(source_down.points):,}")

    # 法線推定
    target_down.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.02, max_nn=30))
    source_down.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.02, max_nn=30))

    # ICP実行
    print("\nICP実行...")
    icp_result = o3d.pipelines.registration.registration_icp(
        source_down,
        target_down,
        max_correspondence_distance=0.05,
        init=np.eye(4),
        estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPlane(),
        criteria=o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=50)
    )

    print(f"  Fitness: {icp_result.fitness:.4f}")
    print(f"  RMSE: {icp_result.inlier_rmse:.4f}")

    if icp_result.fitness > 0.1:
        print("\n✅ ICP収束成功！")
    else:
        print("\n❌ ICP収束失敗")

    return {
        'depth_points': depth_points,
        'bowl_vertices': bowl_vertices,
        'icp_result': icp_result
    }


if __name__ == "__main__":
    result = debug_icp()
