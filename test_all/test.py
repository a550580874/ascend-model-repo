import json
import re
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zipfile import ZipFile

import pandas as pd
import urllib3

from run_dify_workflow_direct import run_dify


BASE_DIR = Path(__file__).resolve().parent
TESTCASE_XLSX = BASE_DIR / "回归测试样例_中英分行.xlsx"
OUTPUT_DIR = BASE_DIR / "dify_regression_report"

QUERY_COLUMN_CANDIDATES = ["query", "用户输入", "问题", "用户问题"]
EXPECTED_COLUMN_CANDIDATES = ["期望输出", "期望", "expected_output", "expected", "预期输出", "预期结果"]
NON_ASCEND_EXPECTED = "非昇腾适配模型查询"
NON_ASCEND_EXPECTED_EN = "not an ascend adaptation model query"
QUERY_BLOCK_PATTERN = re.compile(
    r"^\s*((?:【查询\s*\d+\s*】)|(?:\[\s*Query\s*\d+\s*\]))\s*(.*?)\s*(?:→|->).*$",
    re.MULTILINE | re.IGNORECASE,
)
MAX_WORKERS = 4

warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def normalize_key(value: Any) -> str:
    text = normalize_text(value).lower()
    return re.sub(r"[\s_\-（）()]+", "", text)


