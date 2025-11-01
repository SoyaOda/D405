#!/usr/bin/env python3
"""
お椀のリム（縁）直径を正確に測定

お椀の最上部（リム）の直径を測定し、実際の食器サイズと一致させる。
"""

import numpy as np
import open3d as o3d
from pathlib import Path
from sklearn.decomposition import PCA
from sklearn.linear_model import RANSACRegressor


def measure_bowl_rim_diameter(mesh_path: str, visualize: bool = True) -> dict:
    """
    お椀のリム直径を正確に測定

    Args:
        mesh_path: お椀メッシュのパス
        visualize: 可視化するか

    Returns:
        {
            'rim_diameter_mm': リム直径,
            'bowl_height_mm': お椀の高さ,
            'bowl_volume_ml': 内部容積,
            'rim_points': リム部分の点群,
            'center_diameter_mm': 中心での直径（比較用）
        }
    """
    print("=" * 70)
    print("お椀リム直径測定")
    print("=" * 70)
    print(f"対象: {Path(mesh_path).name}")

    # メッシュ読み込み
    mesh = o3d.io.read_triangle_mesh(mesh_path)

    if not mesh.has_vertices():
        raise ValueError("メッシュに頂点データがありません")

    vertices = np.asarray(mesh.vertices)
    num_vertices = len(vertices)

    print(f"\n頂点数: {num_vertices:,}")

    # ========================================
    # 1. PCAで主軸を特定
    # ========================================
    print("\n[1] 主軸分析（PCA）")
    print("-" * 40)

    # 中心化
    center = vertices.mean(axis=0)
    centered = vertices - center

    # PCA実行
    pca = PCA(n_components=3)
    pca.fit(centered)

    principal_axes = pca.components_
    principal_stds = np.sqrt(pca.explained_variance_)

    print(f"主成分の広がり:")
    print(f"  PC1: {principal_stds[0]:.2f} mm")
    print(f"  PC2: {principal_stds[1]:.2f} mm")
    print(f"  PC3: {principal_stds[2]:.2f} mm")

    # PC3が垂直方向（最小分散）と仮定
    vertical_axis = principal_axes[2]
    horizontal_axes = principal_axes[:2]

    # ========================================
    # 2. リム（最上部）の検出
    # ========================================
    print("\n[2] リム検出")
    print("-" * 40)

    # 垂直軸への投影
    vertical_projections = centered @ vertical_axis

    # 上位5%をリムとする（調整可能）
    rim_percentile = 95
    rim_threshold = np.percentile(vertical_projections, rim_percentile)

    # リム部分の点を抽出
    rim_mask = vertical_projections > rim_threshold
    rim_points = vertices[rim_mask]
    num_rim_points = len(rim_points)

    print(f"リム閾値: 上位{100-rim_percentile}%")
    print(f"リム点数: {num_rim_points:,} / {num_vertices:,}")
    print(f"リムZ範囲: {rim_points[:, 2].min():.2f} - {rim_points[:, 2].max():.2f} mm")

    # ========================================
    # 3. リム直径の計算
    # ========================================
    print("\n[3] 直径計算")
    print("-" * 40)

    # リム点を水平面に投影
    rim_centered = rim_points - center
    rim_horizontal = rim_centered @ horizontal_axes.T

    # 各主軸での範囲
    pc1_range = rim_horizontal[:, 0].max() - rim_horizontal[:, 0].min()
    pc2_range = rim_horizontal[:, 1].max() - rim_horizontal[:, 1].min()

    # 最大直径（楕円の長軸）
    rim_diameter_mm = max(pc1_range, pc2_range)

    print(f"PC1方向の幅: {pc1_range:.2f} mm")
    print(f"PC2方向の幅: {pc2_range:.2f} mm")
    print(f"リム直径: {rim_diameter_mm:.2f} mm ({rim_diameter_mm/10:.1f} cm)")

    # ========================================
    # 4. 比較：中心での直径（従来の方法）
    # ========================================
    print("\n[4] 比較：中心直径（従来法）")
    print("-" * 40)

    # 垂直方向の中央50%付近
    mid_low = np.percentile(vertical_projections, 40)
    mid_high = np.percentile(vertical_projections, 60)
    mid_mask = (vertical_projections >= mid_low) & (vertical_projections <= mid_high)
    mid_points = vertices[mid_mask]

    if len(mid_points) > 0:
        # 中央部分の直径
        mid_centered = mid_points - center
        mid_horizontal = mid_centered @ horizontal_axes.T

        mid_pc1_range = mid_horizontal[:, 0].max() - mid_horizontal[:, 0].min()
        mid_pc2_range = mid_horizontal[:, 1].max() - mid_horizontal[:, 1].min()
        center_diameter_mm = max(mid_pc1_range, mid_pc2_range)

        print(f"中心直径: {center_diameter_mm:.2f} mm ({center_diameter_mm/10:.1f} cm)")
        print(f"差: {rim_diameter_mm - center_diameter_mm:.2f} mm")
        print(f"比率: {rim_diameter_mm / center_diameter_mm:.2f}x")
    else:
        center_diameter_mm = 0
        print("中心直径: 計算不可")

    # ========================================
    # 5. お椀の高さ
    # ========================================
    print("\n[5] 高さ測定")
    print("-" * 40)

    bowl_height_mm = vertical_projections.max() - vertical_projections.min()
    print(f"お椀の高さ: {bowl_height_mm:.2f} mm ({bowl_height_mm/10:.1f} cm)")

    # アスペクト比
    aspect_ratio = rim_diameter_mm / bowl_height_mm
    print(f"アスペクト比（直径/高さ）: {aspect_ratio:.2f}")

    # ========================================
    # 6. 内部容積（Watertightの場合）
    # ========================================
    print("\n[6] 容積計算")
    print("-" * 40)

    if mesh.is_watertight():
        volume_mm3 = mesh.get_volume()
        volume_ml = volume_mm3 / 1000
        print(f"✅ Watertight: Yes")
        print(f"内部容積: {volume_ml:.1f} ml")
    else:
        volume_ml = None
        print(f"⚠️ Watertight: No")
        print(f"内部容積: 計算不可")

    # ========================================
    # 7. リム平面の推定
    # ========================================
    print("\n[7] リム平面")
    print("-" * 40)

    if len(rim_points) > 10:
        # RANSACで平面フィッティング
        X = rim_points[:, :2]
        y = rim_points[:, 2]

        ransac = RANSACRegressor(random_state=42)
        ransac.fit(X, y)

        # 平面の法線
        normal = np.array([
            ransac.estimator_.coef_[0],
            ransac.estimator_.coef_[1],
            -1
        ])
        normal = normal / np.linalg.norm(normal)

        # 垂直からの傾き
        vertical = np.array([0, 0, 1])
        angle = np.arccos(np.clip(np.abs(np.dot(normal, vertical)), 0, 1))
        angle_deg = np.degrees(angle)

        print(f"リム平面の傾き: {angle_deg:.2f}度")

        if angle_deg < 5:
            print(f"✅ リムは水平（良好）")
        elif angle_deg < 10:
            print(f"⚠️ リムがやや傾いている")
        else:
            print(f"❌ リムが大きく傾いている")

    # ========================================
    # 8. 可視化
    # ========================================
    if visualize:
        print("\n[8] 可視化")
        print("-" * 40)

        geometries = []

        # メッシュ（グレー）
        mesh_vis = o3d.geometry.TriangleMesh(mesh)
        mesh_vis.paint_uniform_color([0.7, 0.7, 0.7])
        mesh_vis.compute_vertex_normals()
        geometries.append(mesh_vis)

        # リム点（赤）
        rim_pcd = o3d.geometry.PointCloud()
        rim_pcd.points = o3d.utility.Vector3dVector(rim_points)
        rim_pcd.paint_uniform_color([1, 0, 0])
        geometries.append(rim_pcd)

        # 中心点（青）
        center_sphere = o3d.geometry.TriangleMesh.create_sphere(radius=3.0)
        center_sphere.translate(center)
        center_sphere.paint_uniform_color([0, 0, 1])
        geometries.append(center_sphere)

        # リム直径ライン（黄色）
        rim_center = rim_points.mean(axis=0)
        rim_horizontal_max = rim_centered @ horizontal_axes[0]
        max_idx = np.argmax(np.abs(rim_horizontal_max))

        endpoint1 = rim_points[max_idx]
        endpoint2 = 2 * rim_center - endpoint1  # 対称点

        line_set = o3d.geometry.LineSet()
        line_set.points = o3d.utility.Vector3dVector([endpoint1, endpoint2])
        line_set.lines = o3d.utility.Vector2iVector([[0, 1]])
        line_set.colors = o3d.utility.Vector3dVector([[1, 1, 0]])
        geometries.append(line_set)

        print("可視化ウィンドウを開きます...")
        print("  赤: リム部分の点")
        print("  青: 中心点")
        print("  黄: リム直径")

        o3d.visualization.draw_geometries(
            geometries,
            window_name=f"お椀リム直径測定 - {Path(mesh_path).name}",
            width=1200,
            height=800
        )

    # 結果を返す
    result = {
        'rim_diameter_mm': rim_diameter_mm,
        'bowl_height_mm': bowl_height_mm,
        'bowl_volume_ml': volume_ml,
        'rim_points': rim_points,
        'center_diameter_mm': center_diameter_mm,
        'aspect_ratio': aspect_ratio
    }

    return result


