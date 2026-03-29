import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from ascend_query_executor import execute_query
from run_dify_workflow_direct import run_dify


TESTCASE_XLSX = Path(r"C:\Users\Administrator\Desktop\测试用例.xlsx")
OUTPUT_DIR = Path(r"C:\Users\Administrator\Desktop\dify_regression_report")

COL_SCENE = "用例场景类型"
COL_QUERY = "用户输入"
COL_EXPECTED = "预期筛选关键词"


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_key(value: Any) -> str:
    text = normalize_text(value).lower()
    return re.sub(r"[\s_\-]", "", text)


def normalize_framework(value: Any) -> str:
    raw = normalize_text(value)
    if not raw:
        return ""
    mapping = {
        "vllm": "vLLM-Ascend",
        "vllmascend": "vLLM-Ascend",
        "sglang": "SGLangAscend",
        "sglangascend": "SGLangAscend",
        "mindie": "MindIE",
        "ascendsact": "Ascend-SACT",
        "sact": "Ascend-SACT",
        "xllm": "xLLM",
    }
    return mapping.get(normalize_key(raw), raw)


def normalize_hardware(value: Any) -> str:
    raw = normalize_text(value).upper().replace(" ", "")
    if not raw:
        return ""
    if raw in {"A2", "A3", "A4"}:
        return raw
    if raw.startswith("910B"):
        return "A2"
    if raw.startswith("910C"):
        return "A3"
    return raw


def normalize_tag(value: Any) -> str:
    return normalize_key(value)


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


def split_top_level_commas(text: str) -> List[str]:
    parts: List[str] = []
    current: List[str] = []
    depth = 0
    for ch in text:
        if ch == "[":
            depth += 1
            current.append(ch)
            continue
        if ch == "]":
            depth = max(depth - 1, 0)
            current.append(ch)
            continue
        if ch == "," and depth == 0:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            continue
        current.append(ch)

    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def looks_like_structured_output(obj: Any) -> bool:
    return (
        isinstance(obj, dict)
        and "is_ascend_query" in obj
        and "query_type" in obj
        and "entities" in obj
        and isinstance(obj.get("entities"), list)
    )


def try_parse_json(text: str) -> Optional[Any]:
    text = normalize_text(text)
    if not text:
        return None

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        candidate = match.group(0)
        try:
            return json.loads(candidate)
        except Exception:
            pass

    return None


def extract_structured_output(response: Any) -> Dict[str, Any]:
    if looks_like_structured_output(response):
        return response

    if isinstance(response, dict):
        direct = response.get("structured_output")
        if looks_like_structured_output(direct):
            return direct

        outputs = response.get("outputs")
        if isinstance(outputs, dict):
            if looks_like_structured_output(outputs):
                return outputs
            nested = outputs.get("structured_output")
            if looks_like_structured_output(nested):
                return nested

        for key in ["answer", "result", "text"]:
            value = response.get(key)
            if isinstance(value, str):
                parsed = try_parse_json(value)
                if looks_like_structured_output(parsed):
                    return parsed

    return {
        "is_ascend_query": False,
        "query_type": "unknown",
        "retrieval_query": "",
        "retrieval_query_normalized": "",
        "entities": [],
    }


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


def is_framework_token(token: str) -> bool:
    return normalize_framework(token) in {"vLLM-Ascend", "SGLangAscend", "MindIE", "Ascend-SACT", "xLLM"}


def is_hardware_token(token: str) -> bool:
    return normalize_hardware(token) in {"A2", "A3", "A4"}


def is_tag_token(token: str) -> bool:
    nt = normalize_tag(token)
    return bool(
        re.fullmatch(r"w\d+a\d+", nt)
        or re.fullmatch(r"a\d+b", nt)
        or nt in {"mtp", "coder", "vl", "embedding", "instruct"}
    )


