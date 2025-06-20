# 誰でも使えるWebクローリングツール

## 概要
Streamlit＋BeautifulSoupで動作する、ノーコードWebクローリングツールです。  
一覧ページURL・詳細ページ抽出セレクタ・抽出要素リスト・ページ数を指定するだけで、  
誰でも簡単にWebデータをCSVで取得できます。

## 使い方

1. 必要なパッケージをインストール
    ```
    pip install -r requirements.txt
    ```

2. アプリを起動
    ```
    streamlit run app.py
    ```

3. Web画面で各種条件を入力し、「クロール開始」→「CSVダウンロード」

## ファイル構成

- `app.py` : Streamlitアプリ本体
- `crawler.py` : クローリング機能（BeautifulSoup/Selenium切替設計）
- `utils.py` : CSV出力など補助関数
- `requirements.txt` : 必要パッケージ
- `README.md` : このファイル

## 拡張ポイント

- **Selenium対応**: `crawler.py`の`fetch_list_page`/`fetch_detail_page`をSelenium実装に差し替えれば、JavaScriptレンダリング対応も可能です。
- **XPath対応**: `extract_elements`関数に`lxml`や`parsel`を使ってXPath抽出を追加できます。
- **例外処理強化**: リトライ、User-Agent指定、プロキシ対応なども容易に拡張できます。

## テスト

`crawler.py`の`__main__`ブロックにサンプルテストコードがあります。

---

## 注意事項

- 利用規約やrobots.txtを遵守し、過度なアクセスは控えてください。
- JavaScript描画が必要なサイトはSelenium版に切り替えてください。
