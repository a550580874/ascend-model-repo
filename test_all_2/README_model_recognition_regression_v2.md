# 模型识别 Agent 回归测试说明 v2

本目录用于维护“模型识别 Agent”的全量回归测试集合。测试目标是验证 `from_query_get_result(query)` 是否能从用户输入中准确识别：

- 模型名 `model-name`
- 属性标签 `attribute-tag`
- 适配框架 `framwork`
- 适配硬件 `hardware`
- 单模型 / 多模型查询
- 中文 / 英文查询

## 1. 本版核心口径变更

本版最重要的变更是：

> **模型系列版本属于 `model-name`，不再拆到 `attribute-tag`。**

也就是说，类似 `qwen3-30B` 这种输入中：

- `qwen3` 是模型名的一部分
- `30B` 才是属性标签

### 示例

| 输入 | 旧口径 | 新口径 |
|---|---|---|
| `qwen3-30B` | `model-name: qwen attribute-tag: 3, 30b` | `model-name: qwen3 attribute-tag: 30b` |
| `qwen2.5-72b-instruct` | `model-name: qwen attribute-tag: 2.5, 72b, instruct` | `model-name: qwen2.5 attribute-tag: 72b, instruct` |
| `glm-4.7` | `model-name: glm attribute-tag: 4.7` | `model-name: glm4.7` |
| `deepseek-r1-distill-qwen-32b` | `model-name: deepseek attribute-tag: r1, distill, qwen, 32b` | `model-name: deepseek-r1 attribute-tag: distill, qwen, 32b` |
| `minimax-m2.7-80b` | `model-name: minimax attribute-tag: m2.7, 80b` | `model-name: minimax-m2.7 attribute-tag: 80b` |

## 2. 文件说明

| 文件 | 说明 |
|---|---|
| `模型识别Agent_全量回归测试用例_v2.xlsx` | 新口径测试用例表，包含「输入」「预期输出」两列。 |
| `run_model_recognition_regression_v2.py` | 新口径回归测试脚本。 |
| `模型识别Agent_回归测试结果_v2.xlsx` | 脚本运行后默认生成的测试结果文件。 |

## 3. 测试用例格式

测试脚本默认读取 Excel 的第一个 Sheet。表头必须包含以下两列：

| 列名 | 含义 |
|---|---|
| `输入` | 用户可能输入的原始 query。 |
| `预期输出` | 模型识别 Agent 应返回的标准化识别结果。 |

示例：

| 输入 | 预期输出 |
|---|---|
| `qwen3-30B` | `[query 1] model-name: qwen3 attribute-tag: 30b` |
| `glm-5 vllm a3 and glm4.7 vllm 910B` | `[query 1] model-name: glm5 framwork: vllm hardware: a3; [query 2] model-name: glm4.7 framwork: vllm hardware: 910b` |
| `查询 qwen3-30B 和 deepseek-r1 在 A3 上的适配` | `[查询1] model-name: qwen3 attribute-tag: 30b hardware: a3; [查询2] model-name: deepseek-r1 hardware: a3` |

> 注意：脚本默认会将「预期输出」和「实际输出」都转为小写后比较，所以大小写差异不会导致失败。

## 4. 字段定义

### 4.1 model-name

`model-name` 表示模型系列名或模型系列版本名。

应该进入 `model-name` 的内容：

| 类型 | 示例 |
|---|---|
| 基础模型系列 | `qwen`、`glm`、`deepseek`、`kimi` |
| 模型主版本 | `qwen3`、`qwen2.5`、`glm5`、`glm4.7` |
| 官方版本代号 | `deepseek-r1`、`deepseek-v3`、`kimi-k2` |
| 特殊系列名 | `minimax-m2.7`、`llama3.1`、`gemma3`、`phi3` |
| 多模态系列名 | `minicpm-v`、`hunyuan3d` |

### 4.2 attribute-tag

`attribute-tag` 表示模型名后面的附加属性。

应该进入 `attribute-tag` 的内容：

| 类型 | 示例 |
|---|---|
| 参数规模 | `7b`、`8b`、`30b`、`32b`、`70b`、`72b`、`671b` |
| MoE 激活/总参数规格 | `a3b`、`a22b`、`a35b`、`8x7b` |
| 量化 | `w8a8`、`w8a8s`、`w4a8`、`int4` |
| 精度 | `bf16`、`fp16` |
| 任务类型 | `instruct`、`chat`、`coder`、`code` |
| 模态类型 | `vl`、`vision`、`audio` |
| 派生/蒸馏 | `distill` |
| 上下文长度 | `4k`、`16k`、`128k` |
| 变体名 | `air`、`mini`、`plus`、`turbo` |

### 4.3 framwork

`framwork` 表示用户输入中提到的适配框架。

当前测试集中包含：

