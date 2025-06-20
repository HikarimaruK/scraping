import streamlit as st
import time
import random
from crawler import fetch_list_page, extract_detail_urls, fetch_detail_page, extract_elements
from utils import results_to_csv

st.set_page_config(page_title="誰でも使えるWebクローリングツール", layout="wide")
st.title("誰でも使えるWebクローリングツール")

st.markdown("### クロール条件を入力してください")
list_url = st.text_input("一覧ページURL（<<PAGE>>でページ番号を指定）", "https://example.com/list?page=<<PAGE>>")
num_pages = st.number_input("クロールする一覧ページ数（例: 5 → 5ページ分の全詳細ページをクロール）", min_value=1, max_value=100, value=5)
detail_selector = st.text_input("詳細ページURL抽出用CSSセレクタ（<<NUM>>で可変指定可）", "div.card > a")

# <<NUM>>が含まれている場合のみ範囲入力欄を表示
num_range_start, num_range_end = None, None
if "<<NUM>>" in detail_selector:
    st.markdown(":blue[※ <<NUM>> を含む場合、範囲指定で複数のリンクを抽出できます]")
    col_num1, col_num2 = st.columns(2)
    with col_num1:
        num_range_start = st.number_input("<<NUM>> 開始値", min_value=1, max_value=100, value=2, key="num_start")
    with col_num2:
        num_range_end = st.number_input("<<NUM>> 終了値", min_value=1, max_value=100, value=5, key="num_end")

st.markdown("#### 詳細ページから抽出したい要素リスト（最大20項目）")
element_count = st.slider("抽出要素数", min_value=1, max_value=20, value=2)

selectors = []
for i in range(element_count):
    col1, col2 = st.columns([3, 7])
    with col1:
        name = st.text_input(f"要素名{i+1}", f"要素{i+1}", key=f"name_{i}")
    with col2:
        selector = st.text_input(f"CSSセレクタ{i+1}", "", key=f"selector_{i}")
    selectors.append({"name": name, "selector": selector, "type": "css"})

# セッションステートで結果とCSVを保持
def get_session_state():
    if 'results' not in st.session_state:
        st.session_state['results'] = []
    if 'csv_bytes' not in st.session_state:
        st.session_state['csv_bytes'] = None
    if 'columns' not in st.session_state:
        st.session_state['columns'] = []
get_session_state()

submitted = st.button("クロール開始")

progress_text = st.empty()
progress_bar = st.progress(0)

if submitted:
    st.info("クロールを開始します。しばらくお待ちください。")
    results = []
    error_count = 0
    detail_urls_set = set()
    total_detail_count = 0
    try:
        for page in range(1, num_pages + 1):
            page_url = list_url.replace("<<PAGE>>", str(page))
            progress_text.markdown(f"<span style='color:blue'>一覧ページ取得中: {page_url}</span>", unsafe_allow_html=True)
            list_html = fetch_list_page(page_url)
            if not list_html:
                st.warning(f"一覧ページ取得失敗: {page_url}")
                error_count += 1
                continue
            # セレクタ生成
            selectors_to_use = []
            if "<<NUM>>" in detail_selector and num_range_start is not None and num_range_end is not None:
                for n in range(int(num_range_start), int(num_range_end) + 1):
                    selectors_to_use.append(detail_selector.replace("<<NUM>>", str(n)))
            else:
                selectors_to_use = [detail_selector]
            # 各セレクタで詳細URL抽出
            detail_urls = []
            for sel in selectors_to_use:
                detail_urls += extract_detail_urls(list_html, sel, base_url=page_url.split("/list")[0])
            for idx, d_url in enumerate(detail_urls):
                if d_url in detail_urls_set:
                    continue
                detail_urls_set.add(d_url)
                progress_text.markdown(f"<span style='color:green'>詳細ページ取得中: {d_url} ({len(results)+1}件目)</span>", unsafe_allow_html=True)
                d_html = fetch_detail_page(d_url)
                if not d_html:
                    st.warning(f"詳細ページ取得失敗: {d_url}")
                    error_count += 1
                    continue
                elements = extract_elements(d_html, selectors)
                row = {"詳細ページURL": d_url}
                row.update(elements)
                results.append(row)
                total_detail_count += 1
                progress_bar.progress(min(1.0, (total_detail_count / (num_pages * max(1, len(detail_urls))))))
                time.sleep(random.uniform(1, 2))  # 1～2秒ランダムスリープ
        st.success(f"クロール完了！取得件数: {len(results)} / エラー: {error_count}")
        if results:
            columns = ["詳細ページURL"] + [s["name"] for s in selectors]
            csv_bytes = results_to_csv(results, columns)
            st.session_state['results'] = results
            st.session_state['csv_bytes'] = csv_bytes
            st.session_state['columns'] = columns
        else:
            st.warning("データが取得できませんでした。")
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")

# 結果があれば常にプレビューとダウンロードボタンを表示
display_results = st.session_state.get('results', [])
display_csv = st.session_state.get('csv_bytes', None)
display_columns = st.session_state.get('columns', [])
if display_results and display_csv and display_columns:
    st.download_button("CSVダウンロード", data=display_csv, file_name="crawl_results.csv", mime="text/csv")
    st.dataframe(display_results)

st.markdown("""
---
#### 📝 補足・拡張ポイント
- JavaScriptレンダリングが必要な場合は、`crawler.py`の`fetch_list_page`/`fetch_detail_page`をSelenium実装に差し替え可能です。
- XPath対応は`extract_elements`関数に`lxml`や`parsel`を使って追加できます。
- 例外処理やリトライ、User-Agent指定、プロキシ対応なども拡張可能です。
- サンプルテストは`crawler.py`の`__main__`ブロックを参照してください。
""")