def parse_expected_keywords(text: str) -> Dict[str, Any]:
    text = normalize_text(text)

    if not text:
        return {
            "is_ascend_query": True,
            "query_type": "unknown",
            "entities": [],
        }

    if "is_ascend_query=false" in text.lower():
        return {
            "is_ascend_query": False,
            "query_type": "unknown",
            "entities": [],
        }

    bracket_entities = re.findall(r"\[([^\[\]]+)\]", text)
    if bracket_entities and not re.search(r"\bprefix\s*=", text, re.I):
        entities: List[Dict[str, Any]] = []
        for raw in bracket_entities:
            parts = [x.strip() for x in raw.split("+") if x.strip()]
            entity = {
                "raw_text": "",
                "normalized_prefix": "",
                "adapter_framework": "",
                "adapter_hardware": "",
                "attribute_tags": [],
            }
            tags: List[str] = []

            for part in parts:
                if is_framework_token(part):
                    entity["adapter_framework"] = normalize_framework(part)
                elif is_hardware_token(part):
                    entity["adapter_hardware"] = normalize_hardware(part)
                elif is_tag_token(part):
                    tags.append(normalize_tag(part))
                else:
                    entity["normalized_prefix"] = normalize_text(part)

            entity["attribute_tags"] = sorted(set(tags))
            entities.append(entity)

        return {
            "is_ascend_query": True,
            "query_type": "mixed_search" if len(entities) > 1 else "series_search",
            "entities": entities,
        }

    parts = split_top_level_commas(text)
    kv: Dict[str, str] = {}
    for part in parts:
        m = re.match(r"\s*([a-zA-Z_]+)\s*=\s*(.+?)\s*$", part)
        if m:
            kv[m.group(1).lower()] = m.group(2)

    tags: List[str] = []
    tags_raw = kv.get("tags", "")
    if tags_raw.startswith("[") and tags_raw.endswith("]"):
        tags_content = tags_raw[1:-1].strip()
        if tags_content:
            tags = [normalize_tag(x.strip()) for x in tags_content.split(",") if x.strip()]

    entity = {
        "raw_text": "",
        "normalized_prefix": normalize_text(kv.get("prefix", "")),
        "adapter_framework": normalize_framework(kv.get("framework", "")),
        "adapter_hardware": normalize_hardware(kv.get("hardware", "")),
        "attribute_tags": sorted(set([x for x in tags if x])),
    }

    return {
        "is_ascend_query": True,
        "query_type": normalize_text(kv.get("query_type", "series_search")) or "series_search",
        "entities": [entity] if any(entity.values()) else [],
    }


def compare_entities(expected: Dict[str, Any], actual: Dict[str, Any]) -> Tuple[bool, str]:
    exp_is_ascend = bool(expected.get("is_ascend_query", True))
    act_is_ascend = bool(actual.get("is_ascend_query", False))
    if exp_is_ascend != act_is_ascend:
        return False, f"is_ascend_query 不一致：expected={exp_is_ascend}, actual={act_is_ascend}"

    exp_query_type = normalize_text(expected.get("query_type", ""))
    act_query_type = normalize_text(actual.get("query_type", ""))
    if exp_query_type and exp_query_type != act_query_type:
        return False, f"query_type 不一致：expected={exp_query_type}, actual={act_query_type}"

    if not exp_is_ascend:
        return True, "符合预期（非昇腾查询）"

    exp_entities = expected.get("entities", []) or []
    act_entities = actual.get("entities", []) or []

    if len(exp_entities) != len(act_entities):
        return False, f"实体数量不一致：expected={len(exp_entities)}, actual={len(act_entities)}"

    diffs: List[str] = []

    for idx, (exp, act) in enumerate(zip(exp_entities, act_entities), start=1):
        exp_prefix = normalize_key(exp.get("normalized_prefix"))
        act_prefix = normalize_key(act.get("normalized_prefix"))
        if exp_prefix != act_prefix:
            diffs.append(
                f"实体{idx} prefix 不一致：expected={exp.get('normalized_prefix')}, actual={act.get('normalized_prefix')}"
            )

        exp_fw = normalize_framework(exp.get("adapter_framework"))
        act_fw = normalize_framework(act.get("adapter_framework"))
        if exp_fw != act_fw:
            diffs.append(
                f"实体{idx} framework 不一致：expected={exp.get('adapter_framework')}, actual={act.get('adapter_framework')}"
            )

        exp_hw = normalize_hardware(exp.get("adapter_hardware"))
        act_hw = normalize_hardware(act.get("adapter_hardware"))
        if exp_hw != act_hw:
            diffs.append(
                f"实体{idx} hardware 不一致：expected={exp.get('adapter_hardware')}, actual={act.get('adapter_hardware')}"
            )

        exp_tags = sorted({normalize_tag(x) for x in exp.get("attribute_tags", []) if normalize_tag(x)})
        act_tags = sorted({normalize_tag(x) for x in act.get("attribute_tags", []) if normalize_tag(x)})
        if exp_tags != act_tags:
            diffs.append(f"实体{idx} tags 不一致：expected={exp_tags}, actual={act_tags}")

    if diffs:
        return False, "；".join(diffs)
    return True, "符合预期"


