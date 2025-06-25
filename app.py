import streamlit as st
import time
import random
import pandas as pd
from crawler import fetch_list_page, extract_detail_urls, fetch_detail_page, extract_elements
from utils import results_to_csv
import base64
import concurrent.futures

# get_table_download_link, copy_to_clipboard_buttonの定義を必ず先に置く
def get_table_download_link(df):
    csv = df.to_csv(index=False, sep='\t', encoding='utf-8-sig')
    b64 = base64.b64encode(csv.encode()).decode()
    return f'<a href="data:text/csv;base64,{b64}" download="scraping_results.tsv">コピー用TSVダウンロード</a>'

def copy_to_clipboard_button(df):
    csv = df.to_csv(index=False, sep='\t', encoding='utf-8-sig')
    st.code(csv, language='text')
    st.markdown("<span style='color:gray'>上記を全選択してコピーできます（Excel/スプレッドシート貼付用）</span>", unsafe_allow_html=True)

st.set_page_config(page_title="万能スクレイピングツール", layout="wide")
st.title("万能スクレイピングツール")

st.markdown("### スクレイピング条件を入力してください")
list_url = st.text_input("一覧ページURL（<<PAGE>>でページ番号を指定）", "https://example.com/list?page=<<PAGE>>")
num_pages = st.number_input("スクレイピングする一覧ページ数（例: 5 → 5ページ分の全詳細ページをスクレイピング）", min_value=1, max_value=100, value=5)
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

# --- 改善1: ボタンは要素入力直後に必ず表示（進捗・表より上） ---
button_label = "スクレイピング終了（停止）" if st.session_state.get('scraping', False) else "スクレイピング開始"
button_clicked = st.button(button_label, key="main_btn")

# --- UIプレースホルダ（進捗・表はボタンより下に） ---
progress_text = st.empty()
progress_bar = st.empty()
table_placeholder = st.empty()

# --- セッション状態初期化 ---
if 'scraping' not in st.session_state:
    st.session_state['scraping'] = False
if 'stop_flag' not in st.session_state:
    st.session_state['stop_flag'] = False

# --- 改善2: ボタン押下時の状態遷移を明確化 ---
if button_clicked:
    if not st.session_state['scraping']:
        # 開始時のみスクレイピング処理を実行
        st.session_state['scraping'] = True
        st.session_state['stop_flag'] = False
        st.session_state['results'] = []
        st.session_state['csv_bytes'] = None
        st.session_state['columns'] = []
        st.session_state['detail_urls'] = []
    else:
        # 終了時はフラグだけ変更
        st.session_state['stop_flag'] = True

# --- スクレイピング本体 ---
if st.session_state['scraping']:
    results = []
    error_count = 0
    detail_urls_set = set()
    all_detail_urls = []
    progress_text.info("一覧ページをクロール中...（準備中）")
    def fetch_list(page):
        page_url = list_url.replace("<<PAGE>>", str(page))
        return (page, fetch_list_page(page_url))
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        list_results = list(executor.map(fetch_list, range(1, num_pages + 1)))
    for page, list_html in list_results:
        if not list_html:
            st.warning(f"一覧ページ取得失敗: {list_url.replace('<<PAGE>>', str(page))}")
            error_count += 1
            continue
        selectors_to_use = []
        if "<<NUM>>" in detail_selector and num_range_start is not None and num_range_end is not None:
            for n in range(int(num_range_start), int(num_range_end) + 1):
                selectors_to_use.append(detail_selector.replace("<<NUM>>", str(n)))
        else:
            selectors_to_use = [detail_selector]
        for sel in selectors_to_use:
            detail_urls = extract_detail_urls(list_html, sel, base_url=list_url.split("/list")[0])
            for d_url in detail_urls:
                if d_url not in detail_urls_set:
                    detail_urls_set.add(d_url)
                    all_detail_urls.append(d_url)
    st.session_state['detail_urls'] = all_detail_urls
    total_detail_count = len(all_detail_urls)
    if total_detail_count == 0:
        progress_text.warning("詳細ページURLが取得できませんでした。条件を見直してください。")
        st.session_state['scraping'] = False
        st.session_state['stop_flag'] = False
    else:
        progress_text.info(f"詳細ページをクロール中...（{total_detail_count}件）")
        for idx, d_url in enumerate(all_detail_urls):
            if st.session_state['stop_flag']:
                st.session_state['scraping'] = False
                st.session_state['stop_flag'] = False
                break
            progress_text.markdown(f"<span style='color:green'>詳細ページ取得中: {d_url} ({idx+1}/{total_detail_count})</span>", unsafe_allow_html=True)
            d_html = fetch_detail_page(d_url)
            if not d_html:
                st.warning(f"詳細ページ取得失敗: {d_url}")
                error_count += 1
                continue
            elements = extract_elements(d_html, selectors)
            row = {"詳細ページURL": d_url}
            row.update(elements)
            results.append(row)
            st.session_state['results'] = results.copy()
            columns = ["詳細ページURL"] + [s["name"] for s in selectors]
            st.session_state['columns'] = columns
            df = pd.DataFrame(results, columns=columns)
            st.session_state['csv_bytes'] = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            progress_bar.progress(min(1.0, (idx+1)/total_detail_count))
            table_placeholder.dataframe(df, key="latest_result_table")
            time.sleep(random.uniform(1, 2))
        if st.session_state['stop_flag']:
            progress_text.info(f"スクレイピングを中止しました。取得件数: {len(results)} / エラー: {error_count}")
        else:
            progress_text.success(f"スクレイピング完了！取得件数: {len(results)} / エラー: {error_count}")
        st.session_state['scraping'] = False
        st.session_state['stop_flag'] = False

# --- 結果表示 ---
if st.session_state.get('results', []) and st.session_state.get('columns', []):
    df = pd.DataFrame(st.session_state['results'], columns=st.session_state['columns'])
    st.download_button("CSVダウンロード", data=st.session_state['csv_bytes'], file_name="scraping_results.csv", mime="text/csv")
    st.markdown(get_table_download_link(df), unsafe_allow_html=True)
    copy_to_clipboard_button(df)
    table_placeholder.dataframe(df, key="latest_result_table")

st.markdown("""
---
#### 補足
- 一覧ページURLのページ番号部分は `<<PAGE>>` で指定できます（例: `https://example.com/list?page=<<PAGE>>`）。
- 詳細ページURL抽出用CSSセレクタで `<<NUM>>` を使うと、繰り返し部分の番号を変数化できます。
- 各要素のCSSセレクタも、繰り返し部分やパターンに応じて `nth-child(<<NUM>>)` などで柔軟に指定できます。
""")