- `vllm`
- `vllm-ascend`
- `sglang`
- `sglang-ascend`
- `mindie`
- `xllm`

> 说明：这里沿用你原始样例里的拼写 `framwork`。如果你的 Agent 输出的是标准拼写 `framework`，可以使用脚本的 `--loose` 模式兼容。

### 4.4 hardware

`hardware` 表示用户输入中提到的昇腾硬件。

当前测试集中包含：

- `a2`
- `a3`
- `910b`
- `910b1`
- `910c`

## 5. 被测函数要求

你需要提供一个 Python 函数：

```python
def from_query_get_result(query: str) -> str:
    ...
```

函数要求：

1. 输入参数是用户原始 query。
2. 返回值是字符串。
3. 返回格式应与测试用例中的「预期输出」一致。
4. 如果输入中包含多个模型，应按模型在输入中出现的顺序输出多个 query 片段。
5. 对于中文输入，推荐使用 `[查询1]`、`[查询2]`。
6. 对于英文输入，推荐使用 `[query 1]`、`[query 2]`。

## 6. 快速开始

### 6.1 安装依赖

```bash
pip install openpyxl
```

### 6.2 准备被测模块

假设你的识别函数在当前目录的 `agent.py` 中：

```python
# agent.py

def from_query_get_result(query: str) -> str:
    # 替换成你的真实模型识别逻辑
    return ""
```

目录结构示例：

```text
test_all/
├── agent.py
├── run_model_recognition_regression_v2.py
└── 模型识别Agent_全量回归测试用例_v2.xlsx
```

### 6.3 执行回归测试

```bash
python run_model_recognition_regression_v2.py \
  --cases 模型识别Agent_全量回归测试用例_v2.xlsx \
  --module agent \
  --function from_query_get_result \
  --output 模型识别Agent_回归测试结果_v2.xlsx
```

如果函数名就是 `from_query_get_result`，可以省略 `--function`：

```bash
python run_model_recognition_regression_v2.py \
  --cases 模型识别Agent_全量回归测试用例_v2.xlsx \
  --module agent
```

## 7. 脚本参数说明

| 参数 | 是否必填 | 默认值 | 说明 |
|---|---:|---|---|
| `--cases` | 否 | `模型识别Agent_全量回归测试用例_v2.xlsx` | 测试用例 Excel 路径。 |
| `--output` | 否 | `模型识别Agent_回归测试结果_v2.xlsx` | 输出结果 Excel 路径。 |
| `--module` | 是 | 无 | 包含 `from_query_get_result` 的 Python 模块名。 |
| `--function` | 否 | `from_query_get_result` | 被测函数名。 |
| `--sheet` | 否 | 第一个 Sheet | 指定测试用例 Sheet 名。 |
| `--loose` | 否 | 关闭 | 启用宽松比较。 |
| `--fail-on-error` | 否 | 关闭 | 存在失败用例时返回非 0 退出码，适合 CI 使用。 |

## 8. 严格比较与宽松比较

### 8.1 默认严格比较

默认模式下，脚本只做：

- 转小写
- 去除首尾空白
- 合并连续空白

也就是说，下面这种内容差异会判定为失败：

```text
预期：model-name: qwen3 attribute-tag: 30b
实际：model-name: qwen attribute-tag: 3, 30b
```

这正是本版需要重点校验的内容。

### 8.2 宽松比较

如果只是格式差异，可以使用 `--loose`：

```bash
python run_model_recognition_regression_v2.py \
  --cases 模型识别Agent_全量回归测试用例_v2.xlsx \
  --module agent \
  --loose
```

宽松模式会兼容：

| 差异类型 | 示例 |
|---|---|
| `framework:` / `framwork:` 拼写差异 | `framework: vllm` 与 `framwork: vllm` |
| 中文字段名差异 | `模型名:`、`属性标签:`、`硬件:` |
| 中英文查询编号差异 | `[查询1]` 与 `[query 1]` |
| 中英文标点差异 | `；` 与 `;`，`：` 与 `:` |
| 多余空白差异 | 连续空格、分号前后空格 |

> 重要：宽松模式不会把 `qwen3` 和 `qwen + attribute-tag: 3` 视为等价。因此仍能验证本次新口径。

## 9. 输出结果说明

脚本会生成一个新的 Excel 文件，默认名为：

```text
模型识别Agent_回归测试结果_v2.xlsx
```

结果文件包含三个 Sheet。

### 9.1 回归测试结果

| 列名 | 说明 |
|---|---|
| `序号` | 测试用例序号。 |
| `输入` | 测试用例输入。 |
| `预期输出` | 标准答案。 |
| `实际输出` | `from_query_get_result(query)` 的真实返回值。 |
| `是否符合预期` | `是` 或 `否`。 |
| `错误信息` | 函数执行异常时记录 traceback。 |

