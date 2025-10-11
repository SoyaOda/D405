# RealSense D405 食材スキャンシステム

Intel RealSense D405を使用した、研究用途向け食材スキャン・深度測定システムです。
Nutrition5kデータセット互換の撮像プロトコルを実装しています。

## 📋 目次

- [クイックスタート](#-クイックスタート)
- [環境情報](#-環境情報)
- [カメラキャリブレーション（重要）](#-カメラキャリブレーション重要)
- [食材スキャンシステム](#-食材スキャンシステム)
- [基本スクリプト](#-基本スクリプト)
- [使用例・ワークフロー](#-使用例ワークフロー)
- [トラブルシューティング](#-トラブルシューティング)
- [ファイル構成](#-ファイル構成)
- [参考情報](#-参考情報)

---

## 🚀 クイックスタート

### 最も簡単な始め方（Nutrition5k互換スキャン）

```bash
# 1. カメラを固定してキャリブレーション（レーザー距離計で測定: 例250mm）
sudo /Users/moei/program/D405/venv/bin/python3 calibrate_realsense.py 250

# 2. 食材をスキャン
sudo /Users/moei/program/D405/venv/bin/python3 nutrition5k_style_scanner.py apple 20

# 3. データ解析
python3 analyze_nutrition5k_data.py apple
```

**操作:**
- カメラプレビューで7-50cm範囲に食材を配置
- 's' キー: 高品質撮影（20フレーム平均）
- 'c' キー: クイック撮影
- 'q' キー: 終了

---

## 🔧 環境情報

### システム構成
- **OS**: macOS (Apple Silicon)
- **Python**: 3.9.6
- **カメラ**: Intel RealSense D405
- **ライブラリ**: pyrealsense2-macosx, opencv-python, numpy

### セットアップ完了済み ✅
1. Homebrew で librealsense インストール済み
2. Python 仮想環境作成済み (`venv/`)
3. pyrealsense2-macosx インストール済み
4. OpenCV, NumPy インストール済み

### ⚠️ 重要事項

**macOS では sudo 権限が必須です**

すべての RealSense カメラを使うスクリプトは以下の形式で実行：

```bash
sudo /Users/moei/program/D405/venv/bin/python3 <スクリプト名>
```

---

## 🔧 カメラキャリブレーション（重要）

### なぜキャリブレーションが必要？

食材の体積推定を正確に行うには、**テーブル面（参照平面）に対するキャリブレーション**が必須です。

**理由:**
1. **参照平面の確立**: テーブル面を基準とした相対深度の計算
2. **食材の高さ計算**: 食材の高さ = 測定深度 - テーブル深度
3. **深度精度の補正**: Ground Truth距離による補正で±1mm精度

### calibrate_realsense.py - Tare Calibration

```bash
sudo /Users/moei/program/D405/venv/bin/python3 calibrate_realsense.py [ground_truth_mm]
```

**手順:**

#### 1. カメラを固定位置に設置
- オーバーヘッド（真上）から撮影できる位置
- カメラが動かないように固定

#### 2. 空のテーブルにレーザー距離計を当てる
- カメラからテーブル面までの正確な距離を測定
- 推奨: レーザー距離計使用（精度 ±1mm）
- 代替: 定規で測定（精度 ±5mm）

#### 3. キャリブレーション実行

```bash
# 例: レーザー距離計で測定した距離が 250mm の場合
sudo /Users/moei/program/D405/venv/bin/python3 calibrate_realsense.py 250
```

#### 4. キャリブレーション完了
- `calibration_data.json` に保存される
- 以降のスキャンで自動的に使用される

**保存されるデータ:**
- テーブル距離（メートル）
- Ground Truth 距離（ミリメートル）
- 深度スケール
- キャリブレーション日時
- 統計情報（平均、標準偏差、最小値、最大値）

**重要な注意事項:**
- ⚠️ **カメラを移動したらキャリブレーションをやり直す**
- 空のテーブルでキャリブレーション実行
- キャリブレーションなしでもスキャン可能（精度は低下）

---

## 🍎 食材スキャンシステム

### Nutrition5k スタイルスキャナー ⭐ 推奨

Google Research の Nutrition5k データセットの撮像プロトコルに基づいた実装です。

#### nutrition5k_style_scanner.py
**Nutrition5k 互換の食材スキャナー（研究用途）** 🔬

```bash
sudo /Users/moei/program/D405/venv/bin/python3 nutrition5k_style_scanner.py [食材名] [平均化フレーム数]
```

**例:**
```bash
# デフォルト（20フレーム平均）
sudo /Users/moei/program/D405/venv/bin/python3 nutrition5k_style_scanner.py apple 20

# 滑らかな表面用（30フレーム平均）
sudo /Users/moei/program/D405/venv/bin/python3 nutrition5k_style_scanner.py tomato 30

# テクスチャのある表面用（10フレーム平均）
sudo /Users/moei/program/D405/venv/bin/python3 nutrition5k_style_scanner.py banana 10
```

**Nutrition5k 仕様:**
- **深度エンコーディング:** 16-bit PNG（1m = 10,000ユニット）
- **最大深度:** 0.4m（4,000ユニット）← Nutrition5k 仕様
- **解像度:** 1280x720（FOV最適化）
- **オーバーヘッド撮影:** 真上からの撮影を想定
- **カラーマップ:** 青（近）→ 赤（遠）
- **マルチフレーム平均:** 複数フレームの中央値フィルター

**平均化フレーム数のガイドライン:**
- **テクスチャのある表面:** 10-15フレーム
- **白い/滑らかな表面:** 20-30フレーム（ノイズ大幅削減）
- **デフォルト:** 20フレーム

**操作方法:**
- `s` キー: マルチフレーム平均撮影（高品質）
- `c` キー: 単一フレーム撮影（クイック）
- `q` キー: 終了

**保存形式（Nutrition5k互換）:**
```
nutrition5k_data/imagery/realsense_overhead/
├── rgb_<dish_id>.png           # RGB画像
├── depth_raw_<dish_id>.png     # 生深度（16-bit）
├── depth_colorized_<dish_id>.png  # カラーマップ深度
└── metadata_<dish_id>.txt      # メタデータ（キャリブレーション情報含む）
```

**メタデータに含まれる情報:**
- Dish ID、タイムスタンプ、食材名
- 解像度、深度エンコーディング、最大深度
- 平均化フレーム数
- **キャリブレーション情報** ✅
  - キャリブレーション日時
  - テーブル距離
  - Ground Truth距離
- 深度統計（最小値、最大値、平均値、中央値）

**利点:**
- ✅ 研究データセット（Nutrition5k）との互換性
- ✅ キャリブレーション情報がメタデータに記録
- ✅ 標準化されたデータフォーマット
- ✅ 他の研究者とのデータ共有が容易
- ✅ 体積推定に最適化

#### analyze_nutrition5k_data.py
**Nutrition5k形式データの解析ツール**

```bash
python3 analyze_nutrition5k_data.py [dish_id または 食材名]
```

**例:**
```bash
# 特定のスキャンを解析
python3 analyze_nutrition5k_data.py apple_20251010_120000

# 最新のスキャンを自動選択
python3 analyze_nutrition5k_data.py apple
```

**機能:**
- Nutrition5k形式データの読み込み
- 深度統計の表示（ユニット + メートル）
- 深度分布ヒストグラム
- RGB + 深度の可視化
- キャリブレーション情報の表示

**注意:** このスクリプトは sudo 不要です（保存済みデータを読むだけ）

---

### 従来版食材スキャナー

#### food_scanner.py
**食材スキャン専用スクリプト（ベストプラクティス適用済み）** 🥗

```bash
sudo /Users/moei/program/D405/venv/bin/python3 food_scanner.py [食材名] [平均化フレーム数]
```

**nutrition5k_style_scanner.py との違い:**
- 保存形式: NumPy形式（.npy）
- ディレクトリ構造: `food_scans/[食材名]/`
- メタデータ形式: 簡易版

**ベストプラクティス適用内容:**

✅ **D405 最適設定**
- 推奨距離範囲：7-50cm（リアルタイム表示）
- Visual Preset: High Accuracy
- 高解像度：1280x720（FOV一致、位置合わせ精度最大）

✅ **ポストプロセッシングフィルター**
1. Decimation Filter - ノイズ削減
2. Spatial Filter - 平滑化
3. Temporal Filter - フレーム間一貫性向上
4. Hole Filling Filter - 欠損値補完

✅ **時間平均フィルター**
- 複数フレーム（10-30フレーム）の中央値フィルター
- 深度=0（無効値）を除外して計算
- **ノイズ大幅削減**：白い表面で約3倍改善

✅ **Color-Depth アライメント**
- カラー画像と深度画像の位置合わせ

**操作方法:**
- `s` キー: 複数フレームをキャプチャして保存（高品質）
- `q` キー: 終了

**保存先:** `food_scans/[食材名]/`

#### analyze_food_scan.py
**食材スキャンデータの解析・比較** 📊

```bash
python3 analyze_food_scan.py [食材名]
```

**機能:**
- 食材のすべてのスキャンをリスト表示
- 個別スキャンの詳細解析
- 複数スキャンの比較
- 統計情報の可視化

**注意:** このスクリプトは sudo 不要です

---

## 📝 基本スクリプト

### test_pipeline.py
**基本的な動作確認用**

```bash
sudo /Users/moei/program/D405/venv/bin/python3 test_pipeline.py
```

- 深度・カラーストリームの起動確認
- 5フレームを取得してサイズを表示
- 動作確認が目的

### capture_and_visualize.py
**リアルタイム可視化・画像保存用** 🎥

```bash
sudo /Users/moei/program/D405/venv/bin/python3 capture_and_visualize.py
```

**機能:**
- カラー画像と深度画像をリアルタイム表示
- 画面中央の距離を表示
- キー操作で画像保存

**操作方法:**
- `s` キー: 現在のフレームを保存
- `q` キー: 終了

**保存先:** `captured_images/`

### analyze_depth.py
**保存した深度データの解析用** 📊

```bash
python3 analyze_depth.py captured_images/depth_raw_<タイムスタンプ>.npy
```

**機能:**
- 深度データの統計情報表示
- 深度分布のヒストグラム表示
- 深度マップの可視化

**注意:** このスクリプトは sudo 不要です

---

## 🔬 使用例・ワークフロー

### Nutrition5k スタイルスキャンのワークフロー（研究用途・推奨）

#### Step 1: カメラを固定してキャリブレーション

```bash
# 1. カメラをオーバーヘッド（真上）に固定
# 2. レーザー距離計でテーブルまでの距離を測定（例: 250mm）
# 3. 空のテーブルでキャリブレーション実行

sudo /Users/moei/program/D405/venv/bin/python3 calibrate_realsense.py 250

# → calibration_data.json が作成される
```

**確認事項:**
- ✅ カメラが固定されている
- ✅ テーブルが空である
- ✅ レーザー距離計で正確に測定

#### Step 2: 食材をスキャン

```bash
# リンゴをスキャン（20フレーム平均）
sudo /Users/moei/program/D405/venv/bin/python3 nutrition5k_style_scanner.py apple 20

# トマトをスキャン（滑らかな表面なので30フレーム平均）
sudo /Users/moei/program/D405/venv/bin/python3 nutrition5k_style_scanner.py tomato 30
```

**操作手順:**
1. プレビューウィンドウが開く
2. カメラから 7-50cm の距離に食材を配置
3. 画面に "OPTIMAL (7-50cm)" が表示されたら準備OK
4. `s` キー: 高品質撮影（指定フレーム数の中央値）
5. 複数角度から撮影する場合は、位置を変えて `s` を複数回
6. `q` キー: 終了

#### Step 3: スキャンデータを確認

```bash
# 保存されたファイルを確認
ls nutrition5k_data/imagery/realsense_overhead/

# 出力例：
# rgb_apple_20251010_120000.png
# depth_raw_apple_20251010_120000.png (16-bit)
# depth_colorized_apple_20251010_120000.png
# metadata_apple_20251010_120000.txt

# メタデータを表示
cat nutrition5k_data/imagery/realsense_overhead/metadata_apple_20251010_120000.txt
```

#### Step 4: スキャンデータを解析

```bash
# データ解析（特定のスキャン）
python3 analyze_nutrition5k_data.py apple_20251010_120000

# または食材名のみ（最新のスキャンを自動選択）
python3 analyze_nutrition5k_data.py apple
```

**出力:**
- 深度統計（ユニット + メートル）
- 深度分布ヒストグラム
- RGB + 深度の可視化
- キャリブレーション情報

---

### 基本的なワークフロー（動作確認）

#### 1. 動作確認
```bash
sudo /Users/moei/program/D405/venv/bin/python3 test_pipeline.py
```

#### 2. 画像キャプチャ（一般用途）
```bash
sudo /Users/moei/program/D405/venv/bin/python3 capture_and_visualize.py
# ウィンドウが表示されたら 's' キーで保存
```

#### 3. 深度データ解析
```bash
python3 analyze_depth.py captured_images/depth_raw_20251010_223000.npy
```

---

## 🔧 トラブルシューティング

### "No module named 'pyrealsense2'" エラー

→ 仮想環境のフルパスで Python を実行してください：
```bash
sudo /Users/moei/program/D405/venv/bin/python3 <スクリプト>
```

### "failed to set power state" エラー

→ これは macOS の既知の問題です。以下を試してください：
- sudo で実行する
- USB ポートを変更する（画面に近いポートを推奨）
- カメラを抜き差しする

### "segmentation fault" エラー

→ システムの Python を使っています。venv の Python を使ってください：
```bash
sudo /Users/moei/program/D405/venv/bin/python3 <スクリプト>
```

### 深度データが拡大して見える / 位置がずれる

→ これは **FOV（視野角）の違い**が原因です：
- **原因：** 640x480 では深度カメラ（79.4°）とカラーカメラ（72.9°）の FOV が異なる
- **解決策：** 1280x720 または 640x360 を使用（FOV がほぼ一致）
- **現在の実装：** nutrition5k_style_scanner.py と food_scanner.py は 1280x720 に設定済み（推奨）

**FOV 比較：**
- 640x480: 深度 79.4° vs カラー 72.9° → **差が大きい** ❌
- 1280x720: 深度 89.5° vs カラー 89.1° → **ほぼ一致** ✅

### キャリブレーションが読み込まれない

→ 以下を確認してください：
- `calibration_data.json` が存在するか確認
- カメラを移動した場合は再キャリブレーション
- キャリブレーションなしでもスキャン可能（警告が表示される）

---

## 📁 ファイル構成

```
D405/
├── venv/                          # Python 仮想環境
│
├── captured_images/               # 一般キャプチャ画像の保存先
│   ├── color_*.png
│   ├── depth_*.png
│   └── depth_raw_*.npy
│
├── food_scans/                    # 食材スキャンデータの保存先（従来版）
│   ├── apple/                     # 食材ごとにフォルダ分け
│   │   ├── color_*.png
│   │   ├── depth_vis_*.png
│   │   ├── depth_raw_*.npy
│   │   └── metadata_*.txt
│   ├── tomato/
│   └── banana/
│
├── nutrition5k_data/              # Nutrition5k互換データの保存先 ⭐
│   └── imagery/
│       └── realsense_overhead/
│           ├── rgb_*.png              # RGB画像
│           ├── depth_raw_*.png        # 生深度（16-bit）
│           ├── depth_colorized_*.png  # カラーマップ深度
│           └── metadata_*.txt         # メタデータ（キャリブレーション情報含む）
│
├── calibration_data.json          # キャリブレーションデータ ⭐
│
├── test_pipeline.py               # 動作確認スクリプト
├── capture_and_visualize.py       # 一般用可視化・保存スクリプト
├── analyze_depth.py               # 深度データ解析スクリプト
│
├── calibrate_realsense.py         # ⭐ Tare Calibration スクリプト
│
├── nutrition5k_style_scanner.py   # ⭐ Nutrition5k互換スキャナー（推奨）
├── analyze_nutrition5k_data.py    # ⭐ Nutrition5kデータ解析スクリプト
│
├── food_scanner.py                # 食材スキャン専用スクリプト（従来版）
├── analyze_food_scan.py           # 食材スキャンデータ解析スクリプト（従来版）
│
└── README.md                      # このファイル
```

**⭐ = 研究用途推奨**

---

## 📚 参考情報

### 公式リソース
- [librealsense GitHub](https://github.com/IntelRealSense/librealsense)
- [pyrealsense2-macosx](https://github.com/cansik/pyrealsense2-macosx)
- [macOS での既知の問題](https://github.com/IntelRealSense/librealsense/issues/11815)

### Nutrition5k データセット
- [Nutrition5k Dataset (Google Research)](https://github.com/google-research-datasets/Nutrition5k)
- [CVPR 2021 Paper](https://openaccess.thecvf.com/content/CVPR2021/papers/Thames_Nutrition5k_Towards_Automatic_Nutritional_Understanding_of_Generic_Food_CVPR_2021_paper.pdf)

### RealSense D405 仕様
- **推奨動作範囲:** 7-50cm
- **深度FOV (1280x720):** 89.5° x 76.4°
- **カラーFOV (1280x720):** 89.1° x 69.5°
- **深度精度:** ±1% @ 20cm（キャリブレーション時）

---

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

---

**開発者向けメモ:**
- すべてのスクリプトは macOS (Apple Silicon) で動作確認済み
- Nutrition5k互換スクリプトは研究用途に最適化
- キャリブレーション機能により体積推定精度が向上
- 複数フレーム平均により白い表面のノイズを約3倍削減
