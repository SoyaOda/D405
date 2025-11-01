# 食品体積推定システム 根本的レビューと改善提案

**作成日**: 2025-11-01
**レビュー担当**: Claude Code

---

## 🔍 現在のシステムの問題点

### 1. **お椀の直径測定位置の誤り**

#### 現状の問題
- `_measure_diameter()`が**お椀の重心からの最大距離**を測定している
- 実際の食器では**リム（縁）の直径**が必要
- 測定値: 90.41mm vs 実測値: 165mm（約45%の誤差）

```python
# 現在の実装（誤り）
center = xy_points.mean(axis=0)  # 重心
distances = np.linalg.norm(xy_points - center, axis=1)
diameter = distances.max() * 2
```

#### 改善案
```python
# 正しい実装
def measure_rim_diameter(points: np.ndarray) -> float:
    """リム（最上部）の直径を測定"""
    # Z座標の上位10%の点を取得（リム部分）
    z_threshold = np.percentile(points[:, 2], 90)
    rim_points = points[points[:, 2] > z_threshold]

    # リムの楕円フィッティング
    from sklearn.decomposition import PCA
    pca = PCA(n_components=2)
    rim_xy = rim_points[:, :2]
    pca.fit(rim_xy)

    # 主軸に沿った最大距離
    principal_axes = pca.components_
    projected = rim_xy @ principal_axes.T
    diameter = projected.max(axis=0) - projected.min(axis=0)

    return max(diameter)
```

### 2. **基準面の設定が不適切**

#### 現状の問題
- **お椀の底面**を基準面として使用
- 食品体積は**リムの高さ**を基準に測定すべき
- お椀に盛られた食品の「盛り具合」が考慮されていない

#### 最新研究からの知見
- **リムを基準面**として使用すべき（MDPI論文より）
- 食品がリムより上/下にある場合の処理が必要
- Bowl Fullness Index（充填率）の導入が有効

### 3. **お椀の高さ情報が活用されていない**

#### 現状の問題
- お椀の3D形状全体が利用されていない
- 単純なスケーリングのみで、形状制約が考慮されていない
- お椀の内部容積が計算されていない

#### 改善案
```python
class EnhancedBowlFitter:
    def __init__(self, bowl_mesh_path, real_diameter_mm, real_height_mm):
        self.bowl_mesh = o3d.io.read_triangle_mesh(bowl_mesh_path)
        self.real_diameter = real_diameter_mm
        self.real_height = real_height_mm  # 追加

        # お椀の内部容積を計算
        self.bowl_volume_ml = self._calculate_bowl_volume()

        # リム平面を定義
        self.rim_plane = self._define_rim_plane()

    def _calculate_bowl_volume(self):
        """お椀の内部容積を計算"""
        if self.bowl_mesh.is_watertight():
            volume_mm3 = self.bowl_mesh.get_volume()
            return volume_mm3 / 1000  # ml単位
        return None

    def _define_rim_plane(self):
        """リム平面を定義"""
        vertices = np.asarray(self.bowl_mesh.vertices)
        # 最上部10%の点から平面を推定
        z_threshold = np.percentile(vertices[:, 2], 90)
        rim_vertices = vertices[vertices[:, 2] > z_threshold]

        # 平面方程式: ax + by + cz + d = 0
        # RANSAC or least squaresで平面フィッティング
        from sklearn.linear_model import RANSACRegressor

        X = rim_vertices[:, :2]
        y = rim_vertices[:, 2]

        ransac = RANSACRegressor()
        ransac.fit(X, y)

        return {
            'normal': np.array([ransac.estimator_.coef_[0],
                              ransac.estimator_.coef_[1], -1]),
            'point': np.array([0, 0, ransac.estimator_.intercept_])
        }
```

---

## 📊 最新研究からの重要な知見

### 1. **MetaFood CVPR 2024 Challenge**
- 物理制約を考慮した3D食品再構成
- 深度カメラ単体での精度: MAPE 10.5%
- 食品カテゴリごとの密度データベース活用

