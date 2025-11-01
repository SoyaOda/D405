# 体積推定パイプライン インストールガイド

## 📋 概要

SAM2.1 + ICP + お椀3Dモデルを使った食品体積推定システムのインストール手順

---

## 🚀 インストール手順

### ステップ1: 基本依存関係のインストール

```bash
cd /Users/moei/program/D405

# 仮想環境でインストール（推奨）
source venv/bin/activate

# 基本依存関係
pip install -r requirements_volume_estimation.txt
```

### ステップ2: SAM2.1のインストール

SAM2.1は別途GitHubからインストールが必要です。

```bash
# 一時ディレクトリにクローン
cd /tmp
git clone https://github.com/facebookresearch/sam2.git
cd sam2

# SAM2.1をインストール
pip install -e .

# 元のディレクトリに戻る
cd /Users/moei/program/D405
```

**または直接インストール:**

```bash
pip install git+https://github.com/facebookresearch/sam2.git
```

### ステップ3: インストール確認

```bash
# SAM2.1の確認
python3 -c "from sam2.sam2_image_predictor import SAM2ImagePredictor; print('SAM2.1 OK')"

# Open3Dの確認
python3 -c "import open3d as o3d; print('Open3D OK')"

# PyTorchの確認
python3 -c "import torch; print(f'PyTorch {torch.__version__} OK')"
```

---

## 📦 必要な依存関係

### 必須

| パッケージ | バージョン | 用途 |
|----------|----------|------|
| numpy | >=1.24.0 | 数値計算 |
| opencv-python | >=4.8.0 | 画像処理 |
| open3d | >=0.18.0 | 3D処理・ICP |
| torch | >=2.5.1 | SAM2.1 |
| torchvision | >=0.20.1 | SAM2.1 |
| sam2 | latest | セグメンテーション |
| pyrealsense2 | >=2.54.2 | カメラSDK |

### オプション

| パッケージ | 用途 |
|----------|------|
| matplotlib | グラフ描画 |
| tqdm | 進捗バー |

---

## 🔧 お椀の3Dモデル準備

### 方法1: Blenderから.ply形式に変換

```bash
# Blenderをインストール（未インストールの場合）
brew install blender  # macOS

# .blend → .ply 変換スクリプト
blender --background --python - <<EOF
import bpy
import sys

# .blendファイルを開く
bpy.ops.wm.open_mainfile(filepath="path/to/bowl.blend")

# すべてのオブジェクトを選択
bpy.ops.object.select_all(action='SELECT')

# .ply形式でエクスポート
bpy.ops.wm.ply_export(filepath="data/bowl.ply")
print("✓ 変換完了: data/bowl.ply")
EOF
```

### 方法2: オンラインツールを使用

1. [Aspose 3D Converter](https://products.aspose.app/3d/conversion/blend-to-ply) にアクセス
2. .blendファイルをアップロード
3. PLY形式を選択してダウンロード
4. `data/bowl.ply` に配置

### 3Dモデルの確認

```bash
# Open3Dで可視化
python3 -c "
import open3d as o3d
mesh = o3d.io.read_triangle_mesh('data/bowl.ply')
print(f'頂点数: {len(mesh.vertices)}')
print(f'三角形数: {len(mesh.triangles)}')
o3d.visualization.draw_geometries([mesh])
"
```

---

## ✅ 動作確認

### 最小テスト

```bash
# 1. Tare Calibration（既存）
sudo /Users/moei/program/D405/venv/bin/python3 scripts/calibrate.py 374

# 2. スキャン（既存）
sudo /Users/moei/program/D405/venv/bin/python3 scripts/scan.py test_food

# 3. 体積推定（新規）
python3 scripts/estimate_food_volume.py \
  --rgb nutrition5k_data/imagery/realsense_overhead/rgb_test_food_*.png \
  --depth nutrition5k_data/imagery/realsense_overhead/depth_raw_test_food_*.png \
  --bowl-model data/bowl.ply \
  --bowl-diameter 120 \
  --output results/volume_test.json
```

---

## 🐛 トラブルシューティング

### Q1: SAM2.1のインストールが失敗する

**A:** PyTorchのバージョンを確認

```bash
# PyTorchバージョン確認
python3 -c "import torch; print(torch.__version__)"

# 2.5.1以上が必要
# アップグレード
pip install --upgrade torch torchvision
```

### Q2: "CUDA not available"エラー

**A:** CPU版で動作します（GPUオプション）

```bash
# CPU版で動作確認
python3 -c "
from sam2.sam2_image_predictor import SAM2ImagePredictor
predictor = SAM2ImagePredictor.from_pretrained('facebook/sam2-1-hiera-tiny')
print('CPU版で動作OK')
"
```

GPU版を使用する場合:

```bash
# CUDA対応PyTorchをインストール
pip install torch==2.5.1+cu121 torchvision==0.20.1+cu121 \
  --index-url https://download.pytorch.org/whl/cu121
```

### Q3: Open3Dの可視化ウィンドウが表示されない

**A:** ヘッドレスモードを使用

```bash
# 可視化を無効化
python3 scripts/estimate_food_volume.py \
  --rgb ... \
  --depth ... \
  --bowl-model ... \
  --bowl-diameter 120 \
  --no-visualize  # 追加
```

### Q4: お椀の3Dモデルが読み込めない

**A:** サポートされている形式を確認

```bash
# サポート形式: .ply, .obj, .stl
# 確認
file data/bowl.ply

# 変換（.objの場合）
python3 -c "
import open3d as o3d
mesh = o3d.io.read_triangle_mesh('data/bowl.obj')
o3d.io.write_triangle_mesh('data/bowl.ply', mesh)
print('✓ PLY変換完了')
"
```

---

## 📚 参考資料

- **SAM2.1 GitHub**: https://github.com/facebookresearch/sam2
- **Open3D Documentation**: http://www.open3d.org/docs/latest/
- **PyTorch Installation**: https://pytorch.org/get-started/locally/
- **Intel RealSense SDK**: https://github.com/IntelRealSense/librealsense

---

## 🎯 次のステップ

インストール完了後:

1. お椀の3Dモデルを準備（.ply形式）
2. お椀の実寸を測定（直径をmm単位で）
3. Tare Calibrationを実行
4. 食品をスキャン
5. 体積推定パイプラインを実行

詳細は `README.md` を参照してください。