def classify_failure(expected: Dict[str, Any], actual_structured: Dict[str, Any], local_response: Optional[Dict[str, Any]], diff: str) -> str:
    if local_response is None:
        return "structured_output 提取错"

    if "failed to fetch data source" in diff or "no model list found" in diff:
        return "数据源字段兼容问题"

    if "result" not in local_response or not normalize_text(local_response.get("result")):
        return "输出渲染问题"

    if not looks_like_structured_output(actual_structured):
        return "structured_output 提取错"

    if "is_ascend_query 不一致" in diff or "query_type 不一致" in diff:
        return "Dify LLM prompt / structured_output 边界问题"

    if "实体" in diff or "prefix" in diff or "framework" in diff or "hardware" in diff or "tags" in diff:
        return "expected 解析错" if not expected.get("entities") else "本地代码执行过滤逻辑错"

    return "本地代码执行过滤逻辑错"


def find_column(df: pd.DataFrame, preferred: str, candidates: List[str]) -> str:
    if preferred in df.columns:
        return preferred
    for candidate in candidates:
        if candidate in df.columns:
            return candidate

    normalized_map = {normalize_key(col): col for col in df.columns}
    for candidate in [preferred] + candidates:
        key = normalize_key(candidate)
        if key in normalized_map:
            return normalized_map[key]

    raise KeyError(f"未找到列: {preferred}")


def build_detail_markdown(raw_results: List[Dict[str, Any]]) -> str:
    lines = ["# 回归测试实际回复明细", ""]

    for item in raw_results:
        lines.extend(
            [
                f"## 问题 {item['序号']}",
                "",
                "### 场景",
                item.get("scene", ""),
                "",
                "### 用户输入",
                item.get("query", ""),
                "",
                "### 预期筛选关键词",
                item.get("expected_text", ""),
                "",
                "### 执行结果",
                item.get("status", ""),
                "",
                "### 差异说明",
                item.get("diff", "") or "无",
                "",
                "### 实际 structured_output",
                markdown_code_block(item.get("actual_structured_output", {}), "json"),
                "",
            ]
        )

        actual_response = item.get("actual_response")
        display_result = ""
        if isinstance(actual_response, dict):
            display_result = normalize_text(actual_response.get("result"))

        if display_result:
            lines.extend(["### 实际 result", display_result, ""])
        else:
            lines.extend(["### 实际 result", markdown_code_block(actual_response, "json"), ""])

        lines.extend(["---", ""])

    return "\n".join(lines)






def resolve_output_dir(preferred: Path) -> Path:
    candidates = [preferred, Path.cwd() / "dify_regression_report"]
    last_error = None
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return candidate
        except Exception as exc:
            last_error = exc
            continue
    raise PermissionError(f"所有输出目录都不可写: {last_error}")

def resolve_writable_path(path: Path) -> Path:
    """Return target path, fallback to timestamp suffix when file is locked."""
    if not path.exists():
        return path

    try:
        with open(path, "a", encoding="utf-8"):
            return path
    except PermissionError:
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        return path.with_name(f"{path.stem}_{timestamp}{path.suffix}")


