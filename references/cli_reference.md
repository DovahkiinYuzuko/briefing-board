---
type: Reference
description: briefing-board スキルに同梱される Python スクリプト（new_briefing.py, server.py）の全コマンドライン引数、API エンドポイント、終了コード、実行例を網羅した仕様書。
tags: ["@BriefingBoard", "@CLI", "@Reference"]
links:
  - ../SKILL.md
  - ./schema_specification.md
---

# briefing-board CLI スクリプト仕様書

## 目次 (Contents)
- [1. `new_briefing.py`（セッション生成・更新・ポータル再構築）](#1-new_briefingpyセッション生成更新ポータル再構築)
- [2. `server.py`（軽量ローカルサーバー＆自動保存）](#2-serverpy軽量ローカルサーバー自動保存)
- [3. ユースケース別実行例](#3-ユースケース別実行例)

---

## 1. `new_briefing.py`（セッション生成・更新・ポータル再構築）

入力 TOML/JSON のスキーマ検証、個別セッションフォルダ（`briefing-board/wip/001-...`）の生成・更新、`briefing-board/.gitignore` の自動配置、静的アセット・`locales_data.js` の配備、カンバンポータルの更新、およびローカルサーバーの起動を行うスクリプトです。外部パッケージ不要で Python 3.11+ 標準ライブラリのみで動作します。

### コマンドライン引数一覧

| 引数名 | 短縮形 | 型 | デフォルト値 | 必須 | 説明 |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `--input` | `-i` | String (パス) | `None` | △ | 入力となる検討アジェンダ TOML/JSON ファイルへのパス。`--rebuild-portal` 指定時は省略可能。 |
| `--rebuild-portal` | なし | Flag | `False` | △ | **ポータル再生成専用フラグ**。既存の `wip/` および `done/` を走査して `briefing-board/index.html` のみを再ビルドします。 |
| `--update-session` | なし | String | `None` | 任意 | 既存セッションフォルダ名またはパスを指定し、アセットと `briefing.toml` を上書き更新します（既存 `decision.toml` は `previousDecision` として引き継ぎます）。 |
| `--topic` | `-t` | String | 入力ファイル名 | 任意 | 新規セッションフォルダ名に使用するトピック名スラッグ。 |
| `--title` | なし | String | `None` | 任意 | 入力ファイルの `title` を一時的に上書きします。 |
| `--output` | `-o` | String (パス) | `briefing-board` | 任意 | 出力先ルートディレクトリ（プロジェクトルート直下の `briefing-board`）。 |
| `--port` | `-p` | Integer | プロジェクト別自動算出 (`8899..8998`) | 任意 | ローカルサーバーのポート番号（使用中なら `+20` まで自動探索）。 |
| `--no-serve` | なし | Flag | `False` | 任意 | サーバーを起動せず静的ファイル生成のみで終了します。 |

### 主な終了コード
- `0`: 正常終了
- `1`: エラー終了（TOML スキーマ違反、リソース欠落、読み込み失敗など）

---

## 2. `server.py`（軽量ローカルサーバー＆自動保存）

プロジェクトの `briefing-board/` フォルダを配信ルートとし、決定事項の保存・復元、ハイブリッド設定の永続化、およびサーバー停止を処理するローカル HTTP サーバーです。

### コマンドライン引数一覧

| 引数名 | 短縮形 | 型 | デフォルト値 | 必須 | 説明 |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `--dir` | `-d` | String (パス) | `None` | 任意 | 配信対象のディレクトリパス（未指定時はカレントディレクトリの `briefing-board` のみを厳格に参照）。 |
| `--port` | `-p` | Integer | プロジェクト別自動算出 (`8899..8998`) | 任意 | リッスンポート番号（使用中なら `+20` まで自動探索）。 |

### 提供 API エンドポイント

1. **`GET /api/decision?target_path=<path>`**:
   - 指定された `decision.toml` が存在すればパースして `{"status": "ok", "exists": true, "data": {...}}` を返却します（パストラバーサル防止ガード付き）。存在しない場合は `{"status": "ok", "exists": false, "data": null}` を返却します。
2. **`POST /api/save`**:
   - リクエストボディ: `{ "toml": "...", "target_path": "briefing-board/wip/001-.../decision.toml" }`
   - `decision.toml` と同時に、現在のユーザー言語設定に応じた `summary.md` を自動生成して保存します。
3. **`GET /api/settings` / `POST /api/settings`**:
   - **ユーザー設定 (`<skill_root>/user_settings.json`)**: `language`（デフォルト `"en"`）、`view_mode` を全プロジェクト共通で永続化します（スキルルートは `__file__` 基準で動的解決）。
   - **ポータル設定 (`<serve_dir>/portal_settings.json`)**: `sort_key`, `sort_order`, `search_query` をプロジェクト単位で永続化します。
4. **`POST /api/shutdown`**:
   - サーバーを安全に停止し、`<serve_dir>/.server.pid` を削除します。

---

## 3. ユースケース別実行例

※ `<SKILL_DIR>` は本スキル（`briefing-board`）の配置ディレクトリに読み替えて実行してください。

### 1. 新規セッション作成（静的ビルドのみ）
```bash
python "<SKILL_DIR>/scripts/new_briefing.py" --input ./briefing_input.toml --topic "loop-safety" --no-serve
```

### 2. 既存セッションの差し戻し更新（履歴・前回選択を保持）
```bash
python "<SKILL_DIR>/scripts/new_briefing.py" --input ./briefing_input.toml --update-session 001-2026-11-17-loop-safety --no-serve
```

### 3. サーバー単独起動
```bash
python "<SKILL_DIR>/scripts/server.py" --dir briefing-board
```

### 4. アーカイブ後のポータル再ビルド
```bash
python "<SKILL_DIR>/scripts/new_briefing.py" --rebuild-portal
```
