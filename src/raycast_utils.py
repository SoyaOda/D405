#!/usr/bin/env python3
"""
Raycasting Utilities for Bowl Surface Distance Calculation

お椀の3D形状を使用した深度差分積分法のための
レイキャスティング機能を提供します。
"""

import numpy as np
import open3d as o3d
from typing import Dict, Tuple


def raycast_bowl_surface(
    bowl_mesh_aligned: o3d.geometry.TriangleMesh,
    pixel_coords: np.ndarray,
    camera_intrinsics: Dict,
    verbose: bool = False
) -> Tuple[np.ndarray, np.ndarray]:
    """
    各ピクセルに対してお椀底面までの距離を計算（レイキャスティング）

    Args:
        bowl_mesh_aligned: ICPで位置合わせ済みのお椀メッシュ
        pixel_coords: ピクセル座標 (N, 2) [u, v]
        camera_intrinsics: カメラ内部パラメータ {fx, fy, cx, cy}
        verbose: 詳細ログを出力するか

    Returns:
        bowl_depths: お椀底面までの距離 (N,) mm単位
        hit_mask: レイがメッシュに当たったかどうか (N,) bool
    """
    if verbose:
        print(f"\nレイキャスティング実行中...")
        print(f"  ピクセル数: {len(pixel_coords):,}")

    fx = camera_intrinsics['fx']
    fy = camera_intrinsics['fy']
    cx = camera_intrinsics['cx']
    cy = camera_intrinsics['cy']

    # Open3D tensor geometryに変換
    mesh_t = o3d.t.geometry.TriangleMesh.from_legacy(bowl_mesh_aligned)

    # RaycastingScene作成
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(mesh_t)

    # レイの生成
    N = len(pixel_coords)
    rays = np.zeros((N, 6), dtype=np.float32)

    for i, (u, v) in enumerate(pixel_coords):
        # カメラ原点
        rays[i, :3] = [0, 0, 0]

        # レイ方向ベクトル（カメラ座標系）
        # ピンホールカメラモデル: (u, v) -> 3D方向
        x = (u - cx) / fx
        y = (v - cy) / fy
        z = 1.0

        # 正規化
        norm = np.sqrt(x**2 + y**2 + z**2)
        rays[i, 3:6] = [x/norm, y/norm, z/norm]

    # レイキャスト実行
    rays_tensor = o3d.core.Tensor(rays, dtype=o3d.core.Dtype.Float32)
    result = scene.cast_rays(rays_tensor)

    # 交点までの距離（t_hit）
    bowl_depths = result['t_hit'].numpy()

    # ヒット判定（無限大 = ミス）
    hit_mask = bowl_depths < 1e10
    bowl_depths[~hit_mask] = 0

    if verbose:
        hit_rate = hit_mask.sum() / N * 100
        print(f"  ヒット率: {hit_rate:.1f}% ({hit_mask.sum():,} / {N:,})")
        if hit_mask.sum() > 0:
            valid_depths = bowl_depths[hit_mask]
            print(f"  距離範囲: {valid_depths.min():.1f} - {valid_depths.max():.1f} mm")
            print(f"  平均距離: {valid_depths.mean():.1f} mm")

    return bowl_depths, hit_mask


def create_ray_from_pixel(
    u: int,
    v: int,
    camera_intrinsics: Dict
) -> Tuple[np.ndarray, np.ndarray]:
    """
    ピクセル座標からカメラレイを生成

    Args:
        u: ピクセルのx座標
        v: ピクセルのy座標
        camera_intrinsics: カメラ内部パラメータ

    Returns:
        ray_origin: レイの始点 (3,)
        ray_direction: レイの方向（正規化済み） (3,)
    """
    fx = camera_intrinsics['fx']
    fy = camera_intrinsics['fy']
    cx = camera_intrinsics['cx']
    cy = camera_intrinsics['cy']

    # カメラ原点
    ray_origin = np.array([0.0, 0.0, 0.0])

    # レイ方向（ピンホールカメラモデル）
    x = (u - cx) / fx
    y = (v - cy) / fy
    z = 1.0

    ray_direction = np.array([x, y, z])
    ray_direction = ray_direction / np.linalg.norm(ray_direction)

    return ray_origin, ray_direction


def compute_pixel_area(
    depth_mm: float,
    camera_intrinsics: Dict
) -> float:
    """
    深度に応じたピクセルの実面積を計算

    Args:
        depth_mm: 深度（mm単位）
        camera_intrinsics: カメラ内部パラメータ

    Returns:
        pixel_area_mm2: ピクセル面積（mm²）
    """
    fx = camera_intrinsics['fx']

    # ピクセル面積は深度の2乗に比例
    # A = (D / f)²
    pixel_area_mm2 = (depth_mm / fx) ** 2

    return pixel_area_mm2