def run_regression() -> None:
    output_dir = resolve_output_dir(OUTPUT_DIR)

    if not TESTCASE_XLSX.exists():
        raise FileNotFoundError(f"未找到测试用例文件: {TESTCASE_XLSX}")

    df = pd.read_excel(TESTCASE_XLSX)

    col_scene = find_column(df, COL_SCENE, ["场景", "测试场景", "用例场景"])
    col_query = find_column(df, COL_QUERY, ["问题", "query", "用户问题"])
    col_expected = find_column(df, COL_EXPECTED, ["预期", "筛选关键词", "expected"])

    rows: List[Dict[str, Any]] = []
    raw_results: List[Dict[str, Any]] = []

    total = len(df)
    passed = 0
    failed = 0
    errors = 0

    for idx, row in df.iterrows():
        scene = normalize_text(row.get(col_scene))
        query = normalize_text(row.get(col_query))
        expected_text = normalize_text(row.get(col_expected))
        expected_struct = parse_expected_keywords(expected_text)

        dify_response: Optional[Dict[str, Any]] = None
        llm_structured: Dict[str, Any] = {}
        actual_response: Optional[Dict[str, Any]] = None
        actual_structured: Dict[str, Any] = {}
        status = ""
        diff = ""
        fail_category = ""

        try:
            dify_response = call_dify_with_retry(query)
            llm_structured = extract_structured_output(dify_response)

            actual_response = execute_query(llm_structured)
            actual_structured = actual_response.get("structured_output", {})

            ok, diff = compare_entities(expected_struct, actual_structured)
            status = "通过" if ok else "不通过"

            if ok:
                passed += 1
            else:
                failed += 1
                fail_category = classify_failure(expected_struct, actual_structured, actual_response, diff)

        except Exception as exc:
            status = "执行异常"
            diff = f"{type(exc).__name__}: {exc}"
            errors += 1
            fail_category = classify_failure(expected_struct, actual_structured, actual_response, diff)

        rows.append(
            {
                "序号": idx + 1,
                "用例场景类型": scene,
                "用户输入": query,
                "预期筛选关键词": expected_text,
                "执行结果": status,
                "差异说明": diff,
                "失败分类": fail_category,
                "实际structured_output": safe_json_dumps(actual_structured),
                "LLM_structured_output": safe_json_dumps(llm_structured),
            }
        )

        raw_results.append(
            {
                "序号": idx + 1,
                "scene": scene,
                "query": query,
                "expected_text": expected_text,
                "expected_struct": expected_struct,
                "dify_response": dify_response,
                "llm_structured_output": llm_structured,
                "actual_response": actual_response,
                "actual_structured_output": actual_structured,
                "status": status,
                "diff": diff,
                "fail_category": fail_category,
            }
        )

        print(f"[{idx + 1}/{total}] {query} -> {status}")

    report_df = pd.DataFrame(rows)

    excel_path = resolve_writable_path(output_dir / "回归测试报告.xlsx")
    report_df.to_excel(excel_path, index=False)

    json_path = resolve_writable_path(output_dir / "回归测试原始结果.json")
    json_path.write_text(json.dumps(raw_results, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_path = resolve_writable_path(output_dir / "回归测试总结.md")
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

    bad_df = report_df[report_df["执行结果"] != "通过"]
    if bad_df.empty:
        summary_lines.append("全部通过。")
    else:
        for _, r in bad_df.iterrows():
            summary_lines.extend(
                [
                    f"### {r['序号']}. {r['用户输入']}",
                    f"- 场景：{r['用例场景类型']}",
                    f"- 预期：{r['预期筛选关键词']}",
                    f"- 结果：{r['执行结果']}",
                    f"- 失败分类：{r['失败分类']}",
                    f"- 差异：{r['差异说明']}",
                    "",
                ]
            )

    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")

    detail_path = resolve_writable_path(output_dir / "回归测试实际回复明细.md")
    detail_path.write_text(build_detail_markdown(raw_results), encoding="utf-8")

    print("\n=== 回归测试完成 ===")
    print(f"Excel 报告：{excel_path}")
    print(f"JSON 明细：{json_path}")
    print(f"Markdown 总结：{summary_path}")
    print(f"Markdown 实际回复明细：{detail_path}")


if __name__ == "__main__":
    run_regression()
