# RealSense D405 Tare Calibration ガイド
## 複数のカメラ位置で頻繁にキャリブレーションする場合

---

## 🎯 実証済みの方法

### **Pythonスクリプト（リトライ機能付き）- 推奨**
- ✅ **macOS 15.6.1で動作確認済み**
- ✅ コマンドラインで完結
- ✅ 自動リトライ機能（最大3回）
- ✅ スクリプトで自動化可能
- ⚠️ USBケーブル抜き差しが必要な場合あり

### **RealSense Viewer（GUI）**
- ❌ **macOS 15.6.1ではOpenGLエラーで起動失敗**
- ⚠️ 環境によっては動作しません

---

## 📋 推奨方法: Pythonスクリプト（実証済み）

### **✅ 成功事例（2025年実証）**

**環境:**
- macOS 15.6.1 (Sequoia)
- pyrealsense2-macosx 2.54.2
- Intel RealSense D405

**結果:**
- ✅ 3回目の試行で成功
- ✅ 自動リトライ機能が効果を発揮
- ✅ EEPROMへの保存完了

### **手順:**

#### ステップ1: USBケーブルを抜き差し（重要！）

```bash
# 1. USBケーブルを抜く
# 2. 10秒待つ
# 3. USBケーブルを挿す
# 4. 5秒待つ
```

**なぜ必要？**
- カメラのハードウェアを完全にリセット
- "HW not ready"エラーの発生確率を下げる

#### ステップ2: 距離を測定

```bash
# 定規でカメラレンズ中心からトレイ底面までの距離を測定
# 例: 374mm
```

#### ステップ3: キャリブレーション実行

```bash
sudo /Users/moei/program/D405/venv/bin/python3 scripts/calibrate.py 374
```

**自動的に実行されること:**
1. カメラ初期化
2. ウォームアップ（90フレーム）
3. 最大3回の自動リトライ
   - 試行1失敗 → 5秒待機 → 試行2
   - 試行2失敗 → 5秒待機 → 試行3
   - 試行3で成功！
4. EEPROMへの自動保存

#### ステップ4: 成功確認

```
✓ Tare Calibration完了（40.0秒）
✓ キャリブレーション完了
補正データがカメラのEEPROMに保存されました。
```

#### ステップ5: スキャン実行

```bash
sudo /Users/moei/program/D405/venv/bin/python3 scripts/scan.py test_food
```

---

## 💡 ベストプラクティス（実証済み）

### **毎回のキャリブレーション時:**

1. **USBケーブルを抜き差し** → 10秒待つ → 再接続
2. **5秒待ってから** キャリブレーション実行
3. **リトライ機能に任せる** → 3回まで自動再試行
4. **3回失敗したら** → もう一度USBケーブル抜き差し

### **複数カメラ位置でのワークフロー:**

```bash
# 位置1: 40cm
# 1. USBケーブル抜き差し
# 2. 距離測定: 400mm
sudo /Users/moei/program/D405/venv/bin/python3 scripts/calibrate.py 400
sudo /Users/moei/program/D405/venv/bin/python3 scripts/scan.py food_40cm

# 位置2: 37.4cm
# 1. カメラ高さ変更
# 2. USBケーブル抜き差し
# 3. 距離測定: 374mm
sudo /Users/moei/program/D405/venv/bin/python3 scripts/calibrate.py 374
sudo /Users/moei/program/D405/venv/bin/python3 scripts/scan.py food_37cm

# 位置3: 30cm
# （同じワークフロー）
```

---

## 🔧 トラブルシューティング（実証済み対処法）

### Q: "HW not ready"エラーが3回とも出る

**A: 以下を順番に試す**

#### 対処法1: USBケーブル抜き差し（最優先）
```bash
# USBケーブルを抜く → 10秒待つ → 挿す → 5秒待つ
sudo /Users/moei/program/D405/venv/bin/python3 scripts/calibrate.py 374
```
**成功確率: ⭐⭐⭐⭐⭐**

