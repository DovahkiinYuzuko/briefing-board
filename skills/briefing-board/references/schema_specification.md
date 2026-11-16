---
type: Specification
description: briefing-board スキルで使用する入出力 TOML（briefing.toml / decision.toml）の完全なデータ構造、必須キー、アクション定義、およびバリデーション仕様書。
tags: ["@BriefingBoard", "@Schema", "@Specification"]
links:
  - ../SKILL.md
  - ./agenda_template.toml
  - ./cli_reference.md
---

# briefing.toml / decision.toml スキーマ仕様書

## 目次 (Contents)
- [1. トップレベルスキーマ (`briefing.toml`)](#1-トップレベルスキーマ-briefingtoml)
- [2. アジェンダ項目スキーマ (`[[agenda]]`)](#2-アジェンダ項目スキーマ-agenda)
- [3. 選択肢スキーマ (`[[agenda.options]]`)](#3-選択肢スキーマ-agendaoptions)
- [4. 5択アクション定義と `overall_action` 自動算出](#4-5択アクション定義と-overall_action-自動算出)
- [5. 出力スキーマ (`decision.toml`)](#5-出力スキーマ-decisiontoml)
- [6. バリデーション仕様 (`new_briefing.py`)](#6-バリデーション仕様-new_briefingpy)

---

## 1. トップレベルスキーマ (`briefing.toml`)

入力 TOML のルートは必ずテーブル形式でなければなりません（Python 3.11+ 標準ライブラリ `tomllib` でパースされます）。

| フィールド名 | 型 | 必須 | 説明 | 例 |
| :--- | :--- | :---: | :--- | :--- |
| `title` | String | **必須** | 作戦会議ダッシュボードのメイン見出し。空文字は不可。 | `"反復ループ安全性とアーキテクチャ方針"` |
| `agenda` | Array of Tables | **必須** | `[[agenda]]` として定義する検討アジェンダ項目のリスト。最低 1 つ以上の要素が必須。 | 後述の「アジェンダ項目スキーマ」参照 |
| `subtitle` | String | 任意 | ダッシュボードのサブタイトル（概要説明）。 | `"実装前のアジェンダ検討と意思決定"` |
| `project` | String | 任意 | プロジェクト識別名。 | `"my-project"` |
| `ai_notes` | String | 任意 | AI が提示する前提条件・補足メモ。画面上は読み取り専用ブロックに表示され、ユーザーの自由メモ欄とは分離されます。 | `"""既存APIとの後方互換性を前提とします。"""` |

---

## 2. アジェンダ項目スキーマ (`[[agenda]]`)

`[[agenda]]` の各テーブルは、検討対象の 1 つの論点（カード）を表します。

| フィールド名 | 型 | 必須 | デフォルト値 | 説明 |
| :--- | :--- | :---: | :--- | :--- |
| `id` | String | **必須** | なし | アジェンダの一意な識別子。半角英数字・アンダースコア・ハイフン。同一ファイル内で**重複不可**。 |
| `domain` | String | **必須** | なし | 影響分野・ドメインタグ（例: `safety`, `performance`, `ui`）。 |
| `title` | String | **必須** | なし | アジェンダの見出しテキスト。 |
| `summary` | String | **必須** | なし | 課題や検討背景の概要説明文。 |
| `defaultAction` | String | 任意 | `"pending"` | 初期選択アクション。許容値: `pending`, `approve`, `revise`, `investigate`, `cancel` |
| `history` | Array of Tables | 任意 | `[]` | `[[agenda.history]]` 形式で過去ラウンド履歴（`round`, `action`, `comment`）を保持。カード内に折りたたみ表示されます。 |
| `formula` | String | 任意 | なし | 数学モデル・定式化（LaTeX 構文）。KaTeX でレンダリングされます（シングルクォートのリテラル文字列 `'...'` 推奨）。 |
| `code` | String | 任意 | なし | コードスニペット。Prism.js（autoloader）でシンタックスハイライトされます。 |
| `codeLang` | String | 任意 | `"go"` | コードの構文ハイライト言語（例: `go`, `python`, `typescript`, `toml`）。 |
| `optionsType` | String | 任意 | `"radio"` | 選択肢の UI 形式。`radio`（単一選択）または `checkbox`（複数選択）。 |
| `options` | Array of Tables | 任意 | `[]` | `[[agenda.options]]` 形式で定義する選択肢一覧。 |

---

## 3. 選択肢スキーマ (`[[agenda.options]]`)

| フィールド名 | 型 | 必須 | デフォルト値 | 説明 |
| :--- | :--- | :---: | :--- | :--- |
| `id` | String | **必須** | なし | 選択肢の一意な識別子。 |
| `label` | String | **必須** | なし | 選択肢の表示ラベル。 |
| `description` | String | 任意 | なし | トレードオフやメリット・デメリットの説明文。 |
| `recommended` | Boolean | 任意 | `false` | `true` の場合、DADS 推奨バッジが表示されます。 |
| `defaultSelected` | Boolean | 任意 | `false` | `true` の場合、初期状態で選択されます。 |

---

## 4. 5択アクション定義と `overall_action` 自動算出

### 個別アクション (`action`)
| アクション名 | 日本語表記 | セマンティクス |
| :--- | :--- | :--- |
| `pending` | **Pending / 未決定** | まだ判断を下していない・議論中。`pending` が残っている間は完了保存できません。 |
| `approve` | **Approve / 確定** | 提案された方針・選択肢を承認する。 |
| `revise` | **Revise / 差し戻し** | 前提条件や案の修正を求める。 |
| `investigate` | **Investigate / 調査** | 判断前に追加調査・検証を求める。 |
| `cancel` | **Cancel / 見送り** | 当該対応を見送る（取り下げる）。 |

### `overall_action` 自動算出ルール
`overall_action` は全アジェンダの `action` から自動算出されます（手動上書き不可）：

| 内訳 | `overall_action` | エージェントの挙動 |
| :--- | :--- | :--- |
| 1件でも `pending` を含む | `pending` | 議論継続（実装・起票禁止） |
| 1件でも `revise` または `investigate` を含む | `revise_needed` | 差し戻し・調査対応後、再提示（実装・起票禁止） |
| すべて `approve` | `approve` | `COMPLETED` 時のみ起票・次ステップ確認へ |
| すべて `cancel` | `cancel` | `COMPLETED` 時のみクローズ確認へ |
| `approve` と `cancel` の混在 | `partial` | `COMPLETED` 時のみ承認分の扱いを確認へ |

---

## 5. 出力スキーマ (`decision.toml`)

| フィールド名 | 型 | 説明 |
| :--- | :--- | :--- |
| `updated_at` | String | ISO 8601 形式の保存日時。 |
| `project` | String | プロジェクト名。 |
| `decision_status` | String | `"DRAFT"`（下書き・議論継続）または `"COMPLETED"`（全件判定完了）。 |
| `overall_action` | String | 自動算出された総合判定（`pending`, `revise_needed`, `approve`, `cancel`, `partial`）。 |
| `global_notes` | String | ユーザー専用の自由メモ欄の内容。 |
| `proposed_agendas` | Array of Tables | `[[proposed_agendas]]` 形式で記録される、ユーザーが追加リクエストした論点（`title`, `detail`）。空の場合は `proposed_agendas = []`。 |
| `decisions` | Array of Tables | `[[decisions]]` 形式で記録される各アジェンダの判定結果（`id`, `action`, `selected_options`, `comment`）。 |

---

## 6. バリデーション仕様 (`new_briefing.py`)

エラーが 1 つでも存在する場合、終了コード 1 で停止します：

1. ルート要素がテーブル（Dictionary）型であること。
2. ルートに非空の `title` が存在すること。
3. ルートに 1 つ以上の要素を含む `agenda` リストが存在すること。
4. すべての `agenda` 項目に `id`, `domain`, `title`, `summary` が存在すること。
5. `agenda` 項目間で `id` が重複していないこと。
6. `defaultAction` 指定時は `pending`, `approve`, `revise`, `investigate`, `cancel` のいずれかであること。
7. `history` 指定時はリスト型であること。
8. `options` 指定時は各要素に `id` と `label` が存在すること。