def safe_json_dumps(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return str(obj)


def markdown_code_block(content: Any, lang: str = "json") -> str:
    if isinstance(content, str):
        text = content
    else:
        text = safe_json_dumps(content)
    return f"```{lang}\n{text}\n```"


def resolve_testcase_path() -> Path:
    return TESTCASE_XLSX


def resolve_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_writable_path(path: Path) -> Path:
    if not path.exists():
        return path
    try:
        with open(path, "a", encoding="utf-8"):
            return path
    except PermissionError:
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        return path.with_name(f"{path.stem}_{timestamp}{path.suffix}")


def looks_like_numbers_package(path: Path) -> bool:
    try:
        with ZipFile(path) as zf:
            names = set(zf.namelist())
        return "Index/Document.iwa" in names and "Metadata/BuildVersionHistory.plist" in names
    except Exception:
        return False


def read_testcase_dataframe(path: Path) -> pd.DataFrame:
    try:
        return pd.read_excel(path, engine="openpyxl")
    except Exception as exc:
        if looks_like_numbers_package(path):
            raise ValueError(
                f"测试文件不是标准 .xlsx，而是 Apple Numbers 文件改名而来: {path}。"
                "请先在 Numbers 或 Excel 中重新导出为真正的 .xlsx 后再执行。"
            ) from exc
        raise


def find_column(df: pd.DataFrame, candidates: List[str]) -> str:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate

    normalized_map = {normalize_key(col): col for col in df.columns}
    for candidate in candidates:
        matched = normalized_map.get(normalize_key(candidate))
        if matched:
            return matched

    raise KeyError(f"未找到列，候选列名: {candidates}")


def extract_expected_output(value: Any) -> str:
    text = normalize_text(value).replace("\u3000", " ")
    return re.sub(r"\s+", " ", text)


def extract_actual_output_from_answer(answer: Any) -> str:
    text = normalize_text(answer)
    if not text:
        return ""

    blocks: List[str] = []
    for prefix, body in QUERY_BLOCK_PATTERN.findall(text):
        prefix_clean = normalize_query_block_prefix(prefix)
        body_clean = re.sub(r"\s+", " ", body.strip())
        blocks.append(f"{prefix_clean} {body_clean}".strip())
    return "；".join(blocks)


def normalize_expected_output(value: Any) -> str:
    text = normalize_text(value).replace("\u3000", " ")
    text = text.replace(";", "；")
    text = re.sub(r"\s*；\s*", "；", text)
    text = re.sub(r"\s+", " ", text).strip()
    parts = [part.strip() for part in text.split("；") if part.strip()]
    normalized_parts = []
    for part in parts:
        normalized_parts.append(normalize_query_block_text(part))
    if normalized_parts:
        return "；".join(normalized_parts)
    return text


def normalize_query_block_prefix(prefix: str) -> str:
    text = normalize_text(prefix)
    match = re.search(r"(\d+)", text)
    if not match:
        return text
    number = match.group(1)
    return f"[Query{number}]"


def normalize_query_block_text(text: str) -> str:
    cleaned = normalize_text(text)
    cleaned = re.sub(r"^\[\s*query\s*(\d+)\s*\]\s*", lambda m: f"[Query{m.group(1)}] ", cleaned, flags=re.I)
    cleaned = re.sub(r"^【\s*查询\s*(\d+)\s*】\s*", lambda m: f"[Query{m.group(1)}] ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def is_non_ascend_expected(expected: str) -> bool:
    normalized = normalize_expected_output(expected).lower()
    return normalized in {NON_ASCEND_EXPECTED.lower(), NON_ASCEND_EXPECTED_EN}


def is_non_ascend_answer(answer: str, actual: str) -> bool:
    answer_text = normalize_text(answer)
    lowered = answer_text.lower()
    markers = [
        "这不是一个昇腾适配模型查询问题",
        "不是一个昇腾适配模型查询问题",
        "非昇腾",
        "非昇腾适配模型查询",
        "not an ascend adaptation model query",
    ]
    return any(marker in answer_text for marker in markers) or (not actual and not lowered.startswith("【查询"))


def compare_expected_vs_actual(expected: str, actual: str, answer: str) -> Tuple[bool, str]:
    expected_norm = normalize_expected_output(expected)
    actual_norm = normalize_expected_output(actual)

    if is_non_ascend_expected(expected_norm):
        if is_non_ascend_answer(answer, actual):
            return True, "符合预期（非昇腾适配模型查询）"
        return False, f"期望为非昇腾适配模型查询，但实际提取到查询块：{actual_norm or '无'}"

    if not expected_norm and not actual_norm:
        return True, "期望输出和实际提取输出均为空"
    if expected_norm == actual_norm:
        return True, "符合预期"
    if not actual_norm:
        return False, "answer 中未提取到任何查询块标题"
    return False, f"期望输出={expected_norm}；实际提取输出={actual_norm}"


def call_dify_with_retry(query: str, max_retries: int = 3) -> Dict[str, Any]:
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            return run_dify(query)
        except Exception as exc:
            last_exc = exc
            if attempt >= max_retries:
                break
            time.sleep(1.5 * attempt)
    raise RuntimeError(f"run_dify failed after {max_retries} attempts: {last_exc}")


def build_detail_markdown(raw_results: List[Dict[str, Any]]) -> str:
    lines = ["# 回归测试实际回复明细", ""]

    for item in raw_results:
        lines.extend(
            [
                f"## 问题 {item['序号']}",
                "",
                "### query",
                item.get("query", ""),
                "",
                "### 期望输出",
                item.get("expected_output", ""),
                "",
                "### 实际提取输出",
                item.get("extracted_output", ""),
                "",
                "### 执行结果",
                item.get("status", ""),
                "",
                "### 差异说明",
                item.get("diff", "") or "无",
                "",
                "### answer 原文",
                item.get("answer", "") or "",
                "",
                "### 原始 response",
                markdown_code_block(item.get("raw_response", {}), "json"),
                "",
                "---",
                "",
            ]
        )

    if len(raw_results) == 0:
        lines.extend(["测试文件为空，未执行任何用例。", ""])

    return "\n".join(lines)


def process_row(idx: int, total: int, row: pd.Series, query_col: str, expected_col: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    query = normalize_text(row.get(query_col))
    expected_output = extract_expected_output(row.get(expected_col))
    raw_response: Optional[Dict[str, Any]] = None
    answer = ""
    extracted_output = ""
    status = ""
    diff = ""

    try:
        raw_response = call_dify_with_retry(query)
        answer = normalize_text(raw_response.get("answer")) if isinstance(raw_response, dict) else ""
        extracted_output = extract_actual_output_from_answer(answer)
        ok, diff = compare_expected_vs_actual(expected_output, extracted_output, answer)
        status = "通过" if ok else "不通过"
    except Exception as exc:
        status = "执行异常"
        diff = f"{type(exc).__name__}: {exc}"

    report_row = {
        "序号": idx + 1,
        "query": query,
        "期望输出": expected_output,
        "实际提取输出": extracted_output,
        "执行结果": status,
        "差异说明": diff,
        "answer原文": answer,
    }
    raw_result = {
        "序号": idx + 1,
        "query": query,
        "expected_output": expected_output,
        "raw_response": raw_response,
        "answer": answer,
        "extracted_output": extracted_output,
        "status": status,
        "diff": diff,
    }
    print(f"[{idx + 1}/{total}] {query} -> {status}", flush=True)
    return report_row, raw_result


def write_reports(
    output_dir: Path,
    report_rows: List[Dict[str, Any]],
    raw_results: List[Dict[str, Any]],
    total: int,
    passed: int,
    failed: int,
    errors: int,
) -> Dict[str, Path]:
    report_df = pd.DataFrame(report_rows)

    excel_path = resolve_writable_path(output_dir / "回归测试报告.xlsx")
    report_df.to_excel(excel_path, index=False)

    json_path = resolve_writable_path(output_dir / "回归测试原始结果.json")
    json_path.write_text(json.dumps(raw_results, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_lines = [
        "# 昇腾适配模型查询助手回归测试总结",
        "",
        f"- 总用例数：{total}",
        f"- 通过：{passed}",
        f"- 不通过：{failed}",
        f"- 执行异常：{errors}",
        "",
        "## 不通过/异常用例",
        "",
    ]

    bad_rows = [row for row in report_rows if row.get("执行结果") != "通过"]
    if not bad_rows:
        summary_lines.append("全部通过。")
    else:
        for row in bad_rows:
            summary_lines.extend(
                [
                    f"### {row['序号']}. {row['query']}",
                    f"- 期望输出：{row['期望输出']}",
                    f"- 实际提取输出：{row['实际提取输出']}",
                    f"- 执行结果：{row['执行结果']}",
                    f"- 差异说明：{row['差异说明']}",
                    "",
                ]
            )

    summary_path = resolve_writable_path(output_dir / "回归测试总结.md")
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")

    detail_path = resolve_writable_path(output_dir / "回归测试实际回复明细.md")
    detail_path.write_text(build_detail_markdown(raw_results), encoding="utf-8")

    return {
        "excel": excel_path,
        "json": json_path,
        "summary": summary_path,
        "detail": detail_path,
    }


def run_regression() -> None:
    testcase_path = resolve_testcase_path()
    output_dir = resolve_output_dir(OUTPUT_DIR)

    if not testcase_path.exists():
        raise FileNotFoundError(f"未找到测试用例文件: {testcase_path}")

    df = read_testcase_dataframe(testcase_path)

    if df.empty or len(df.columns) == 0:
        paths = write_reports(
            output_dir=output_dir,
            report_rows=[],
            raw_results=[],
            total=0,
            passed=0,
            failed=0,
            errors=0,
        )
        print("测试文件为空，未执行任何用例。")
        print("\n=== 回归测试完成 ===")
        print(f"Excel 报告：{paths['excel']}")
        print(f"JSON 明细：{paths['json']}")
        print(f"Markdown 总结：{paths['summary']}")
        print(f"Markdown 实际回复明细：{paths['detail']}")
        return

    query_col = find_column(df, QUERY_COLUMN_CANDIDATES)
    expected_col = find_column(df, EXPECTED_COLUMN_CANDIDATES)

    total = len(df)
    report_rows: List[Optional[Dict[str, Any]]] = [None] * total
    raw_results: List[Optional[Dict[str, Any]]] = [None] * total
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, total or 1)) as executor:
        future_map = {
            executor.submit(process_row, idx, total, row, query_col, expected_col): idx
            for idx, row in df.iterrows()
        }
        for future in as_completed(future_map):
            idx = future_map[future]
            report_row, raw_result = future.result()
            report_rows[idx] = report_row
            raw_results[idx] = raw_result

    final_report_rows = [row for row in report_rows if row is not None]
    final_raw_results = [row for row in raw_results if row is not None]
    passed = sum(1 for row in final_report_rows if row["执行结果"] == "通过")
    failed = sum(1 for row in final_report_rows if row["执行结果"] == "不通过")
    errors = sum(1 for row in final_report_rows if row["执行结果"] == "执行异常")

    paths = write_reports(
        output_dir=output_dir,
        report_rows=final_report_rows,
        raw_results=final_raw_results,
        total=total,
        passed=passed,
        failed=failed,
        errors=errors,
    )

    print("\n=== 回归测试完成 ===")
    print(f"Excel 报告：{paths['excel']}")
    print(f"JSON 明细：{paths['json']}")
    print(f"Markdown 总结：{paths['summary']}")
    print(f"Markdown 实际回复明细：{paths['detail']}")


if __name__ == "__main__":
    run_regression()