### 2. **Bowl Reconstruction手法（MDPI 2022）**
- **リムを基準面として使用**
- Bowl Fullness Ratio（充填率）による体積推定
- Virtual Levelsによる段階的体積計算

### 3. **View Synthesis手法（PMC 2018）**
- 単一深度画像から反対側を予測
- **修正ICP**: 回転を固定し、平行移動のみ最適化
- Alpha Shapesによる非凸形状の体積計算

### 4. **DepthCalorieCam（ACM 2019）**
- モバイルアプリでの実装例
- リアルタイム処理（30fps）
- 食品カテゴリ分類と体積推定の統合

---

## 🔧 改善実装案

### Phase 1: 即座に実装可能な改善

#### 1.1 リム直径の正確な測定
```python
def measure_bowl_rim_diameter(mesh_path: str) -> dict:
    """
    お椀のリム直径を正確に測定

    Returns:
        {
            'rim_diameter_mm': リム直径,
            'bowl_height_mm': お椀の高さ,
            'bowl_volume_ml': 内部容積
        }
    """
    mesh = o3d.io.read_triangle_mesh(mesh_path)
    vertices = np.asarray(mesh.vertices)

    # PCA for orientation
    pca = PCA(n_components=3)
    centered = vertices - vertices.mean(axis=0)
    pca.fit(centered)

    # PC3が垂直方向と仮定
    vertical_axis = pca.components_[2]

    # リム検出（上位5%）
    projections = centered @ vertical_axis
    rim_threshold = np.percentile(projections, 95)
    rim_points = vertices[projections > rim_threshold]

    # リム直径計算
    rim_xy = rim_points @ pca.components_[:2].T
    diameter = np.ptp(rim_xy, axis=0).max()

    # 高さ計算
    height = projections.max() - projections.min()

    # 容積計算（watertightの場合）
    volume = mesh.get_volume() / 1000 if mesh.is_watertight() else None

    return {
        'rim_diameter_mm': diameter,
        'bowl_height_mm': height,
        'bowl_volume_ml': volume
    }
```

#### 1.2 リムベース基準面の導入
```python
def calculate_food_volume_rim_based(
    food_points: np.ndarray,
    bowl_rim_z: float,
    bowl_volume_ml: float
) -> dict:
    """
    リムを基準とした食品体積計算

    Args:
        food_points: 食品点群
        bowl_rim_z: リムのZ座標
        bowl_volume_ml: お椀の内部容積

    Returns:
        体積計算結果
    """
    # リムより上の食品
    above_rim = food_points[food_points[:, 2] > bowl_rim_z]

    # リムより下の食品
    below_rim = food_points[food_points[:, 2] <= bowl_rim_z]

    # それぞれの体積を計算
    volume_above = calculate_volume_alpha_shape(above_rim) if len(above_rim) > 0 else 0
    volume_below = calculate_volume_from_fullness(below_rim, bowl_volume_ml)

    total_volume_ml = volume_above + volume_below

    # Bowl Fullness Index
    fullness_index = volume_below / bowl_volume_ml if bowl_volume_ml > 0 else 0

    return {
        'total_volume_ml': total_volume_ml,
        'volume_above_rim_ml': volume_above,
        'volume_below_rim_ml': volume_below,
        'fullness_index': fullness_index,
        'overflow': volume_above > 0
    }
```

### Phase 2: 中期的な改善