def validate_bowl_mesh(bowl_mesh: o3d.geometry.TriangleMesh) -> Dict:
    """
    お椀メッシュの品質を検証

    Args:
        bowl_mesh: お椀メッシュ

    Returns:
        validation_result: {
            'is_valid': bool,
            'num_vertices': int,
            'num_triangles': int,
            'is_watertight': bool,
            'has_normals': bool,
            'issues': List[str]
        }
    """
    issues = []

    num_vertices = len(bowl_mesh.vertices)
    num_triangles = len(bowl_mesh.triangles)

    if num_vertices == 0:
        issues.append("頂点データなし")

    if num_triangles == 0:
        issues.append("面データなし")

    is_watertight = bowl_mesh.is_watertight()
    if not is_watertight:
        issues.append("Watertightでない（穴がある可能性）")

    has_normals = bowl_mesh.has_vertex_normals()
    if not has_normals:
        issues.append("法線データなし")

    # 退化三角形チェック
    mesh_clean = bowl_mesh.remove_degenerate_triangles()
    num_removed = num_triangles - len(mesh_clean.triangles)
    if num_removed > 0:
        issues.append(f"退化三角形: {num_removed}個")

    is_valid = len(issues) == 0

    return {
        'is_valid': is_valid,
        'num_vertices': num_vertices,
        'num_triangles': num_triangles,
        'is_watertight': is_watertight,
        'has_normals': has_normals,
        'issues': issues
    }


def visualize_raycasting_result(
    bowl_mesh_aligned: o3d.geometry.TriangleMesh,
    pixel_coords: np.ndarray,
    bowl_depths: np.ndarray,
    hit_mask: np.ndarray,
    camera_intrinsics: Dict,
    num_samples: int = 100
):
    """
    レイキャスティング結果を3D可視化

    Args:
        bowl_mesh_aligned: お椀メッシュ
        pixel_coords: ピクセル座標
        bowl_depths: お椀底面までの距離
        hit_mask: ヒット判定
        camera_intrinsics: カメラ内部パラメータ
        num_samples: 可視化するレイの数
    """
    geometries = []

    # お椀メッシュ（グレー）
    mesh_vis = o3d.geometry.TriangleMesh(bowl_mesh_aligned)
    mesh_vis.paint_uniform_color([0.7, 0.7, 0.7])
    mesh_vis.compute_vertex_normals()
    geometries.append(mesh_vis)

    # カメラ原点（赤）
    camera_sphere = o3d.geometry.TriangleMesh.create_sphere(radius=5.0)
    camera_sphere.paint_uniform_color([1, 0, 0])
    geometries.append(camera_sphere)

    # サンプリング
    hit_indices = np.where(hit_mask)[0]
    if len(hit_indices) > num_samples:
        sample_indices = np.random.choice(hit_indices, num_samples, replace=False)
    else:
        sample_indices = hit_indices

    # レイを可視化
    for idx in sample_indices:
        u, v = pixel_coords[idx]
        depth = bowl_depths[idx]

        ray_origin, ray_direction = create_ray_from_pixel(u, v, camera_intrinsics)
        ray_end = ray_origin + ray_direction * depth

        # ライン作成
        line_set = o3d.geometry.LineSet()
        line_set.points = o3d.utility.Vector3dVector([ray_origin, ray_end])
        line_set.lines = o3d.utility.Vector2iVector([[0, 1]])
        line_set.colors = o3d.utility.Vector3dVector([[0, 1, 0]])  # 緑
        geometries.append(line_set)

        # 交点（青）
        point_sphere = o3d.geometry.TriangleMesh.create_sphere(radius=1.0)
        point_sphere.paint_uniform_color([0, 0, 1])
        point_sphere.translate(ray_end)
        geometries.append(point_sphere)

    print(f"\n可視化: {len(sample_indices)}本のレイを表示")
    print("  赤: カメラ原点")
    print("  緑: レイ")
    print("  青: お椀表面との交点")
    print("  グレー: お椀メッシュ")

    o3d.visualization.draw_geometries(
        geometries,
        window_name="Raycasting Result",
        width=1200,
        height=800
    )


if __name__ == "__main__":
    # テスト用サンプル
    print("レイキャスティングユーティリティのテスト")

    # ダミーメッシュ作成（球）
    test_mesh = o3d.geometry.TriangleMesh.create_sphere(radius=50.0)
    test_mesh.translate([0, 0, 200])  # カメラから200mm離す
    test_mesh.compute_vertex_normals()

    # ダミーカメラ内部パラメータ
    camera_intrinsics = {
        'fx': 424.0,
        'fy': 424.0,
        'cx': 424.0,
        'cy': 240.0
    }

    # テスト用ピクセル座標（中心付近）
    pixel_coords = np.array([
        [424, 240],  # 中心
        [424, 250],
        [434, 240],
        [414, 240],
        [424, 230]
    ])

    # レイキャスト実行
    bowl_depths, hit_mask = raycast_bowl_surface(
        test_mesh,
        pixel_coords,
        camera_intrinsics,
        verbose=True
    )

    print(f"\n結果:")
    for i, (u, v) in enumerate(pixel_coords):
        if hit_mask[i]:
            print(f"  Pixel ({u}, {v}): {bowl_depths[i]:.2f} mm")
        else:
            print(f"  Pixel ({u}, {v}): ミス")

    # メッシュ品質検証
    validation = validate_bowl_mesh(test_mesh)
    print(f"\nメッシュ品質:")
    print(f"  有効: {validation['is_valid']}")
    print(f"  頂点数: {validation['num_vertices']:,}")
    print(f"  面数: {validation['num_triangles']:,}")
    print(f"  Watertight: {validation['is_watertight']}")

    if validation['issues']:
        print(f"  問題: {', '.join(validation['issues'])}")
