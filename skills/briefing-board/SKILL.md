---
name: briefing-board
description: >-
  Generates a local DADS-compliant interactive dashboard for pre-implementation strategic discussions, technical tradeoff evaluations, and decision collection. Use when the user requests a briefing or strategy session (e.g., "作戦会議", "ブリーフィング", "方針決め", "briefing"), or when facing major architectural branches before writing production code.
---

# briefing-board

実装前の選択肢比較、トレードオフ検討、およびユーザーの意思決定を収集するための対話型ダッシュボードを提供するスキルです。

## ワークフロー進捗チェックリスト

```text
Briefing Progress:
- [ ] Step 1: 検討アジェンダ TOML（briefing_input.toml）を作成する
- [ ] Step 2: new_briefing.py で検証・ビルドし、サーバーを起動する
- [ ] Step 3: ユーザーへ直行URL・ポータルURLを案内して待機する
- [ ] Step 4: decision.toml を読み込み、決定木に従って次アクションを分岐する
- [ ] Step 5: 全件完了後にタスク化確認・done/ へアーカイブ・サーバー停止を行う
```

---

## Step 1: アジェンダ TOML の作成

[references/schema_specification.md](references/schema_specification.md) のスキーマに従い、[references/agenda_template.toml](references/agenda_template.toml) を参考に一時入力ファイル（例: `briefing_input.toml`）を作成します。

- AI からの前提メモ・補足は `ai_notes` に記述します（ユーザー専用の自由メモ欄は空欄のまま保たれます）。
- 各アジェンダの `defaultAction` は原則 `"pending"`（未決定）を使用します。
- 出力先の `briefing-board/` 配下には自動で `.gitignore`（`*` / `!.gitignore`）が生成されるため、対象プロジェクトの Git 履歴を汚しません。入力用の一時 TOML ファイルはプロジェクトの作業方針に沿った一時領域に置くか、セッション生成後に削除してください。

---

## Step 2: セッション生成とサーバー起動

スクリプトはブラックボックスとして実行します。詳細な引数は `--help` または [references/cli_reference.md](references/cli_reference.md) を参照してください。

- **依存関係**: Python 3.11 以上（標準ライブラリ `tomllib` を使用するため外部パッケージ不要）。
- `<SKILL_DIR>` は本スキル（`SKILL.md` があるフォルダ）のディレクトリパスを指定してください。

```bash
# 新規セッション作成・ポータル更新・サーバー起動（ポートはプロジェクト毎に自動決定）
python "<SKILL_DIR>/scripts/new_briefing.py" --input ./briefing_input.toml --topic "topic-slug"
```

- 既存セッションを差し戻し等で更新する場合は `--update-session <session-dir>` を使用します（既存の `decision.toml` が保持・復元されます）。
- エージェント環境からバックグラウンド常駐させる場合は `--no-serve` でビルド後、`scripts/server.py` をバックグラウンド実行してください。

---

## Step 3: ダッシュボードの案内

サーバー起動時に標準出力へ表示される URL を確認し、以下をユーザーへ案内して判断を待機します：

- **今回の作戦会議（直行URL）**: `http://localhost:<PORT>/wip/<session-folder>/`
- **カンバンポータル（全体一覧）**: `http://localhost:<PORT>/`
- **同一LAN端末（スマホ等）**: `http://<LAN-IP>:<PORT>/wip/<session-folder>/`
- **ローカルファイル（フォールバック）**: `briefing-board/wip/<session-folder>/index.html`

> [!NOTE]
> ダッシュボード UI はデフォルトで英語（`en`）表示になっており、ヘッダーの言語ドロップダウンから後から切り替え可能です（選択した言語はスキル設定へ永続化されます）。

---

## Step 4: 決定内容の受領と決定木（Decision Tree）

ユーザーから保存完了の通知を受けたら、対象セッションの `decision.toml` を読み込み、以下の決定木に従って処理します。

> [!CAUTION]
> **作業開始・先走り禁止ガード**:
> - `decision_status` が `"DRAFT"` の場合、または `overall_action` が `"pending"` / `"revise_needed"` の場合、**いかなる実装・本番コード編集・Issue 起票・`done/` への移動も絶対に行ってはいけません。**
> - `decision_status == "COMPLETED"`（`approve` / `partial` / `cancel`）を受領したターンであっても、**ユーザーへ決定内容の要約と次ステップの確認質問を返すことのみを行い、同一ターン内で `--archive` 移動・タスク起票・実装・サーバー停止などの状態変更ツールを絶対に呼び出してはいけません。** 必ずユーザーの明示的な許可の返答を待ってから、次のターンで実行してください。

```text
decision.toml を確認
 ├── decision_status == "DRAFT" または overall_action == "pending"
 │     → 会議継続中。global_notes / proposed_agendas / 各コメントに回答・議論し、
 │       必要に応じて --update-session でボードを更新する（実装・起票は禁止）。
 │
 ├── overall_action == "revise_needed"（revise または investigate を含む）
 │     → 差し戻し・追加調査を実施。調査結果や修正案を briefing_input.toml に反映
 │       （過去の選択・コメントは history へ記録）し、--update-session で再提示する。
 │
 └── decision_status == "COMPLETED" かつ overall_action が approve / partial / cancel
       → Step 5（タスク化確認・アーカイブ・サーバー停止）へ進む。
```

---

## Step 5: タスク化確認・アーカイブ・サーバー停止

決定完了（`COMPLETED` かつ `approve` / `partial` / `cancel`）後、**独断で起票・実装・アーカイブせず**、まず確認のみのターンとしてユーザーへ以下を確認します（この確認ターンでは状態変更ツールを実行しないこと）：

1. 決定事項を Issue やタスクとして起票するかどうか（`partial` の場合は承認分のみ対象）
2. 起票する場合の方式・規律（GitHub Issues、ローカル Issue 等）
3. セッションを `done/` へアーカイブし、サーバーを停止してよいか

ユーザーの明示的な許可と指示を受けて確認・タスク化が完了したら、以下を実施します：

1. 専用コマンドで対象セッションを `briefing-board/wip/` から `briefing-board/done/` へ移動し、カンバンポータルを自動再構築する（`COMPLETED` かつ `approve`/`partial`/`cancel` でない場合は安全ガードによりブロックされます）：
   ```bash
   python "<SKILL_DIR>/scripts/new_briefing.py" --archive <session-folder>
   ```
2. **バックグラウンドサーバーを停止する**：アーカイブ・ポータル再構築が完了したら（特に `wip/` に進行中セッションがなくなった場合）、バックグラウンドで常駐させていた `server.py` のタスク／プロセスを終了する（ポータルの停止ボタンまたは `POST /api/shutdown` でも停止可能）。