def main():
    """メイン処理"""

    print("=" * 70)
    print("お椀リム直径測定ツール")
    print("=" * 70)

    # デフォルトパス
    mesh_path = "/Users/moei/program/D405/data/mesh_output/001_bowl_mesh.ply"

    # ファイル存在チェック
    if not Path(mesh_path).exists():
        print(f"❌ エラー: {mesh_path} が存在しません")
        return

    # 測定実行
    result = measure_bowl_rim_diameter(mesh_path, visualize=True)

    # 結果サマリー
    print("\n" + "=" * 70)
    print("測定結果サマリー")
    print("=" * 70)

    print(f"\n✅ リム直径: {result['rim_diameter_mm']:.2f} mm "
          f"({result['rim_diameter_mm']/10:.1f} cm)")

    print(f"✅ お椀の高さ: {result['bowl_height_mm']:.2f} mm "
          f"({result['bowl_height_mm']/10:.1f} cm)")

    if result['bowl_volume_ml']:
        print(f"✅ 内部容積: {result['bowl_volume_ml']:.1f} ml")

    print(f"\n比較:")
    print(f"  中心直径: {result['center_diameter_mm']:.2f} mm")
    print(f"  差: {result['rim_diameter_mm'] - result['center_diameter_mm']:.2f} mm")

    print(f"\n推奨:")
    print(f"  --bowl-diameter パラメータに {result['rim_diameter_mm']:.0f} を使用")

    # 実測値との比較
    actual_diameter_mm = 165  # ユーザーが測定した実測値
    difference = result['rim_diameter_mm'] - actual_diameter_mm
    error_percent = abs(difference) / actual_diameter_mm * 100

    print(f"\n実測値との比較:")
    print(f"  実測値: {actual_diameter_mm} mm")
    print(f"  測定値: {result['rim_diameter_mm']:.2f} mm")
    print(f"  誤差: {difference:+.2f} mm ({error_percent:.1f}%)")

    if error_percent < 5:
        print(f"  ✅ 精度良好")
    elif error_percent < 10:
        print(f"  ⚠️ 許容範囲内")
    else:
        print(f"  ❌ 誤差が大きい - メッシュの確認が必要")


if __name__ == "__main__":
    main()