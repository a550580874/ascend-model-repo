# 模型识别 Agent 回归测试说明

本目录用于维护“模型识别 Agent”的全量回归测试集合。测试目标是验证 `from_query_get_result(query)` 对用户输入中的模型名称、版本/属性标签、适配框架、适配硬件等信息是否能够稳定、准确地识别。

## 文件说明

| 文件 | 说明 |
|---|---|
| `模型识别Agent_全量回归测试用例.xlsx` | 回归测试用例表，包含「输入」「预期输出」两列。 |
| `run_model_recognition_regression.py` | 回归测试执行脚本，读取测试用例并调用目标识别函数。 |
| `模型识别Agent_回归测试结果.xlsx` | 脚本运行后生成的测试结果文件，默认输出文件名。 |

## 测试用例格式

测试用例 Excel 默认读取第一个 Sheet，表头必须包含以下两列：

| 列名 | 含义 |
|---|---|
| `输入` | 用户可能输入的原始 query。 |
| `预期输出` | 模型识别 Agent 应该返回的标准化识别结果。 |

示例：

| 输入 | 预期输出 |
|---|---|
| `glm-5 vllm a3 and glm4.7 vllm 910B` | `[query 1] model-name: glm attribute-tag: 5 framwork: vllm hardware: a3; [query 2] model-name: glm attribute-tag: 4.7 framwork: vllm hardware: 910b` |
| `查询 qwen3-8b instruct 在 vllm ascend a2 上的适配` | `[查询1] model-name: qwen attribute-tag: 3, 8b, instruct framwork: vllm-ascend hardware: a2` |

> 注意：测试脚本会将「预期输出」和「实际输出」都转换为小写后再比较，因此大小写差异不会导致失败。

## 覆盖范围

当前测试集主要覆盖以下场景：

1. **中英文输入**
   - 英文输入返回英文格式，如 `[query 1] ...`
   - 中文输入返回中文格式，如 `[查询1] ...`

2. **单模型识别**
   - 标准模型名：`qwen`、`glm`、`deepseek`
   - 带版本：`glm-5`、`qwen2.5`、`deepseek-r1`
   - 中文别名：`千问`、`智谱`、`深度求索`

3. **多模型识别**
   - 示例：`deepseek-r1 和 moonshot`
   - 示例：`glm-5 vllm a3 and glm4.7 vllm 910B`

4. **属性标签识别**
   - 版本：`3`、`4.7`、`5`、`r1`、`v3`
   - 参数规模：`7b`、`8b`、`32b`、`70b`
   - 模型类型/变体：`instruct`、`coder`、`vl`、`audio`、`distill`
   - 量化/精度：`w8a8`、`w4a8`、`bf16`

5. **框架识别**
   - `vllm`
   - `vllm-ascend`
   - `sglang`
   - `sglang-ascend`
   - `mindie`
   - `xllm`

6. **硬件识别**
   - `a2`
   - `a3`
   - `910b`
   - `910b1`
   - `910c`

## 被测函数要求

你需要提供一个 Python 函数：

```python
def from_query_get_result(query: str) -> str:
    ...
```

函数要求：

1. 输入参数是用户原始 query。
2. 返回值是字符串。
3. 返回格式应与测试用例中的「预期输出」一致。
4. 如果输入中包含多个模型，应按识别顺序输出多个 query 片段。

推荐输出格式：

```text
[query 1] model-name: glm attribute-tag: 5 framwork: vllm hardware: a3; [query 2] model-name: glm attribute-tag: 4.7 framwork: vllm hardware: 910b
```

中文输入推荐输出格式：

```text
[查询1] model-name: glm attribute-tag: 5 framwork: vllm hardware: a3; [查询2] model-name: qwen attribute-tag: 3, 8b framwork: vllm-ascend hardware: a2
```

## 快速开始

### 1. 安装依赖

```bash
pip install openpyxl
```

### 2. 准备被测模块

假设你的识别函数在当前目录的 `agent.py` 中：

```python
# agent.py

def from_query_get_result(query: str) -> str:
    # 这里替换成你的真实模型识别逻辑
    return ""
```

目录结构示例：

```text
test_all/
├── agent.py
├── run_model_recognition_regression.py
└── 模型识别Agent_全量回归测试用例.xlsx
```

### 3. 执行回归测试

```bash
python run_model_recognition_regression.py \
  --cases 模型识别Agent_全量回归测试用例.xlsx \
  --module agent \
  --function from_query_get_result \
  --output 模型识别Agent_回归测试结果.xlsx
```

如果函数名就是 `from_query_get_result`，可以省略 `--function`：

```bash
python run_model_recognition_regression.py \
  --cases 模型识别Agent_全量回归测试用例.xlsx \
  --module agent
```

## 参数说明

| 参数 | 是否必填 | 默认值 | 说明 |
|---|---:|---|---|
| `--cases` | 否 | `模型识别Agent_全量回归测试用例.xlsx` | 测试用例 Excel 路径。 |
| `--output` | 否 | `模型识别Agent_回归测试结果.xlsx` | 输出结果 Excel 路径。 |
| `--module` | 是 | 无 | 包含 `from_query_get_result` 的 Python 模块名。 |
| `--function` | 否 | `from_query_get_result` | 被测函数名。 |
| `--sheet` | 否 | 第一个 Sheet | 指定测试用例 Sheet 名。 |
| `--loose` | 否 | 关闭 | 启用宽松比较。 |