### 9.2 汇总

| 指标 | 说明 |
|---|---|
| `总用例数` | 实际执行的测试用例数量。 |
| `通过数` | 通过的用例数量。 |
| `失败数` | 未通过的用例数量。 |
| `通过率` | 通过数 / 总用例数。 |
| `比较模式` | 严格比较或宽松比较。 |
| `核心口径` | 本版测试口径说明。 |

### 9.3 失败用例

只包含未通过的用例，便于快速定位问题。

## 10. 本版测试覆盖范围

当前 v2 测试集主要覆盖以下场景：

1. **模型系列版本并入 model-name**
   - `qwen3`
   - `qwen2.5`
   - `glm5`
   - `glm4.7`
   - `deepseek-r1`
   - `deepseek-v3`
   - `minimax-m2.7`
   - `llama3.1`
   - `gemma3`
   - `phi3`

2. **属性标签识别**
   - 参数规模：`8b`、`30b`、`32b`、`70b`、`72b`
   - 量化：`w8a8`、`w8a8s`、`w4a8`
   - 任务：`instruct`、`chat`、`coder`
   - 模态：`vl`、`audio`
   - 精度：`bf16`
   - 蒸馏：`distill`

3. **中文 / 英文输入**
   - 英文输入输出 `[query 1] ...`
   - 中文输入输出 `[查询1] ...`

4. **单模型 / 多模型输入**
   - 单模型：`qwen3-30B`
   - 多模型：`qwen3-30B and deepseek-r1`
   - 多模型共享硬件：`qwen3、glm5、deepseek-r1 都在 a3 上`
   - 多模型独立框架硬件：`qwen3 vllm a3 and qwen2.5 mindie a2`

5. **别名和模糊输入**
   - `千问` -> `qwen`
   - `智谱` -> `glm`
   - `深度求索` / `DS` -> `deepseek`
   - `moonshot` / `月之暗面` -> `kimi`
   - `MiniMax M2.7` / `MM M2.7` -> `minimax-m2.7`

## 11. 常见失败类型

### 11.1 仍然把主版本放进 attribute-tag

错误示例：

```text
输入：qwen3-30B
实际：model-name: qwen attribute-tag: 3, 30b
预期：model-name: qwen3 attribute-tag: 30b
```

修复方向：

- 模型系列解析阶段要先识别 `qwen3`、`qwen2.5`、`glm5`、`glm4.7` 这类主版本。
- 不要在 attribute-tag 提取阶段再次把主版本号提出来。

### 11.2 DeepSeek R1 / V3 被拆错

错误示例：

```text
输入：deepseek-r1-distill-qwen-32b
实际：model-name: deepseek attribute-tag: r1, distill, qwen, 32b
预期：model-name: deepseek-r1 attribute-tag: distill, qwen, 32b
```

修复方向：

- `r1`、`v3` 这类 DeepSeek 官方代号应并入 `model-name`。
- `distill`、`qwen`、`32b` 才是 attribute-tag。

### 11.3 MiniMax M2.7 被拆错

错误示例：

```text
输入：minimax-m2.7-80b
实际：model-name: minimax attribute-tag: m2.7, 80b
预期：model-name: minimax-m2.7 attribute-tag: 80b
```

修复方向：

- `m2.7` 应视为 MiniMax 的模型版本代号。
- 建议在正则中对 `minimax[-\s]?m\d+(\.\d+)?` 做专门归一化。

### 11.4 多模型共用框架/硬件没有传播

错误示例：

```text
输入：qwen3、glm5、deepseek-r1 都在 a3 上的 vllm 适配
预期：三个模型都带 framwork: vllm hardware: a3
```

修复方向：

- 对“都在 / all on / both on”这类表达，需要支持共享约束传播。
- 如果每个模型片段有独立约束，则优先使用局部约束。

## 12. 建议的回归流程

1. 修改模型识别逻辑。
2. 执行 v2 回归测试。
3. 查看 `模型识别Agent_回归测试结果_v2.xlsx`。
4. 优先排查失败用例：
   - 主版本是否进入了 `model-name`
   - 参数规模是否进入了 `attribute-tag`
   - DeepSeek R1/V3 是否保留在 `model-name`
   - MiniMax M2.7 是否保留在 `model-name`
   - 多模型拆分顺序是否正确
   - 多模型共享 framework/hardware 是否正确传播
5. 修复后再次执行。
6. 将新发现的问题补充到测试用例表。

## 13. 推荐提交规范

每次修改识别逻辑时，建议同时提交：

```text
1. 识别逻辑代码变更
2. 新增或更新的测试用例
3. 最新回归测试结果
```

提交信息示例：

```text
test: update regression cases for model-name version semantics
```

或者：

```text
fix: keep qwen3 and minimax-m2.7 as model-name
```
