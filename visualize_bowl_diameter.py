#!/usr/bin/env python3
"""
お椀の直径測定位置を3D可視化
PCAで計算した主軸と直径測定円を表示
"""

import numpy as np
import open3d as o3d
from pathlib import Path
from sklearn.decomposition import PCA

def create_arrow(start, end, color=[1, 0, 0], radius=0.5):
    """
    矢印を作成

    Args:
        start: 始点
        end: 終点
        color: 色 [R, G, B]
        radius: 半径

    Returns:
        open3d.geometry.TriangleMesh: 矢印メッシュ
    """
    direction = end - start
    length = np.linalg.norm(direction)

    if length < 1e-6:
        return None

    direction = direction / length

    # 円柱（矢印の棒）
    cylinder_height = length * 0.8
    cylinder = o3d.geometry.TriangleMesh.create_cylinder(
        radius=radius,
        height=cylinder_height
    )

    # 円錐（矢印の先）
    cone_height = length * 0.2
    cone = o3d.geometry.TriangleMesh.create_cone(
        radius=radius * 2,
        height=cone_height
    )
    cone.translate([0, 0, cylinder_height])

    # 結合
    arrow = cylinder + cone
    arrow.paint_uniform_color(color)

    # Z軸を方向ベクトルに合わせる回転
    z_axis = np.array([0, 0, 1])
    rotation_axis = np.cross(z_axis, direction)
    rotation_axis_norm = np.linalg.norm(rotation_axis)

    if rotation_axis_norm > 1e-6:
        rotation_axis = rotation_axis / rotation_axis_norm
        angle = np.arccos(np.clip(np.dot(z_axis, direction), -1.0, 1.0))

        # ロドリゲスの回転公式
        K = np.array([
            [0, -rotation_axis[2], rotation_axis[1]],
            [rotation_axis[2], 0, -rotation_axis[0]],
            [-rotation_axis[1], rotation_axis[0], 0]
        ])
        R = np.eye(3) + np.sin(angle) * K + (1 - np.cos(angle)) * (K @ K)
        arrow.rotate(R, center=[0, 0, 0])

    # 始点に移動
    arrow.translate(start)

    return arrow


def create_circle(center, radius, normal, color=[0, 1, 0], num_points=100):
    """
    円を作成

    Args:
        center: 中心座標
        radius: 半径
        normal: 法線ベクトル
        color: 色
        num_points: 円周上の点数

    Returns:
        open3d.geometry.LineSet: 円のラインセット
    """
    # 円周上の点を生成（ローカル座標系）
    theta = np.linspace(0, 2 * np.pi, num_points)
    circle_points_2d = np.column_stack([
        radius * np.cos(theta),
        radius * np.sin(theta),
        np.zeros(num_points)
    ])

    # 法線ベクトルに合わせて回転
    z_axis = np.array([0, 0, 1])
    normal_normalized = normal / np.linalg.norm(normal)

    rotation_axis = np.cross(z_axis, normal_normalized)
    rotation_axis_norm = np.linalg.norm(rotation_axis)

    if rotation_axis_norm > 1e-6:
        rotation_axis = rotation_axis / rotation_axis_norm
        angle = np.arccos(np.clip(np.dot(z_axis, normal_normalized), -1.0, 1.0))

        K = np.array([
            [0, -rotation_axis[2], rotation_axis[1]],
            [rotation_axis[2], 0, -rotation_axis[0]],
            [-rotation_axis[1], rotation_axis[0], 0]
        ])
        R = np.eye(3) + np.sin(angle) * K + (1 - np.cos(angle)) * (K @ K)

        circle_points_3d = (R @ circle_points_2d.T).T
    else:
        circle_points_3d = circle_points_2d

    # 中心に移動
    circle_points_3d += center

    # LineSet作成
    lines = [[i, (i + 1) % num_points] for i in range(num_points)]

    line_set = o3d.geometry.LineSet()
    line_set.points = o3d.utility.Vector3dVector(circle_points_3d)
    line_set.lines = o3d.utility.Vector2iVector(lines)
    line_set.colors = o3d.utility.Vector3dVector([color for _ in range(len(lines))])

    return line_set


