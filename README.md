# briefing-board

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-323330?style=flat-square&logo=javascript&logoColor=white)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square&logo=opensourceinitiative&logoColor=white)](./LICENSE.MIT)

[日本語](./README.md) | [English](./README.en.md)

実装前の設計相談や技術選定において、AI エージェントが整理した論点と選択肢からローカルの対話型 Web ダッシュボードとカンバンポータルを生成し、ユーザーの判断結果を構造化ファイル（`decision.toml` / `summary.md`）として回収するエージェントスキルです。

## 目次

- [briefing-board](#briefing-board)
  - [目次](#目次)
  - [インストールと起動](#インストールと起動)
    - [インストール](#インストール)
    - [起動方法](#起動方法)
  - [セッションの進行フロー](#セッションの進行フロー)
  - [主な機能と設計上の特徴](#主な機能と設計上の特徴)
  - [動作環境と制約](#動作環境と制約)
  - [内部構成と詳細リファレンス](#内部構成と詳細リファレンス)
    - [コンポーネントの役割](#コンポーネントの役割)
    - [詳細仕様ドキュメント](#詳細仕様ドキュメント)
  - [LICENSE](#license)

## インストールと起動

Python 3.11 以上が必要です（標準ライブラリ `tomllib` を使用するため、追加の Python パッケージは不要です）。

### インストール

お使いの環境に合わせて、いずれかのコマンドでインストールします。

**Agent Skills 対応環境へ導入する場合**

```bash
npx skills add DovahkiinYuzuko/briefing-board
```

**Antigravity プラグインとして導入する場合**

```bash
agy plugin install https://github.com/DovahkiinYuzuko/briefing-board
```

### 起動方法

エージェントとの会話で、以下のスラッシュコマンドまたはフレーズを入力するとスキルが起動します。

- `/briefing-board`
- 「作戦会議したい」「ブリーフィングボードを開いて」「実装前の方針決めをしたい」

---

## セッションの進行フロー

起動後のセッションは、次の 5 つのステップで進行します。

1. **アジェンダ作成**: エージェントが検討対象の論点・選択肢・補足メモ（`ai_notes`）を `briefing_input.toml` として作成します。
2. **検証・ビルド・起動**: スクリプトが入力スキーマを検証し、対象プロジェクトの `briefing-board/` 配下にセッションとカンバンポータルを生成してローカルサーバーを起動し、アクセス用 URL（`http://localhost:<PORT>/wip/<session-folder>/`）を案内します。
3. **ブラウザでの判断・保存**: ユーザーがブラウザでダッシュボードを開き、各論点の判定（未決定 / 確定 / 差し戻し / 調査 / 見送り）・選択肢・コメント・追加論点を入力して保存します。
4. **確定状態の判定と再提示**: エージェントが保存された `decision.toml` を読み込みます。下書き保存中や、未決定・差し戻し・調査の論点が残っている間は実装や Issue 起票へ進まず、回答や調査結果を反映して `--update-session` でボードを更新します。
5. **アーカイブと終了**: 会議が完了し、すべての論点が確定または見送りになった後、タスク化の要否を確認したうえで、完了セッションを `done/` へ移動し、ポータル再構築とサーバー停止を行います。

---

## 主な機能と設計上の特徴

- **対象リポジトリを汚さない隔離設計**: 出力先ディレクトリ（`briefing-board/`）の初回生成時に、`*` と `!.gitignore` のみを記載した `.gitignore` を自動生成します。
- **プロジェクト別ポート算出と LAN 共有**: 出力先パスの CRC32 ハッシュから `8899..8998` の範囲でプロジェクト固有のポートを自動決定します（使用中の場合は `+20` まで探索）。サーバーは `0.0.0.0` で待ち受けるため、同一 LAN 内のスマートフォンやタブレットからも閲覧・保存できます。
- **UI と出力のバイリンガル対応**: ヘッダーの言語切り替えから英語（`en`）と日本語（`ja`）を切り替えられます。保存時に生成される `summary.md` も選択中の言語に合わせて出力されます。
- **ハイブリッド設定永続化**: UI 言語や表示モード（`auto` / `desktop` / `mobile`）はスキル側の `user_settings.json` に全プロジェクト共通で保存され、ポータルの並び替え・検索条件はプロジェクト側の `portal_settings.json` に保存されます。

---

## 動作環境と制約

- **適用範囲と不向きな作業**: 複数のアーキテクチャ案や仕様のトレードオフを比較検討し、全件合意まで実装着手を止めたい場面に適しています。単一の事実確認や修正箇所が自明な作業では、ダッシュボード生成やブラウザ確認のオーバーヘッドを省くため、通常のチャット応答のほうが直接的です。
- **数式・コードハイライト・フォントの CDN 依存**: KaTeX（0.16.8）、Prism.js（1.29.0）、および Google Fonts（Noto Sans JP / Noto Sans Mono）は CDN 経由で読み込みます。これは Python 標準ライブラリのみで動作する構成を維持するための選択です。オフライン環境では数式や構文ハイライトがプレーンテキスト表示になりますが、ダッシュボード上の選択操作や保存処理自体は動作します。
- **`file://` フォールバック時の機能制限**: ローカルサーバーが起動できない環境でも HTML ファイルを直接開いて閲覧および `decision.toml` のダウンロード保存を行えるよう、静的アセットをすべてセッションフォルダへ展開する設計になっています。ただし、`file://` 経由では `POST /api/save` による自動保存、`summary.md` の自動生成、および `/api/settings` による設定永続化は動作しません。これらの機能を使う場合は `server.py` 経由の HTTP URL からアクセスします。
- **カンバンポータルの静的生成**: 一覧ポータル（`briefing-board/index.html`）はセッション生成・更新時に静的にビルドされます。常駐データベースや監視プロセスを持たない構成としているため、セッションフォルダを手動で `wip/` から `done/` へ移動した後は、`new_briefing.py --rebuild-portal` を実行して一覧を更新します。

---

## 内部構成と詳細リファレンス

<details>
<summary>ディレクトリ・スクリプトの役割一覧および詳細仕様リンクを開く</summary>

### コンポーネントの役割

| パス | 役割 |
| :--- | :--- |
| `plugin.json` | Antigravity プラグイン用のマニフェスト定義。 |
| `skills/briefing-board/SKILL.md` | エージェント向けの実行プロトコル（5ステップ、決定木、作業開始禁止ガード）の定義。 |
| `skills/briefing-board/scripts/new_briefing.py` | 入力 TOML/JSON のスキーマ検証、セッションフォルダの生成・更新（`--update-session`）、ポータル再構築（`--rebuild-portal`）、サーバー起動の制御。 |
| `skills/briefing-board/scripts/server.py` | ローカル HTTP サーバー（`GET /api/decision`, `POST /api/save`, `GET/POST /api/settings`, `POST /api/shutdown`）と `summary.md` 自動生成の担当。 |
| `skills/briefing-board/scripts/briefing_common.py` | TOML/JSON の読み込み、プロジェクト別ポート番号の算出、`user_settings.json` / `portal_settings.json` の読み書きなどの共通処理。 |
| `skills/briefing-board/resources/` | DADS トークン準拠のフロントエンド実装（`index.html`, `portal.html`, `app.js`, `style.css`）。 |
| `skills/briefing-board/locales/` | 多言語定義ファイル（`en.json`, `ja.json`）。 |
| `skills/briefing-board/references/` | スキーマ仕様、CLI リファレンス、入力テンプレート。 |

### 詳細仕様ドキュメント

- スキル定義本体: [SKILL.md](./skills/briefing-board/SKILL.md)
- CLI 引数・API エンドポイント仕様（開発・動作確認向け）: [cli_reference.md](./skills/briefing-board/references/cli_reference.md)
- 入出力 TOML（`briefing.toml` / `decision.toml`）スキーマ仕様: [schema_specification.md](./skills/briefing-board/references/schema_specification.md)
- アジェンダ入力テンプレート: [agenda_template.toml](./skills/briefing-board/references/agenda_template.toml)

</details>

---

## LICENSE

[MIT](./LICENSE.MIT)

Third-Party → [NOTICE.md](./NOTICE.md)

本スキルの UI は[デジタル庁デザインシステム（DADS）](https://design.digital.go.jp/dads/)の仕様を参照して独自に実装したものであり、デジタル庁が直接作成または提供するものではありません。
