# diavox

Googleの軽量なLLM <code>gemma3n</code> と <code>VoiceVox</code> を連携させて会話出来るアプリです。

### 実行方法
<code>src/apiversion.py</code> をCLI上で動かしてください。

<code>src/localversion.py</code> は開発中で動きません。

### 使用上の注意点
- 開発環境は <code>Python 3.13.3</code> です。よほど古いバージョンでなければ動くと思います。

- VoiceVoxを起動しておく必要があります。

- APIバージョンとローカルバージョンがありますが、現状正常に動くのはAPIバージョンのみです。

---
APIバージョンを使用するには、GoogleのGemini APIキーが必要になります。

Google AI StudioでAPIキーを作成した後、srcファイルのあるディレクトリ（ <code>README.md</code> と同じ階層）に <code>.env</code> ファイルを作成し、

<code>GEMINI_API_KEY = "APIKEY"</code> 

という形式でAPIキーを書き込み保存してください。