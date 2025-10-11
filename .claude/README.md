# Claude Code + Serena MCP 設定

このディレクトリでは、Serena MCPがデフォルトで有効になっています。

## 自動設定内容

- **MCP サーバー**: Serena
- **起動コマンド**: `uvx --from git+https://github.com/oraios/serena serena-mcp-server`

## 使い方

このディレクトリでClaude Codeを起動すると、自動的にSerena MCPが利用可能になります。

## Serena MCPについて

Serenaは、プロジェクトの記憶・コンテキスト管理を行うMCPサーバーです。
以下の機能を提供します：

- プロジェクトに関する情報の記憶
- 過去のやり取りのコンテキスト保持
- プロジェクト固有の知識ベース

## データの保存場所

Serenaのデータは以下のディレクトリに保存されます（.gitignoreに含まれています）：

- `.serena/`
- `memories/`

## 注意事項

- 初回起動時は、Serenaのインストールに時間がかかる場合があります
- uvが必要です（Homebrewでインストール済み）
