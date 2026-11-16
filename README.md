# briefing-board

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-323330?style=flat-square&logo=javascript&logoColor=white)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square&logo=opensourceinitiative&logoColor=white)](./LICENSE.MIT)

[日本語](./README.md) | [English](./README.en.md)

実装前の設計相談や技術選定において、AI エージェントが生成したアジェンダ定義（`briefing_input.toml`）からローカルの対話型 Web ダッシュボードとカンバンポータルを生成し、ユーザーの判断結果を構造化ファイル（`decision.toml` および `summary.md`）として収集するエージェントスキルです。

## 目次

- [解決する課題と用途（Why / When）](#解決する課題と用途why--when)
- [スキルとしての導入と起動方法](#スキルとしての導入と起動方法)
- [エージェントとの協調ワークフロー](#エージェントとの協調ワークフロー)
- [主な特徴](#主な特徴)
- [設計上のスコープと制約](#設計上のスコープと制約)
- [内部構成と詳細リファレンス](#内部構成と詳細リファレンス)
- [LICENSE](#license)

---

## 解決する課題と用途（Why / When）

AI エージェントとテキストチャットだけで設計方針やトレードオフを相談する場合、以下の課題が発生しやすくなります。

- **論点と選択状態の埋没**: 複数の論点を同時に議論すると、チャットログが流れて「どの論点にどの選択肢を選んだか」の全体像を追いにくくなります。
- **比較情報の可読性低下**: コードスニペットや数式を含む選択肢のメリット・デメリットを、テキストの羅列だけで並べて比較することが困難です。
- **合意前の実装着手リスク**: 一部の論点が未決定（保留・差し戻し）のまま、エージェントが合意完了と解釈して実装や Issue 起票に進んでしまう場合があります。

`briefing-board` は、論点ごとのカード UI・選択肢比較・5択の決定ステータス・LaTeX 数式（KaTeX）および構文ハイライト（Prism.js）をローカルブラウザ上に分離して提示し、保存された `decision.toml` のステータスを機械的に判定することで、**全件確定（`COMPLETED` かつ `approve` / `partial` / `cancel`）になるまで実装へ進まない仕組み**を提供します。

実装前に複数のアーキテクチャ案を比較したい場面、仕様のトレードオフを整理したい場面、あるいは過去の検討履歴をプロジェクト単位で残したい場面に適しています。単一の事実確認や修正箇所が自明な作業には、通常のチャット応答のほうが適しています。

---

## スキルとしての導入と起動方法

本リポジトリは、AI エージェント（Antigravity 等）が読み込むスキルパッケージとして構成されています。

### 配置と動作要件

- **動作要件**: Python 3.11 以上（標準ライブラリ `tomllib` を使用するため、Python 側の追加パッケージは不要です）
- **配置先**: お使いのエージェント環境のスキルディレクトリ（例: `~/.gemini/config/skills/briefing-board/`）に本リポジトリ一式を配置します。

### 起動方法（会話トリガー）

エージェントとの会話の中で、以下のような指示やスラッシュコマンドを入力するとスキルが起動します。

- `/briefing-board`
- 「作戦会議したい」「ブリーフィングボードを開いて」「実装前の方針決めをしたい」

起動後、エージェントが `briefing_input.toml` の作成・セッションのビルド・ローカルサーバーの起動を自動で行い、アクセス用 URL（`http://localhost:<PORT>/wip/<session-folder>/`）を案内します。

---

## エージェントとの協調ワークフロー

セッションは 5 つのステップで進行します。

1. **アジェンダ作成**: エージェントが検討対象の論点・選択肢・補足メモ（`ai_notes`）を TOML 形式で作成します。
2. **検証・ビルド・起動**: スクリプトがスキーマを検証し、対象プロジェクトの `briefing-board/` 配下にセッションとカンバンポータルを生成してローカルサーバーを起動します。
3. **ブラウザでの判断・保存**: ユーザーが PC または同一 LAN 上の端末からダッシュボードを開き、各論点のアクション（`pending` / `approve` / `revise` / `investigate` / `cancel`）・選択肢・コメント・追加論点（`proposed_agendas`）を入力して保存します。
4. **決定木による分岐**: エージェントが `decision.toml` を読み込みます。`decision_status` が `"DRAFT"`、または `overall_action` が `"pending"` / `"revise_needed"` の間は実装や Issue 起票へ進まず、回答や調査結果を反映して `--update-session` で再提示します。
5. **アーカイブと終了**: 全件確定（`COMPLETED` かつ `approve` / `partial` / `cancel`）後、タスク化の要否を確認したうえで、完了セッションを `done/` へ移動し、ポータル再構築とサーバー停止を行います。

---

## 主な特徴

- **対象リポジトリを汚さない隔離設計**: 出力先ディレクトリ（`briefing-board/`）の初回生成時に、`*` と `!.gitignore` のみを記載した `.gitignore` を自動生成します。
- **プロジェクト別ポート算出と LAN 共有**: 出力先パスの CRC32 ハッシュから `8899..8998` の範囲でプロジェクト固有のポートを自動決定します（使用中の場合は `+20` まで探索）。サーバーは `0.0.0.0` で待ち受けるため、同一 LAN 内のスマートフォンやタブレットからも閲覧・保存できます。
- **UI と出力のバイリンガル対応**: ヘッダーの言語切り替えから英語（`en`）と日本語（`ja`）を切り替えられます。保存時に生成される `summary.md` も選択中の言語に合わせて出力されます。
- **ハイブリッド設定永続化**: UI 言語や表示モード（`auto` / `desktop` / `mobile`）はスキル側の `user_settings.json` に全プロジェクト共通で保存され、ポータルの並び替え・検索条件はプロジェクト側の `portal_settings.json` に保存されます。

---

## 設計上のスコープと制約

- **数式・コードハイライト・フォントの CDN 依存**: KaTeX（0.16.8）、Prism.js（1.29.0）、および Google Fonts（Noto Sans JP / Noto Sans Mono）は CDN 経由で読み込みます。これは Python 標準ライブラリのみで動作する軽量な配布構成を維持するための選択です。オフライン環境では数式や構文ハイライトがプレーンテキスト表示になりますが、ダッシュボード上の選択操作や保存処理自体は動作します。
- **`file://` フォールバック時の機能制限**: ローカルサーバーが起動できない環境でも HTML ファイルを直接開いて閲覧および `decision.toml` のダウンロード保存を行えるよう、静的アセットをすべてセッションフォルダへ展開する設計になっています。ただし、`file://` 経由では `POST /api/save` による自動保存、`summary.md` の自動生成、および `/api/settings` による設定永続化は動作しません。これらの機能を使う場合は `server.py` 経由の HTTP URL からアクセスします。
- **カンバンポータルの静的生成**: 一覧ポータル（`briefing-board/index.html`）はセッション生成・更新時に静的にビルドされます。常駐データベースや監視プロセスを持たない構成としているため、セッションフォルダを手動で `wip/` から `done/` へ移動した後は、`new_briefing.py --rebuild-portal` を実行して一覧を更新します。

---

## 内部構成と詳細リファレンス

<details>
<summary>ディレクトリ・スクリプトの役割一覧および詳細仕様リンクを開く</summary>

### コンポーネントの役割

| パス | 役割 |
| :--- | :--- |
| `SKILL.md` | エージェント向けの実行プロトコル（5ステップ、決定木、作業開始禁止ガード）の定義。 |
| `scripts/new_briefing.py` | 入力 TOML/JSON のスキーマ検証、セッションフォルダの生成・更新（`--update-session`）、ポータル再構築（`--rebuild-portal`）、サーバー起動の制御。 |
| `scripts/server.py` | ローカル HTTP サーバー（`GET /api/decision`, `POST /api/save`, `GET/POST /api/settings`, `POST /api/shutdown`）と `summary.md` 自動生成の担当。 |
| `scripts/briefing_common.py` | TOML/JSON の読み込み、プロジェクト別ポート番号の算出、`user_settings.json` / `portal_settings.json` の読み書きなどの共通処理。 |
| `resources/` | DADS トークン準拠のフロントエンド実装（`index.html`, `portal.html`, `app.js`, `style.css`）。 |
| `locales/` | 多言語定義ファイル（`en.json`, `ja.json`）。 |
| `references/` | スキーマ仕様、CLI リファレンス、入力テンプレート。 |

### 詳細仕様ドキュメント

- スキル定義本体: [SKILL.md](./SKILL.md)
- CLI 引数・API エンドポイント仕様（開発・動作確認向け）: [cli_reference.md](./references/cli_reference.md)
- 入出力 TOML（`briefing.toml` / `decision.toml`）スキーマ仕様: [schema_specification.md](./references/schema_specification.md)
- アジェンダ入力テンプレート: [agenda_template.toml](./references/agenda_template.toml)

</details>

---

## LICENSE

[MIT](./LICENSE.MIT)

Third-Party → [NOTICE.md](./NOTICE.md)

本スキルの UI は[デジタル庁デザインシステム（DADS）](https://design.digital.go.jp/dads/)の仕様を参照して独自に実装したものであり、デジタル庁が直接作成または提供するものではありません。
