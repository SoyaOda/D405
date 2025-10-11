# RealSense D405 セットアップガイド

## 環境情報

- **OS**: macOS (Apple Silicon)
- **Python**: 3.9.6
- **カメラ**: Intel RealSense D405
- **ライブラリ**: pyrealsense2-macosx, opencv-python, numpy

## セットアップ完了済み ✅

1. Homebrew で librealsense インストール済み
2. Python 仮想環境作成済み (`venv/`)
3. pyrealsense2-macosx インストール済み
4. OpenCV インストール済み

## 重要事項 ⚠️

**macOS では sudo 権限が必要です**

すべての RealSense スクリプトは以下の形式で実行してください：

```bash
sudo /Users/moei/program/D405/venv/bin/python3 <スクリプト名>
```

## スクリプト一覧

### 1. test_pipeline.py
**基本的な動作確認用**

```bash
sudo /Users/moei/program/D405/venv/bin/python3 test_pipeline.py
```

- 深度・カラーストリームの起動確認
- 5フレームを取得してサイズを表示
- 動作確認が目的

### 2. capture_and_visualize.py
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

**保存されるファイル:**
- `color_<タイムスタンプ>.png` - カラー画像
- `depth_<タイムスタンプ>.png` - 深度画像（可視化版）
- `depth_raw_<タイムスタンプ>.npy` - 深度データ（生データ）

**保存先:** `captured_images/`

### 3. analyze_depth.py
**保存した深度データの解析用** 📊

```bash
python3 analyze_depth.py captured_images/depth_raw_<タイムスタンプ>.npy
```

**機能:**
- 深度データの統計情報表示（最小値、最大値、平均値など）
- 深度分布のヒストグラム表示
- 深度マップの可視化

**注意:** このスクリプトは sudo 不要です（保存済みデータを読むだけ）

---

## 🍎 食材スキャン専用システム

D405 のベストプラクティスに基づいた食材スキャン専用スクリプトです。

### Nutrition5k スタイルスキャナー ⭐ **NEW**

Google Research の Nutrition5k データセットの撮像プロトコルに基づいた実装です。

#### 6. nutrition5k_style_scanner.py
**Nutrition5k 互換の食材スキャナー（研究用途）** 🔬

```bash
sudo /Users/moei/program/D405/venv/bin/python3 nutrition5k_style_scanner.py [食材名] [平均化フレーム数]
```

**Nutrition5k 仕様:**
- **深度エンコーディング:** 16-bit PNG（1m = 10,000ユニット）
- **最大深度:** 0.4m（4,000ユニット）← Nutrition5k 仕様
- **オーバーヘッド撮影:** 真上からの撮影を想定
- **カラーマップ:** 青（近）→ 赤（遠）

**保存形式（Nutrition5k互換）:**
```
nutrition5k_data/imagery/realsense_overhead/
├── rgb_<dish_id>.png           # RGB画像
├── depth_raw_<dish_id>.png     # 生深度（16-bit）
├── depth_colorized_<dish_id>.png  # カラーマップ深度
└── metadata_<dish_id>.txt      # メタデータ
```

**操作方法:**
- `s` キー: マルチフレーム平均撮影（高品質）
- `c` キー: 単一フレーム撮影（クイック）
- `q` キー: 終了

**利点:**
- 研究データセットとの互換性
- 標準化されたデータフォーマット
- 他の研究者とのデータ共有が容易

#### 7. analyze_nutrition5k_data.py
**Nutrition5k形式データの解析ツール**

```bash
python3 analyze_nutrition5k_data.py [dish_id または 食材名]
```

**機能:**
- Nutrition5k形式データの読み込み
- 深度統計の表示（ユニット + メートル）
- 深度分布ヒストグラム
- RGB + 深度の可視化

### 4. food_scanner.py ⭐ 推奨（改良版）
**食材スキャン専用スクリプト（ベストプラクティス適用済み）** 🥗

```bash
sudo /Users/moei/program/D405/venv/bin/python3 food_scanner.py [食材名] [平均化フレーム数]
```

**例:**
```bash
# デフォルト（20フレーム平均）
sudo /Users/moei/program/D405/venv/bin/python3 food_scanner.py apple

# 滑らかな表面用（30フレーム平均）
sudo /Users/moei/program/D405/venv/bin/python3 food_scanner.py tomato 30

# テクスチャのある表面用（10フレーム平均）
sudo /Users/moei/program/D405/venv/bin/python3 food_scanner.py banana 10
```

**平均化フレーム数のガイドライン:**
- **テクスチャのある表面:** 10-15フレーム
- **白い/滑らかな表面:** 20-30フレーム
- **デフォルト:** 20フレーム

**ベストプラクティス適用内容:**

✅ **D405 最適設定**
- 推奨距離範囲：7-50cm（リアルタイム表示）
- Visual Preset: High Accuracy
- 高解像度：1280x720（FOV一致、位置合わせ精度最大）
  - ⚠️ 注意：640x480はFOV差により深度が拡大して見える問題あり

✅ **ポストプロセッシングフィルター（推奨順序）**
1. Decimation Filter - ノイズ削減
2. Spatial Filter - 平滑化
3. Temporal Filter - フレーム間一貫性向上
4. Hole Filling Filter - 欠損値補完

✅ **時間平均フィルター（重要！）** 🆕
- 複数フレーム（10-30フレーム）の中央値フィルター
- 深度=0（無効値）を除外して計算
- **ノイズ大幅削減**：白い表面で約3倍改善
- 動く物体でもアーティファクトなし