def visualize_bowl_diameter(ply_path):
    """
    お椀の直径測定位置を可視化

    Args:
        ply_path: .plyファイルパス
    """
    print(f"\n{'='*70}")
    print(f"お椀直径測定位置の可視化")
    print(f"{'='*70}")
    print(f"\n対象: {ply_path.name}")

    # メッシュ読み込み
    print("\nメッシュ読み込み中...")
    mesh = o3d.io.read_triangle_mesh(str(ply_path))

    if not mesh.has_vertices():
        print("❌ エラー: 頂点データなし")
        return

    vertices = np.asarray(mesh.vertices)
    num_vertices = len(vertices)

    print(f"頂点数: {num_vertices:,}")

    # メッシュの色設定
    mesh.paint_uniform_color([0.7, 0.7, 0.7])  # グレー
    mesh.compute_vertex_normals()

    # バウンディングボックス中心
    bbox_center = vertices.mean(axis=0)

    # PCA実行
    print("\nPCA分析中...")
    centered_vertices = vertices - bbox_center

    pca = PCA(n_components=3)
    pca.fit(centered_vertices)

    principal_axes = pca.components_
    principal_stds = np.sqrt(pca.explained_variance_)

    print(f"\n主成分:")
    print(f"  PC1（水平1）: std={principal_stds[0]:.2f} mm")
    print(f"  PC2（水平2）: std={principal_stds[1]:.2f} mm")
    print(f"  PC3（垂直）:  std={principal_stds[2]:.2f} mm")

    # 直径計算
    diameter = max(principal_stds[0], principal_stds[1]) * 2
    radius = diameter / 2

    print(f"\n計算された直径:")
    print(f"  直径: {diameter:.2f} mm ({diameter/10:.1f} cm)")
    print(f"  半径: {radius:.2f} mm ({radius/10:.1f} cm)")

    # 可視化オブジェクト作成
    geometries = []

    # 1. お椀メッシュ
    geometries.append(mesh)

    # 2. 中心点（黒）
    center_sphere = o3d.geometry.TriangleMesh.create_sphere(radius=2.0)
    center_sphere.paint_uniform_color([0, 0, 0])
    center_sphere.translate(bbox_center)
    geometries.append(center_sphere)

    # 3. 主軸矢印
    arrow_length = 50  # mm

    # PC1（赤）- 水平方向1
    pc1_arrow = create_arrow(
        bbox_center,
        bbox_center + principal_axes[0] * arrow_length,
        color=[1, 0, 0],  # 赤
        radius=1.0
    )
    if pc1_arrow:
        geometries.append(pc1_arrow)

    # PC2（緑）- 水平方向2
    pc2_arrow = create_arrow(
        bbox_center,
        bbox_center + principal_axes[1] * arrow_length,
        color=[0, 1, 0],  # 緑
        radius=1.0
    )
    if pc2_arrow:
        geometries.append(pc2_arrow)

    # PC3（青）- 垂直方向
    pc3_arrow = create_arrow(
        bbox_center,
        bbox_center + principal_axes[2] * arrow_length,
        color=[0, 0, 1],  # 青
        radius=1.0
    )
    if pc3_arrow:
        geometries.append(pc3_arrow)

    # 4. 直径測定円（黄色）
    # 垂直方向（PC3）に垂直な平面（水平面）に直径の円を描く
    diameter_circle = create_circle(
        center=bbox_center,
        radius=radius,
        normal=principal_axes[2],  # 垂直方向（PC3）に垂直な平面
        color=[1, 1, 0],  # 黄色
        num_points=100
    )
    geometries.append(diameter_circle)

    # 5. 直径の両端点（マゼンタ）
    # 最大主成分方向の両端
    max_pc_index = 0 if principal_stds[0] >= principal_stds[1] else 1
    max_pc_axis = principal_axes[max_pc_index]

    endpoint1 = bbox_center + max_pc_axis * radius
    endpoint2 = bbox_center - max_pc_axis * radius

    endpoint1_sphere = o3d.geometry.TriangleMesh.create_sphere(radius=2.5)
    endpoint1_sphere.paint_uniform_color([1, 0, 1])  # マゼンタ
    endpoint1_sphere.translate(endpoint1)
    geometries.append(endpoint1_sphere)

    endpoint2_sphere = o3d.geometry.TriangleMesh.create_sphere(radius=2.5)
    endpoint2_sphere.paint_uniform_color([1, 0, 1])  # マゼンタ
    endpoint2_sphere.translate(endpoint2)
    geometries.append(endpoint2_sphere)

    # 6. 直径ライン（マゼンタ）
    diameter_line = o3d.geometry.LineSet()
    diameter_line.points = o3d.utility.Vector3dVector([endpoint1, endpoint2])
    diameter_line.lines = o3d.utility.Vector2iVector([[0, 1]])
    diameter_line.colors = o3d.utility.Vector3dVector([[1, 0, 1]])  # マゼンタ
    geometries.append(diameter_line)

    # 凡例情報
    print(f"\n{'='*70}")
    print("可視化の説明")
    print(f"{'='*70}")
    print(f"\n色の意味:")
    print(f"  グレー:     お椀メッシュ")
    print(f"  黒:         中心点")
    print(f"  赤矢印:     PC1（水平方向1）")
    print(f"  緑矢印:     PC2（水平方向2）")
    print(f"  青矢印:     PC3（垂直方向）")
    print(f"  黄色円:     直径測定円（{diameter:.2f} mm）")
    print(f"  マゼンタ線: 直径測定線")
    print(f"  マゼンタ点: 直径の両端点")

    print(f"\n直径測定:")
    print(f"  測定平面: 垂直方向（PC3）に垂直な平面")
    print(f"  測定方向: 最大主成分（PC{max_pc_index+1}）方向")
    print(f"  測定直径: {diameter:.2f} mm ({diameter/10:.1f} cm)")

    print(f"\n操作方法:")
    print(f"  マウスドラッグ: 回転")
    print(f"  ホイール:       ズーム")
    print(f"  右クリック:     パン")
    print(f"  'Q'キー:        終了")

    print(f"\n可視化ウィンドウを開きます...")

    # 可視化
    o3d.visualization.draw_geometries(
        geometries,
        window_name=f"お椀直径測定位置 - {ply_path.name}",
        width=1200,
        height=800,
        left=50,
        top=50
    )

    print("\n✓ 可視化完了")


def main():
    """メイン処理"""

    print("="*70)
    print("お椀直径測定位置 3D可視化")
    print("="*70)

    mesh_dir = Path("/Users/moei/program/D405/data/mesh_output")

    # 最初のファイルを可視化
    ply_file = mesh_dir / "001_bowl_mesh.ply"

    if not ply_file.exists():
        print(f"❌ エラー: {ply_file} が存在しません")
        return

    visualize_bowl_diameter(ply_file)


if __name__ == "__main__":
    main()
