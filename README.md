# briefing-board

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-323330?style=flat-square&logo=javascript&logoColor=white)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square&logo=opensourceinitiative&logoColor=white)](./LICENSE.MIT)

[日本語](./README.md) | [English](./README.en.md)

実装前の設計相談や方針決めで、AI が整理した論点と選択肢をローカルの Web 画面にまとめ、ブラウザ上で確認・回答できるエージェントスキルです。

チャットのやり取りだけで論点が流れてしまう場面や、合意が取れるまで実装を止めておきたいときに使います（単発の質問や小さな修正は、通常のチャット応答のほうが手軽です）。

## 目次

- [briefing-board](#briefing-board)
  - [目次](#目次)
  - [インストールと起動](#インストールと起動)
    - [インストール](#インストール)
    - [起動方法](#起動方法)
  - [使い方](#使い方)
  - [主な特徴](#主な特徴)
  - [動作環境と制約](#動作環境と制約)
  - [内部構成と詳細仕様](#内部構成と詳細仕様)
    - [細かな動作仕様](#細かな動作仕様)
    - [コンポーネントの役割](#コンポーネントの役割)
    - [詳細仕様ドキュメント](#詳細仕様ドキュメント)
  - [LICENSE](#license)

## インストールと起動

Python 3.11 以上で動作します（標準ライブラリの `tomllib` を使うため、追加パッケージは不要です）。

### インストール

**Agent Skills 対応環境へ導入する場合**

```bash
npx skills add DovahkiinYuzuko/briefing-board
```

**Antigravity プラグインとして導入する場合**

```bash
agy plugin install https://github.com/DovahkiinYuzuko/briefing-board
```

### 起動方法

エージェントとの会話で、以下のコマンドかフレーズを入力すると起動します。

- `/briefing-board`
- 「作戦会議したい」「ブリーフィングボードを開いて」「方針決めをしたい」

---

## 使い方

1. **ボードを開く**: スキルを呼び出すと、AI が論点と選択肢を整理してローカルサーバーを起動し、URL（`http://localhost:<PORT>/wip/<session-folder>/`）を案内します。
2. **ブラウザで選ぶ**: 各論点の判定（未決定 / 確定 / 差し戻し / 調査 / 見送り）と選択肢を選び、必要があればコメントや追加論点を書いて保存します。
3. **未決・差し戻しを詰める**: 下書き保存中や「未決定 / 差し戻し / 調査」の項目が残っている間は、AI は実装やタスク起票へ進まずにボードを更新します。確定・見送り済みの項目は「確定済みを隠す」スイッチで隠すことが可能です。
4. **完了して閉じる**: すべて確定または見送りになったら、タスク化の要否を確認したうえでセッションを `done/` へ移し、サーバーを止めて終了します。

---

## 主な特徴

- **`.gitignore`自動生成**: 初回作成時に `briefing-board/.gitignore`（`*` と `!.gitignore`）を自動で作るため、セッションファイルが Git 管理されないようになります。
- **プロジェクト別ポートと LAN 共有**: ローカルサーバーはプロジェクトごとの専用ポート（`8899..8998`）で立ち上がり、`0.0.0.0` で待ち受けるため同じ LAN 内のスマホやタブレットからも開くことが可能です。
- **多言語対応とまとめ出力**: ヘッダーから表示言語を切り替えられ、保存時に生成する `summary.md` も選択した言語に切り替わります。
- **設定の保持**: UI 言語や表示モードは全プロジェクト共通で、一覧の並び順や検索条件はプロジェクト単位で保存する仕組みです。

---

## 動作環境と制約

- **オフライン環境での表示**: 数式（`KaTeX 0.16.8`）、構文ハイライト（`Prism.js 1.29.0`）、フォント（Google Fonts: `Noto Sans JP` / `Noto Sans Mono`）は CDN から読み込むため、オフラインではプレーンテキスト表示になります（選択と保存はそのまま動きます）。
- **`file://` 直開き時の制限**: サーバーを使わずに HTML を直接開いても、閲覧と `decision.toml` のダウンロードまでは行うことが可能ですが、自動保存（`POST /api/save`）、`summary.md` 生成、設定保存（`/api/settings`）には `server.py` の HTTP URL でのアクセスが必要になります。
- **一覧画面の更新タイミング**: 一覧ページ（`briefing-board/index.html`）はセッションの作成・更新・アーカイブ時に静的に生成しています。フォルダを手動で移動したときだけ `new_briefing.py --rebuild-portal` で作り直してください。

---

## 内部構成と詳細仕様

<details>
<summary>ディレクトリ・スクリプトの役割、細かな仕様、詳細ドキュメントを開く</summary>

### 細かな動作仕様

- **ポート番号の算出**: 出力先ディレクトリのパスに対する CRC32 ハッシュから `8899..8998` の範囲で自動決定します（使用中の場合は `+20` まで空きポートを探索）。
- **言語の追加**: `skills/briefing-board/locales/` に JSON ファイルを追加すると対応言語を増やす事が可能です。
- **設定ファイルの保存先**: UI 言語・表示モードはスキル側の `skills/briefing-board/user_settings.json`、一覧の並び替え・検索条件はプロジェクト側の `portal_settings.json` に保存されます。
- **CDN と静的ファイル展開について**: 外部 Python パッケージやフロントエンドのビルド手順を省き、ローカルサーバーが起動できない環境でも `file://` で最低限の閲覧・ダウンロードができるようにしています。

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
