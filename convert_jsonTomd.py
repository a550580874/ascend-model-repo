import json
import re
from pathlib import Path


def generate_aliases(model_name: str) -> list[str]:
    """
    为模型名生成一些基础别名，便于关键词检索。
    """
    if not model_name:
        return []

    aliases = set()
    aliases.add(model_name)

    # 空格版
    spaced = re.sub(r"[-_]+", " ", model_name)
    aliases.add(spaced)

    # 小写版
    aliases.add(model_name.lower())

    # 空格+小写
    aliases.add(spaced.lower())

    return [a for a in aliases if a.strip()]


def normalize_framework(framework: str) -> str:
    """
    统一适配框架字段展示，避免空值。
    """
    fw = (framework or "").strip()
    return fw if fw else "未知"


def convert_json_to_kb_markdown(
    input_json_path: str,
    output_md_path: str
) -> None:
    """
    将 ascend_model.json 转换成适合知识库导入的 Markdown / 文本块格式。
    每个模型一块，块之间用 --- 分隔。
    """
    input_path = Path(input_json_path)
    output_path = Path(output_md_path)

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    models = data.get("models", [])
    if not isinstance(models, list):
        raise ValueError("JSON 格式异常：未找到 models 列表")

    blocks = []

    for item in models:
        if not isinstance(item, dict):
            continue

        name = str(item.get("name") or "").strip()
        full_name = str(item.get("full_name") or "").strip()
        url = str(item.get("url") or "").strip()
        adapter_framework = normalize_framework(item.get("adapter_framework"))

        if not name:
            continue

        aliases = generate_aliases(name)
        alias_text = "，".join(aliases)

        block = [
            f"模型名：{name}",
            f"别名：{alias_text}",
            f"适配框架：{adapter_framework}",
            "昇腾适配状态：已收录",
            f"仓库全路径：{full_name if full_name else '未知'}",
            f"仓库链接：{url if url else '无访问地址'}",
            "来源：ascend-model-repo",
            "说明：该模型已收录在昇腾适配模型仓中，可进一步查看仓库说明与部署方法。",
            "---"
        ]

        blocks.append("\n".join(block))

    output_text = "\n".join(blocks)

    with output_path.open("w", encoding="utf-8") as f:
        f.write(output_text)

    print(f"转换完成，共输出 {len(blocks)} 条模型记录")
    print(f"输出文件：{output_path}")


if __name__ == "__main__":
    convert_json_to_kb_markdown(
        input_json_path="./data/ascend_model_with_adapter.json",
        output_md_path="./data/ascend_model_kb.md"
    )