#### 2.1 改良版ICP実装
```python
def modified_icp_translation_only(
    source: o3d.geometry.PointCloud,
    target: o3d.geometry.PointCloud,
    initial_transform: np.ndarray = None
) -> tuple:
    """
    平行移動のみのICP（回転固定）
    最新研究に基づく実装
    """
    if initial_transform is None:
        initial_transform = np.eye(4)

    # 回転成分を固定
    rotation = initial_transform[:3, :3]

    # 重心ベースの初期位置合わせ
    source_center = np.mean(np.asarray(source.points), axis=0)
    target_center = np.mean(np.asarray(target.points), axis=0)

    translation = target_center - source_center

    # 反復最適化（平行移動のみ）
    for iteration in range(50):
        # 最近傍点探索
        source_points = np.asarray(source.points)
        transformed = source_points @ rotation.T + translation

        # KDTree for nearest neighbor
        target_tree = o3d.geometry.KDTreeFlann(target)

        correspondences = []
        for point in transformed:
            [_, idx, _] = target_tree.search_knn_vector_3d(point, 1)
            correspondences.append(idx[0])

        # 対応点から新しい平行移動を計算
        target_points = np.asarray(target.points)
        target_corresp = target_points[correspondences]

        new_translation = np.mean(target_corresp - source_points @ rotation.T, axis=0)

        # 収束チェック
        if np.linalg.norm(new_translation - translation) < 1e-6:
            break

        translation = new_translation

    # 最終変換行列
    transform = np.eye(4)
    transform[:3, :3] = rotation
    transform[:3, 3] = translation

    return transform, correspondences
```

#### 2.2 Alpha Shapeによる体積計算
```python
def calculate_volume_alpha_shape(points: np.ndarray, alpha: float = None) -> float:
    """
    Alpha Shapeを使用した非凸形状の体積計算
    """
    if len(points) < 4:
        return 0

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)

    # 適応的アルファ値
    if alpha is None:
        distances = pcd.compute_nearest_neighbor_distance()
        alpha = np.mean(distances) * 2

    # Alpha Shape生成
    mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(
        pcd, alpha
    )

    # Watertight修復
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_non_manifold_edges()

    # 体積計算
    if mesh.is_watertight():
        volume_mm3 = mesh.get_volume()
        return volume_mm3 / 1000  # ml

    # フォールバック: 凸包
    hull, _ = pcd.compute_convex_hull()
    return hull.get_volume() / 1000
```

### Phase 3: 長期的な改善

#### 3.1 深層学習によるView Synthesis
- 単一視点から反対側を予測
- U-Net architectureの実装
- Synthetic dataでの事前学習

#### 3.2 食品カテゴリ別密度データベース
```python
FOOD_DENSITIES = {
    'rice': 0.67,           # ご飯
    'soup': 1.02,          # スープ
    'salad': 0.35,         # サラダ
    'meat': 0.95,          # 肉類
    'pasta': 0.58,         # パスタ
    'vegetables': 0.45,    # 野菜
    'fruit': 0.85,         # 果物
    'bread': 0.25,         # パン
    'dairy': 1.03,         # 乳製品
    'dessert': 0.75        # デザート
}
```

---

## 📈 期待される改善効果

### 精度向上
- 現状: MAPE ~25-30%（推定）
- Phase 1実装後: MAPE ~15-20%
- Phase 2実装後: MAPE ~10-15%
- Phase 3実装後: MAPE <10%

### 主な改善点
1. **リム直径の正確な測定**: スケール誤差を45%→5%以下に削減
2. **リムベース基準面**: オーバーフロー食品の正確な計測
3. **修正ICP**: フィッティング精度の向上
4. **Alpha Shape**: 非凸形状への対応
5. **Bowl Fullness Index**: 直感的な充填率指標

---

## 🚀 実装優先順位

### 即座に実装（1-2日）
1. ✅ リム直径測定の修正
2. ✅ リムベース基準面の導入
3. ✅ Bowl Fullness Indexの追加

### 短期実装（1週間）
4. 修正ICPアルゴリズム
5. Alpha Shape体積計算
6. 検証用ユニットテスト

### 中期実装（1ヶ月）
7. View Synthesis（オプション）
8. 食品カテゴリ分類との統合
9. リアルタイム処理最適化

---

## 📝 結論

現在のシステムは基本的なアプローチは正しいものの、以下の重要な改善が必要：

1. **測定位置の修正**: お椀の重心ではなくリムで直径測定
2. **基準面の変更**: 底面ではなくリムを基準に
3. **高さ情報の活用**: お椀の3D形状全体を制約として利用
4. **ICPの改良**: 回転を固定し平行移動のみ最適化
5. **体積計算の改善**: Alpha Shapeによる非凸形状対応

これらの改善により、現在の推定精度を大幅に向上させることが可能です。