✅ **Color-Depth アライメント**
- カラー画像と深度画像の位置合わせ

**操作方法:**
- `s` キー: 複数フレームをキャプチャして保存（高品質、ノイズ削減版）
- `q` キー: 終了

**保存されるファイル（食材ごとにフォルダ分け）:**
- `color_<タイムスタンプ>.png` - カラー画像
- `depth_vis_<タイムスタンプ>.png` - 深度画像（可視化版）
- `depth_raw_<タイムスタンプ>.npy` - 深度データ（生データ）
- `metadata_<タイムスタンプ>.txt` - メタデータ（統計情報）

**保存先:** `food_scans/[食材名]/`

**画面表示:**
- 距離が 7-50cm の範囲内なら「OPTIMAL RANGE」（緑）
- 7cm 未満なら「TOO CLOSE」（オレンジ）
- 50cm 超なら「TOO FAR」（赤）

### 5. analyze_food_scan.py
**食材スキャンデータの解析・比較** 📊

```bash
python3 analyze_food_scan.py [食材名]
```

**例:**
```bash
python3 analyze_food_scan.py apple
```

**機能:**
- 食材のすべてのスキャンをリスト表示
- 個別スキャンの詳細解析
- 複数スキャンの比較
- 統計情報の可視化
- メタデータの表示

**使い方:**
1. 食材名を指定して実行
2. スキャン一覧が表示される
3. 番号を入力して個別解析、または 'all' で全スキャン比較

**注意:** このスクリプトは sudo 不要です

## 使用例

### 基本的なワークフロー

1. **動作確認**
   ```bash
   sudo /Users/moei/program/D405/venv/bin/python3 test_pipeline.py
   ```

2. **画像キャプチャ（一般用途）**
   ```bash
   sudo /Users/moei/program/D405/venv/bin/python3 capture_and_visualize.py
   # ウィンドウが表示されたら 's' キーで保存
   ```

3. **深度データ解析**
   ```bash
   python3 analyze_depth.py captured_images/depth_raw_20251010_223000.npy
   ```

### 🍎 食材スキャンのワークフロー（推奨）

1. **食材をスキャン**
   ```bash
   # リンゴをスキャン（デフォルト20フレーム平均）
   sudo /Users/moei/program/D405/venv/bin/python3 food_scanner.py apple

   # トマトをスキャン（滑らかな表面なので30フレーム平均）
   sudo /Users/moei/program/D405/venv/bin/python3 food_scanner.py tomato 30

   # カメラから 7-50cm の距離に食材を配置
   # 画面に "OPTIMAL RANGE" が表示されたら 's' キーで保存
   # ※ 's' キー押下後、指定フレーム数をキャプチャして自動的に平均化します
   # 複数角度から撮影する場合は、位置を変えて 's' を複数回押す
   # 完了したら 'q' キーで終了（または Ctrl+C）
   ```

2. **スキャンデータを確認**
   ```bash
   # 保存されたファイルを確認
   ls food_scans/apple/

   # 出力例：
   # color_20251010_120000.png
   # depth_vis_20251010_120000.png
   # depth_raw_20251010_120000.npy
   # metadata_20251010_120000.txt
   ```

3. **スキャンデータを解析**
   ```bash
   # リンゴのスキャン一覧を表示
   python3 analyze_food_scan.py apple

   # プロンプトが表示されたら：
   # - Enter または 0: 最新のスキャンを解析
   # - 1, 2, 3...: 指定番号のスキャンを解析
   # - all: すべてのスキャンを比較
   ```

4. **複数の食材を比較**
   ```bash
   # トマトもスキャン
   sudo /Users/moei/program/D405/venv/bin/python3 food_scanner.py tomato

   # バナナもスキャン
   sudo /Users/moei/program/D405/venv/bin/python3 food_scanner.py banana

   # それぞれ解析
   python3 analyze_food_scan.py tomato
   python3 analyze_food_scan.py banana
   ```

## トラブルシューティング

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
- **現在の実装：** food_scanner.py は 1280x720 に設定済み（推奨）

**FOV 比較：**
- 640x480: 深度 79.4° vs カラー 72.9° → **差が大きい** ❌
- 1280x720: 深度 89.5° vs カラー 89.1° → **ほぼ一致** ✅

## ファイル構成

```
D405/
├── venv/                      # Python 仮想環境
├── captured_images/           # 一般キャプチャ画像の保存先
│   ├── color_*.png
│   ├── depth_*.png
│   └── depth_raw_*.npy
├── food_scans/                # 食材スキャンデータの保存先
│   ├── apple/                 # 食材ごとにフォルダ分け
│   │   ├── color_*.png
│   │   ├── depth_vis_*.png
│   │   ├── depth_raw_*.npy
│   │   └── metadata_*.txt
│   ├── tomato/
│   └── banana/
├── test_pipeline.py           # 動作確認スクリプト
├── capture_and_visualize.py   # 一般用可視化・保存スクリプト
├── analyze_depth.py           # 深度データ解析スクリプト
├── food_scanner.py            # ⭐ 食材スキャン専用スクリプト
├── analyze_food_scan.py       # 食材スキャンデータ解析スクリプト
└── README.md                  # このファイル
```

## 参考情報

- [librealsense GitHub](https://github.com/IntelRealSense/librealsense)
- [pyrealsense2-macosx](https://github.com/cansik/pyrealsense2-macosx)
- [macOS での既知の問題](https://github.com/IntelRealSense/librealsense/issues/11815)