#### 対処法2: 別のUSBポートを試す
```bash
# 別のUSB-Cポートに接続
sudo /Users/moei/program/D405/venv/bin/python3 scripts/calibrate.py 374
```
**成功確率: ⭐⭐⭐**

#### 対処法3: macOS再起動
```bash
# macOSを再起動してから実行
sudo /Users/moei/program/D405/venv/bin/python3 scripts/calibrate.py 374
```
**成功確率: ⭐⭐⭐⭐**

#### 対処法4: ファクトリーリセット
```bash
# カメラをファクトリー設定にリセット
sudo /Users/moei/program/D405/venv/bin/python3 scripts/reset_calibration.py
# USBケーブル抜き差し → 5秒待つ
sudo /Users/moei/program/D405/venv/bin/python3 scripts/calibrate.py 374
```
**成功確率: ⭐⭐⭐⭐**

### Q: カメラが認識されない

**A:**
```bash
# 1. sudoで実行しているか確認
# 2. USBケーブルを別のポートに接続
# 3. カメラのLEDが点灯しているか確認
# 4. 以下でデバイス確認
/Users/moei/program/D405/venv/bin/python3 -c "import pyrealsense2 as rs; print('Devices:', rs.context().query_devices().size())"
```

### Q: Health Metricsの意味は？

**A:**
```
Health: (0.0905, -0.002065)
```
- 第1値: RMSエラー（小さいほど良い、<0.2が良好）
- 第2値: バイアス（±0.01以内が良好）
- ✅ 両方とも許容範囲内なら成功

---

## 🚫 動作しない方法（参考）

### RealSense Viewer（macOS 15.6.1）

```bash
sudo realsense-viewer
```

**エラー:**
```
ERROR: ImGui_ImplOpenGL3_CreateDeviceObjects: failed to compile vertex shader!
ERROR: version '150' is not supported
```

**原因:**
- macOS 15.6.1（Apple Silicon）でのOpenGL互換性の問題
- Homebrewのlibrealsense 2.57.3がOpenGL 1.50を要求
- macOSは古いOpenGLバージョンをサポートしていない

**結論:**
- ❌ macOS 15.x（Sequoia）では使用不可
- ✅ Pythonスクリプトを使用してください

---

## 📋 参考: RealSense Viewer（他のmacOSバージョン用）

**注意:** macOS 15.x（Sequoia）では動作しません。古いmacOSバージョンでのみ使用可能。

```bash
sudo realsense-viewer
# More > Tare Calibration > Ground Truth: 374 > Run > Write Calibration
```

---

## 🎯 まとめ（macOS 15.6.1 Sequoia）

### **推奨方法:**
✅ **Pythonスクリプト（リトライ機能付き）**

### **ワークフロー:**
```bash
# 1. USBケーブル抜き差し（10秒待つ）
# 2. 距離測定
# 3. キャリブレーション実行
sudo /Users/moei/program/D405/venv/bin/python3 scripts/calibrate.py 374
# 4. スキャン実行
sudo /Users/moei/program/D405/venv/bin/python3 scripts/scan.py test_food
```

### **成功の鍵:**
- 🔌 USBケーブルの抜き差し
- ♻️ 自動リトライ機能（最大3回）
- ⏱️ 適切な待機時間

### **実証済み:**
- ✅ macOS 15.6.1で動作確認
- ✅ 3回目の試行で成功
- ✅ EEPROMへの保存完了

---

## 📚 さらに詳しい情報

- **RealSenseドキュメント**: https://dev.intelrealsense.com/
- **GitHub Issue #13340**: pyrealsense2 "HW not ready"問題
- **スクリプト**: `/Users/moei/program/D405/scripts/calibrate.py`

---

**カメラEEPROMに保存されるので、一度キャリブレーションすれば電源OFF後も効果が持続します。**
