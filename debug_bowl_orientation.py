#!/usr/bin/env python3
"""
お椀の向きと主軸をデバッグ
"""

import numpy as np
import open3d as o3d
from sklearn.decomposition import PCA


def debug_bowl_orientation():
    """お椀の向きをデバッグ"""

    print("=" * 70)
    print("お椀の向きと主軸のデバッグ")
    print("=" * 70)

    # メッシュロード
    bowl_mesh_path = "data/mesh_output/001_bowl_mesh.ply"
    mesh = o3d.io.read_triangle_mesh(bowl_mesh_path)
    vertices = np.asarray(mesh.vertices)

    print(f"\n頂点数: {len(vertices):,}")
    print(f"\nBounding Box:")
    print(f"  X: {vertices[:, 0].min():.2f} ~ {vertices[:, 0].max():.2f} (範囲: {vertices[:, 0].max() - vertices[:, 0].min():.2f} mm)")
    print(f"  Y: {vertices[:, 1].min():.2f} ~ {vertices[:, 1].max():.2f} (範囲: {vertices[:, 1].max() - vertices[:, 1].min():.2f} mm)")
    print(f"  Z: {vertices[:, 2].min():.2f} ~ {vertices[:, 2].max():.2f} (範囲: {vertices[:, 2].max() - vertices[:, 2].min():.2f} mm)")

    # PCA分析
    print("\n" + "=" * 70)
    print("PCA分析")
    print("=" * 70)

    pca = PCA(n_components=3)
    centered = vertices - vertices.mean(axis=0)
    pca.fit(centered)

    print(f"\n説明分散:")
    for i, var in enumerate(pca.explained_variance_):
        ratio = pca.explained_variance_ratio_[i]
        print(f"  PC{i+1}: {np.sqrt(var):.2f} mm (分散比: {ratio*100:.1f}%)")

    print(f"\n主成分ベクトル:")
    for i, comp in enumerate(pca.components_):
        print(f"  PC{i+1}: [{comp[0]:6.3f}, {comp[1]:6.3f}, {comp[2]:6.3f}]")

    # 各軸での範囲を計算
    print("\n" + "=" * 70)
    print("各主成分方向での範囲")
    print("=" * 70)

    projections = centered @ pca.components_.T

    for i in range(3):
        proj_min = projections[:, i].min()
        proj_max = projections[:, i].max()
        proj_range = proj_max - proj_min
        print(f"\nPC{i+1}方向:")
        print(f"  範囲: {proj_range:.2f} mm")
        print(f"  Min: {proj_min:.2f}, Max: {proj_max:.2f}")

    # 垂直軸の特定
    print("\n" + "=" * 70)
    print("垂直軸の特定")
    print("=" * 70)

    # 方法1: 最小分散
    vertical_idx_by_variance = np.argmin(pca.explained_variance_)
    print(f"\n最小分散軸: PC{vertical_idx_by_variance + 1}")

    # 方法2: Y軸との相関
    y_axis = np.array([0, 1, 0])
    correlations = [abs(np.dot(pca.components_[i], y_axis)) for i in range(3)]
    vertical_idx_by_y = np.argmax(correlations)
    print(f"Y軸と最も相関が高い軸: PC{vertical_idx_by_y + 1} (相関: {correlations[vertical_idx_by_y]:.3f})")

    # 方法3: Z軸との相関
    z_axis = np.array([0, 0, 1])
    correlations_z = [abs(np.dot(pca.components_[i], z_axis)) for i in range(3)]
    vertical_idx_by_z = np.argmax(correlations_z)
    print(f"Z軸と最も相関が高い軸: PC{vertical_idx_by_z + 1} (相関: {correlations_z[vertical_idx_by_z]:.3f})")

    # リム点の抽出（各仮説で）
    print("\n" + "=" * 70)
    print("リム点抽出テスト")
    print("=" * 70)

    for hypothesis, idx in [
        ("最小分散軸", vertical_idx_by_variance),
        ("Y軸相関", vertical_idx_by_y),
        ("Z軸相関", vertical_idx_by_z)
    ]:
        print(f"\n{hypothesis} (PC{idx+1}) を垂直軸とした場合:")

        vertical_axis = pca.components_[idx]
        vertical_projections = centered @ vertical_axis

        rim_threshold = np.percentile(vertical_projections, 95)
        rim_mask = vertical_projections > rim_threshold
        rim_points = vertices[rim_mask]

        print(f"  リム点数: {rim_points.sum() if isinstance(rim_points, np.ndarray) else len(rim_points):,}")

        if len(rim_points) > 3:
            # 水平面に投影
            horizontal_indices = [i for i in range(3) if i != idx]
            horizontal_axes = pca.components_[horizontal_indices]

            rim_centered = rim_points - vertices.mean(axis=0)
            rim_horizontal = rim_centered @ horizontal_axes.T

            pc1_range = rim_horizontal[:, 0].max() - rim_horizontal[:, 0].min()
            pc2_range = rim_horizontal[:, 1].max() - rim_horizontal[:, 1].min()
            diameter = max(pc1_range, pc2_range)

            print(f"  水平軸1範囲: {pc1_range:.2f} mm")
            print(f"  水平軸2範囲: {pc2_range:.2f} mm")
            print(f"  推定直径: {diameter:.2f} mm")

    # 旧実装
    print("\n" + "=" * 70)
    print("旧実装（重心ベース）")
    print("=" * 70)

    center = vertices.mean(axis=0)
    xy_points = vertices[:, :2]
    center_xy = center[:2]
    distances = np.linalg.norm(xy_points - center_xy, axis=1)
    old_diameter = distances.max() * 2
    print(f"\n測定直径: {old_diameter:.2f} mm")
    print(f"期待値: 165.0 mm")
    print(f"誤差: {abs(old_diameter - 165.0):.2f} mm ({abs(old_diameter - 165.0)/165.0*100:.1f}%)")


if __name__ == "__main__":
    debug_bowl_orientation()
