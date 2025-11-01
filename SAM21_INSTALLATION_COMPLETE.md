# SAM2.1インストール完了レポート

## ✅ インストール完了

**日時**: 2025-10-31
**環境**: macOS Sequoia 15.6.1 (Apple Silicon)

---

## 📦 インストールされたコンポーネント

### Python環境

| コンポーネント | バージョン | 場所 |
|------------|----------|------|
| Python | 3.11.14 | `/opt/homebrew/bin/python3.11` |
| 仮想環境 | venv_py311 | `/Users/moei/program/D405/venv_py311` |

### 依存関係

| パッケージ | バージョン | 用途 |
|----------|----------|------|
| **torch** | 2.9.0 | PyTorch (CPU版) |
| **torchvision** | 0.24.0 | TorchVision |
| **SAM-2** | 1.0 | Segment Anything Model 2.1 |
| **open3d** | 0.19.0 | 3D処理・ICP |
| **numpy** | 2.2.6 | 数値計算 |
| **opencv-python** | 4.12.0 | 画像処理 |
| **scipy** | 1.16.3 | 科学計算 |
| **pyrealsense2-macosx** | 2.54.2 | RealSenseカメラSDK |
| **matplotlib** | 3.10.7 | 可視化 |
| **tqdm** | 4.67.1 | 進捗バー |
| **huggingface_hub** | 1.0.1 | モデルダウンロード |

---

## 🧪 テスト結果

### インストール検証テスト

```bash
/Users/moei/program/D405/venv_py311/bin/python3 test_sam21.py
```

**結果**: ✅ すべてのテストに合格

```
✓ PyTorch: 2.9.0
✓ TorchVision: 0.24.0
✓ NumPy: 2.2.6
✓ OpenCV: 4.12.0
✓ Open3D: 0.19.0
✓ SciPy: 1.16.3
✓ PyRealSense2: Imported successfully
✓ SAM2.1: Imported successfully
```

---

## 🚀 使用方法

### 1. 仮想環境のアクティベート

```bash
source /Users/moei/program/D405/venv_py311/bin/activate
```

### 2. セグメンテーションテスト

```bash
# RGB画像からお椀をセグメント
python3 src/segmentation.py nutrition5k_data/imagery/realsense_overhead/rgb_*.png
```

### 3. 体積推定パイプライン

```bash
# 完全なパイプライン実行
python3 scripts/estimate_food_volume.py \
  --rgb nutrition5k_data/imagery/realsense_overhead/rgb_food.png \
  --depth nutrition5k_data/imagery/realsense_overhead/depth_raw_food.png \
  --bowl-model data/bowl.ply \
  --bowl-diameter 120 \
  --output results/volume_food.json
```

---

## 📝 重要な注意事項

### Python 3.11が必要

- **旧環境 (venv)**: Python 3.9.6 → SAM2.1非対応
- **新環境 (venv_py311)**: Python 3.11.14 → ✅ SAM2.1対応

### スクリプト実行時のPython指定

すべてのスクリプトは **venv_py311** を使用してください:

```bash
# ✅ 正しい
/Users/moei/program/D405/venv_py311/bin/python3 scripts/estimate_food_volume.py ...

# ❌ 間違い（古い環境）
/Users/moei/program/D405/venv/bin/python3 scripts/estimate_food_volume.py ...
```

### モデルダウンロード

SAM2.1モデルは初回使用時にHugging Faceから自動ダウンロードされます:

- **facebook/sam2.1-hiera-tiny** (~40MB)
- **facebook/sam2.1-hiera-small** (~180MB)
- **facebook/sam2.1-hiera-base-plus** (~320MB)
- **facebook/sam2.1-hiera-large** (~900MB)

デフォルトはtiny版です。

---

## 🔧 トラブルシューティング

### Q1: "No module named 'sam2'" エラー

**A:** 正しい仮想環境を使用していることを確認してください

```bash
# 確認
which python3
# /Users/moei/program/D405/venv_py311/bin/python3 であることを確認

# 仮想環境をアクティベート
source /Users/moei/program/D405/venv_py311/bin/activate
```

### Q2: "CUDA not available" エラー

**A:** CPU版PyTorchをインストールしているため、これは正常です。
GPU版が必要な場合:

```bash
# GPU版のインストール（CUDA 12.1対応MacはなしApple Siliconでは不要）
# Apple Silicon Macでは Metal Performance Shaders (MPS) が自動使用されます
```

### Q3: モデルダウンロードが遅い

**A:** 小さいモデルから試してください

```python
# src/segmentation.py で model_type を変更
segmentor = SAM2Segmentor(model_type="sam2.1_hiera_tiny")  # 最小
```

---

## 📚 次のステップ

### 1. お椀の3Dモデル準備

```bash
# Blenderで .blend → .ply 変換
# または手動で data/bowl.ply に配置
```

### 2. お椀の実寸測定

定規でお椀の直径を測定（mm単位）

```
例: 120mm
```

### 3. スキャン & 体積推定

```bash
# 1. Tare Calibration
sudo /Users/moei/program/D405/venv_py311/bin/python3 scripts/calibrate.py 374

# 2. 食品スキャン
sudo /Users/moei/program/D405/venv_py311/bin/python3 scripts/scan.py rice_bowl

# 3. 体積推定
/Users/moei/program/D405/venv_py311/bin/python3 scripts/estimate_food_volume.py \
  --rgb nutrition5k_data/imagery/realsense_overhead/rgb_rice_bowl_*.png \
  --depth nutrition5k_data/imagery/realsense_overhead/depth_raw_rice_bowl_*.png \
  --bowl-model data/bowl.ply \
  --bowl-diameter 120 \
  --output results/volume_rice_bowl.json
```

---

## 📖 ドキュメント

- **INSTALLATION.md**: 詳細なインストールガイド
- **README.md**: プロジェクト概要
- **CALIBRATION_GUIDE.md**: キャリブレーション手順
- **requirements_volume_estimation.txt**: 依存関係リスト

---

## ✅ まとめ

SAM2.1のインストールとテストが正常に完了しました！

**準備完了:**
- ✅ Python 3.11環境
- ✅ SAM2.1 + 全依存関係
- ✅ RealSense SDK
- ✅ Open3D (ICP)
- ✅ すべてのモジュール動作確認

**次の作業:**
1. お椀の3Dモデル準備
2. 実際の画像でセグメンテーションテスト
3. 完全な体積推定パイプライン実行

---

**Happy Coding! 🎉**
