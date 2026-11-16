# briefing-board

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-323330?style=flat-square&logo=javascript&logoColor=white)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square&logo=opensourceinitiative&logoColor=white)](./LICENSE.MIT)

[日本語](./README.md) | [English](./README.en.md)

実装前の設計相談や方針決めで、AI が整理した論点と選択肢をローカルの Web 画面にまとめて提示し、ブラウザ上で判定やコメントを回収できるエージェントスキルです。

チャットの長文往復で論点が流れたり、合意前に AI が実装を進めてしまったりするのを防ぎたい場面に向いています。一方で、単発の質問や修正箇所が明らかな作業では、通常のチャット応答のほうが手早く済みます。

## 目次

- [インストールと起動](#インストールと起動)
  - [インストール](#インストール)
  - [起動方法](#起動方法)
- [使い方](#使い方)
- [主な特徴](#主な特徴)
- [動作環境と制約](#動作環境と制約)
- [内部構成と詳細仕様](#内部構成と詳細仕様)
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
- 「作戦会議したい」「ブリーフィングボードを開いて」「方針決めをしたい」

---

## 使い方

1. **会議を始める**: スキルを呼び出すと、AI が検討すべき論点と選択肢を整理してローカルサーバーを起動し、ブラウザで開く URL（`http://localhost:<PORT>/wip/<session-folder>/`）を案内します。
2. **ブラウザで選んで保存する**: 案内された URL を開き、各論点の判定（未決定 / 確定 / 差し戻し / 調査 / 見送り）と選択肢を選びます。必要に応じてコメントや追加したい論点を入力して保存します。
3. **未決・差し戻しの調整**: 下書き保存中、または未決定・差し戻し・調査の論点が残っている間は、AI は実装やタスク起票へ進みません。回答や調査結果を反映してボードが更新され、確定・見送り済みの論点は「確定済みを隠す」スイッチで非表示にできます。
4. **完了とアーカイブ**: すべての論点が確定または見送りになったら、タスク化の要否を確認したうえでセッションを `done/` へ移動し、サーバーを停止して終了します。

---

## 主な特徴

- **リポジトリを汚さない出力**: 出力先ディレクトリ（`briefing-board/`）の初回作成時に、`*` と `!.gitignore` のみを記載した `.gitignore` を自動生成します。
- **プロジェクト別ポートと LAN 共有**: 出力先パスの CRC32 ハッシュから `8899..8998` の範囲でポートを自動決定します（使用中の場合は `+20` まで探索）。`0.0.0.0` で待ち受けるため、同一 LAN 内のスマートフォンやタブレットからも開けます。
- **多言語対応と決定まとめ出力**: ヘッダーから表示言語を切り替えられ、保存時に生成される `summary.md` も選択中の言語で出力されます。標準では日本語・英語を同梱しており、`skills/briefing-board/locales/` に JSON ファイルを追加することで言語を増やせます。
- **設定の永続化**: UI 言語と表示モードはスキル側の `skills/briefing-board/user_settings.json` に全プロジェクト共通で保存され、一覧画面の並び替えや検索条件はプロジェクト側の `portal_settings.json` に保存されます。

---

## 動作環境と制約

- **数式・コード表示・フォントの CDN 依存**: KaTeX（0.16.8）、Prism.js（1.29.0）、Google Fonts（Noto Sans JP / Noto Sans Mono）は CDN から読み込みます。外部 Python パッケージやフロントエンドのビルド手順を不要にするための選択です。オフライン環境では数式や構文ハイライトがプレーンテキスト表示になりますが、選択操作と保存自体は動作します。
- **`file://` 直開き時の機能制限**: ローカルサーバーが起動できない環境でも閲覧と `decision.toml` のダウンロードができるよう、静的ファイルをすべてセッションフォルダへ展開しています。ただし `file://` 経由では自動保存（`POST /api/save`）、`summary.md` の生成、設定保存（`/api/settings`）は動作しないため、これらを使う場合は `server.py` の HTTP URL からアクセスします。
- **一覧画面の静的生成**: セッション一覧（`briefing-board/index.html`）はセッションの作成・更新・アーカイブ時にビルドされます。常駐データベースやファイル監視を持たない構成のため、フォルダを手動で移動した場合のみ `new_briefing.py --rebuild-portal` で再生成します。

---

## 内部構成と詳細仕様

<details>
<summary>ディレクトリ・スクリプトの役割一覧および詳細仕様リンクを開く</summary>

### コンポーネントの役割

| パス | 役割 |
| :--- | :--- |
| `plugin.json` | Antigravity プラグイン用のマニフェスト定義。 |
| `skills/briefing-board/SKILL.md` | エージェント向けの実行プロトコル（5 ステップ、決定木、作業開始禁止ガード）の定義。 |
| `skills/briefing-board/scripts/new_briefing.py` | 入力 TOML/JSON のスキーマ検証、セッションの作成・更新（`--update-session`）、完了検証付きアーカイブ（`--archive <session-folder>`、サーバー停止は別処理）、一覧再構築（`--rebuild-portal`）、サーバー起動の制御。 |
| `skills/briefing-board/scripts/server.py` | ローカル HTTP サーバー（`GET /api/decision`, `POST /api/save`, `GET/POST /api/settings`, `POST /api/shutdown`）と `summary.md` 自動生成の担当。 |
| `skills/briefing-board/scripts/briefing_common.py` | TOML/JSON の読み込み、プロジェクト別ポート番号の算出、`user_settings.json` / `portal_settings.json` の読み書きなどの共通処理。 |
| `skills/briefing-board/resources/` | DADS トークン準拠のフロントエンド実装（`index.html`, `portal.html`, `app.js`, `style.css`）。 |
| `skills/briefing-board/locales/` | 多言語定義ファイル（`en.json`, `ja.json`）。 |
| `skills/briefing-board/references/` | スキーマ仕様、CLI リファレンス、入力テンプレート。 |

### 詳細仕様ドキュメント

- スキル定義本体: [SKILL.md](./skills/briefing-board/SKILL.md)
- CLI 引数・API エンドポイント仕様（開発・動作確認向け）: [cli_reference.md](./skills/briefing-board/references/cli_reference.md)
- 入出力 TOML（`briefing.toml` / `decision.toml`）スキーマ仕様: [schema_specification.md](./skills/briefing-board/references/schema_specification.md)
- 入力テンプレート: [agenda_template.toml](./skills/briefing-board/references/agenda_template.toml)

</details>

---

## LICENSE

[MIT](./LICENSE.MIT)

Third-Party → [NOTICE.md](./NOTICE.md)

本スキルの UI は[デジタル庁デザインシステム（DADS）](https://design.digital.go.jp/dads/)の仕様を参照して独自に実装したものであり、デジタル庁が直接作成または提供するものではありません。
