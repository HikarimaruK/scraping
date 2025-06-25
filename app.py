import streamlit as st
import time
import random
import pandas as pd
from crawler import fetch_list_page, extract_detail_urls, fetch_detail_page, extract_elements
from utils import results_to_csv
import base64

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

# セッションステートで結果とCSVを保持
if 'results' not in st.session_state:
    st.session_state['results'] = []
if 'csv_bytes' not in st.session_state:
    st.session_state['csv_bytes'] = None
if 'columns' not in st.session_state:
    st.session_state['columns'] = []
if 'stop_flag' not in st.session_state:
    st.session_state['stop_flag'] = False
if 'detail_urls' not in st.session_state:
    st.session_state['detail_urls'] = []
if 'scraping' not in st.session_state:
    st.session_state['scraping'] = False

# 進捗・メッセージ用
progress_text = st.empty()
progress_bar = st.progress(0)

# スクレイピング開始/終了ボタンの制御
scraping = st.session_state['scraping']
stop_flag = st.session_state['stop_flag']

# ボタン表示
if not scraping:
    if st.button("スクレイピング開始", key="start_btn"):
        st.session_state['scraping'] = True
        st.session_state['stop_flag'] = False
        st.experimental_rerun()
else:
    if st.button("スクレイピング終了", key="stop_btn"):
        st.session_state['stop_flag'] = True
        st.session_state['scraping'] = False
        st.experimental_rerun()

# スクレイピング本体
if st.session_state['scraping'] and not st.session_state['stop_flag']:
    # 初期化
    st.session_state['results'] = []
    st.session_state['csv_bytes'] = None
    st.session_state['columns'] = []
    st.session_state['detail_urls'] = []
    results = []
    error_count = 0
    detail_urls_set = set()
    all_detail_urls = []
    # 1. 一覧ページ全取得→詳細URLリスト作成
    progress_text.info("一覧ページをクロール中...（準備中）")
    for page in range(1, num_pages + 1):
        if st.session_state['stop_flag']:
            break
        page_url = list_url.replace("<<PAGE>>", str(page))
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
        for sel in selectors_to_use:
            detail_urls = extract_detail_urls(list_html, sel, base_url=page_url.split("/list")[0])
            for d_url in detail_urls:
                if d_url not in detail_urls_set:
                    detail_urls_set.add(d_url)
                    all_detail_urls.append(d_url)
    st.session_state['detail_urls'] = all_detail_urls
    total_detail_count = len(all_detail_urls)
    if st.session_state['stop_flag']:
        progress_text.info("スクレイピングを中止しました。")
    elif total_detail_count == 0:
        progress_text.warning("詳細ページURLが取得できませんでした。条件を見直してください。")
    else:
        # 2. 詳細ページ一括クロール
        progress_text.info(f"詳細ページをクロール中...（{total_detail_count}件）")
        for idx, d_url in enumerate(all_detail_urls):
            if st.session_state['stop_flag']:
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
            # 進捗バー更新
            progress_bar.progress(min(1.0, (idx+1)/total_detail_count))
            # 結果を即時反映
            st.session_state['results'] = results.copy()
            columns = ["詳細ページURL"] + [s["name"] for s in selectors]
            st.session_state['columns'] = columns
            df = pd.DataFrame(results, columns=columns)
            # 最新の表のみ表示
            st.session_state['latest_df'] = df
            # 表をリアルタイムで1つだけ表示
            st.dataframe(df)
            time.sleep(random.uniform(1, 2))  # 1～2秒ランダムスリープ
        # 完了処理
        if st.session_state['stop_flag']:
            progress_text.info(f"スクレイピングを中止しました。取得件数: {len(results)} / エラー: {error_count}")
        else:
            progress_text.success(f"スクレイピング完了！取得件数: {len(results)} / エラー: {error_count}")
        if results:
            columns = ["詳細ページURL"] + [s["name"] for s in selectors]
            csv_bytes = results_to_csv(results, columns)
            st.session_state['results'] = results
            st.session_state['csv_bytes'] = csv_bytes
            st.session_state['columns'] = columns
            st.session_state['latest_df'] = pd.DataFrame(results, columns=columns)
        else:
            st.warning("データが取得できませんでした。")
    st.session_state['scraping'] = False

# 結果があれば常にプレビューとダウンロード・コピーボタンを表示
def get_table_download_link(df):
    csv = df.to_csv(index=False, sep='\t', encoding='utf-8-sig')
    b64 = base64.b64encode(csv.encode()).decode()
    return f'<a href="data:text/csv;base64,{b64}" download="scraping_results.tsv">コピー用TSVダウンロード</a>'

def copy_to_clipboard_button(df):
    csv = df.to_csv(index=False, sep='\t', encoding='utf-8-sig')
    st.code(csv, language='text')
    st.markdown("<span style='color:gray'>上記を全選択してコピーできます（Excel/スプレッドシート貼付用）</span>", unsafe_allow_html=True)

# 表示
if st.session_state.get('results', []) and st.session_state.get('columns', []):
    df = st.session_state.get('latest_df', pd.DataFrame(st.session_state['results'], columns=st.session_state['columns']))
    st.download_button("CSVダウンロード", data=st.session_state['csv_bytes'], file_name="scraping_results.csv", mime="text/csv")
    st.markdown(get_table_download_link(df), unsafe_allow_html=True)
    copy_to_clipboard_button(df)
    # 表は1つだけ
    st.dataframe(df)

st.markdown("""
---
#### 補足
- 一覧ページURLのページ番号部分は `<<PAGE>>` で指定できます（例: `https://example.com/list?page=<<PAGE>>`）。
- 詳細ページURL抽出用CSSセレクタで `<<NUM>>` を使うと、繰り返し部分の番号を変数化できます。
- 各要素のCSSセレクタも、繰り返し部分やパターンに応じて `nth-child(<<NUM>>)` などで柔軟に指定できます。
""")
