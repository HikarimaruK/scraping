import pandas as pd
import io

def results_to_csv(results: list, columns: list) -> bytes:
    """抽出結果をCSVバイト列に変換"""
    df = pd.DataFrame(results, columns=columns)
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