## 宽松比较模式

如果你的实际输出中使用的是 `framework:`，而测试集中沿用了原始示例里的 `framwork:`，可以使用 `--loose` 参数：

```bash
python run_model_recognition_regression.py \
  --cases 模型识别Agent_全量回归测试用例.xlsx \
  --module agent \
  --loose
```

宽松比较会兼容以下轻微格式差异：

| 差异类型 | 示例 |
|---|---|
| `framework:` / `framwork:` 拼写差异 | `framework: vllm` 与 `framwork: vllm` |
| 中文字段名差异 | `模型名:`、`属性标签:`、`硬件:` |
| 中英文查询编号差异 | `[查询1]` 与 `[query 1]` |
| 中英文标点差异 | `；` 与 `;`，`：` 与 `:` |
| 多余空白差异 | 连续空格、分号前后空格 |

> 建议：正式验收时优先使用严格模式；调试阶段可以使用 `--loose` 快速定位真实识别错误。

## 输出结果说明

脚本会生成一个新的 Excel 文件，默认名为：

```text
模型识别Agent_回归测试结果.xlsx
```

结果文件包含两个 Sheet：

### Sheet 1：回归测试结果

| 列名 | 说明 |
|---|---|
| `输入` | 测试用例输入。 |
| `预期输出` | 标准答案。 |
| `实际输出` | `from_query_get_result(query)` 的真实返回值。 |
| `是否符合预期` | `是` 或 `否`。 |

### Sheet 2：汇总

| 指标 | 说明 |
|---|---|
| `总用例数` | 实际执行的测试用例数量。 |
| `通过数` | 通过的用例数量。 |
| `失败数` | 未通过的用例数量。 |
| `通过率` | 通过数 / 总用例数。 |

脚本运行结束后，也会在命令行打印汇总信息和前 5 条失败样例，便于快速排查。

## 常见问题

### 1. 报错：缺少依赖 openpyxl

执行：

```bash
pip install openpyxl
```

### 2. 报错：导入模块失败

确认 `--module` 填的是模块名，不是文件名。

正确：

```bash
python run_model_recognition_regression.py --module agent
```

错误：

```bash
python run_model_recognition_regression.py --module agent.py
```

如果你的模块不在当前目录，需要先设置 `PYTHONPATH`：

```bash
export PYTHONPATH=/path/to/your/project:$PYTHONPATH
python run_model_recognition_regression.py --module agent
```

### 3. 报错：找不到 from_query_get_result

确认模块里存在同名函数：

```python
def from_query_get_result(query: str) -> str:
    ...
```

如果你的函数名不同，可以使用 `--function` 指定：

```bash
python run_model_recognition_regression.py \
  --module agent \
  --function your_function_name
```

### 4. 大量用例因为空格或标点失败

先使用宽松模式确认是否只是格式问题：

```bash
python run_model_recognition_regression.py --module agent --loose
```

如果宽松模式通过、严格模式失败，说明识别内容基本正确，但输出格式需要进一步统一。

### 5. 多模型顺序不一致导致失败

测试集默认要求多模型输出顺序与输入中出现顺序一致。例如：

```text
输入：deepseek-r1 and moonshot
预期：[query 1] deepseek ...; [query 2] moonshot ...
```

如果实际输出顺序反了，会被判定为失败。建议在 Agent 内保持按输入文本出现顺序输出。

## 建议的回归流程

1. 新增或修改模型识别规则。
2. 执行完整回归测试。
3. 查看 `模型识别Agent_回归测试结果.xlsx`。
4. 优先排查失败样例中的：
   - 模型名未识别
   - attribute-tag 丢失
   - framework/hardware 识别错误
   - 多模型拆分错误
   - 中文/英文输出格式错误
5. 修复后再次执行回归测试。
6. 将新增问题沉淀为新的测试用例。

## 维护测试集的原则

新增测试用例时，建议覆盖以下维度：

1. **模型名标准写法**
   - `qwen`
   - `glm`
   - `deepseek`

2. **模型名变体**
   - 连字符：`qwen-3`
   - 空格：`qwen 3`
   - 紧凑写法：`qwen3`
   - 大小写：`QWEN3`

3. **中文别名**
   - `千问`
   - `智谱`
   - `深度求索`
   - `月之暗面`

4. **属性标签**
   - 版本号
   - 参数规模
   - 量化方式
   - 任务类型
   - 模态类型

5. **适配信息**
   - framework
   - hardware
   - framework + hardware 同时出现

6. **多模型组合**
   - 英文 and / or
   - 中文 和 / 以及 / 对比
   - 多个模型共享同一个 framework 或 hardware
   - 每个模型有独立的 framework 或 hardware

7. **负向或模糊样例**
   - 拼写错误
   - 公司名指代
   - 产品名和公司名混用
   - 容易混淆的模型系列

## 推荐提交规范

每次修改识别逻辑时，建议同时提交：

```text
1. 识别逻辑代码变更
2. 新增或更新的测试用例
3. 最新回归测试结果
```

提交信息示例：

```text
test: add regression cases for qwen3 coder and glm5 hardware parsing
```

或者：

```text
fix: normalize minimax m2.7 version parsing
```
