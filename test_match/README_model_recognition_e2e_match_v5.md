# 模型识别 Agent 双层端到端回归测试说明 v5

本目录用于测试模型识别 Agent 的 **两层正确性**：

1. **LLM / match 识别是否正确**  
   从 Dify 最终回答中提取每个查询的识别头部：

   ```text
   model-name / attribute-tag / framwork / hardware
   ```

2. **最终检索输出是否正确**  
   校验 Dify 工作流最终返回的命中数量、展示数量、官方/三方排序、模型名、适配框架、适配硬件、仓库链接等内容。

这样可以区分两类问题：

| 问题类型 | 典型表现 |
|---|---|
| LLM 识别错误 | `qwen3-30B` 被拆成 `model-name: qwen attribute-tag: 3, 30b` |
| 后续代码检索/排序错误 | LLM 识别正确，但最终命中模型不对，或者官方结果没有优先展示 |

---

## 文件说明

| 文件 | 说明 |
|---|---|
| `模型识别Agent_端到端双层回归测试用例_v5.xlsx` | 双层回归测试用例。 |
| `run_dify_e2e_match_regression_v5.py` | 调用 Dify 并生成回归结果的测试脚本。 |
| `模型识别Agent_端到端双层回归测试结果_v5.xlsx` | 脚本运行后生成的结果文件。 |

---

## 测试用例 Excel 格式

测试用例文件包含三个核心列：

| 列名 | 说明 |
|---|---|
| `输入` | 用户原始 query。 |
| `预期match情况` | 预期的 LLM / match 识别头部。 |
| `预期输出` | 预期的最终检索输出片段。 |

示例：

| 输入 | 预期match情况 | 预期输出 |
|---|---|---|
| `qwen2.5 0.5b mindspeed a2` | `[query 1] model-name: qwen2.5 attribute-tag: 0.5b framwork: mindspeed hardware: a2` | 包含 `Qwen2.5-0.5B [official]` |
| `我要查询 sglang 的框架适配情况` | `【查询1】model-name:  attribute-tag:  framwork: sglang hardware:` | `【查询1】... → 命中 <matches> 个，仅展示前 <shown> 个` |

---

## 新增测试点

### 1. framework-only 查询

本版新增了只咨询框架的用例，例如：

```text
我要查询 sglang 的框架适配情况
我要查询 vllm-ascend 的框架适配情况
mindie 适配框架有哪些模型
query sglang framework adapters
show vllm ascend framework support
list mindie supported model adapters
```

这类输入不应强行识别某个模型，推荐 match 结果为：

```text
【查询1】model-name:  attribute-tag:  framwork: sglang hardware:
```

或英文：

```text
[query 1] model-name:  attribute-tag:  framwork: sglang hardware:
```

### 2. model-name 口径

本测试集继续沿用 v2 口径：

```text
qwen3-30B
```

应识别为：

```text
model-name: qwen3
attribute-tag: 30b
```

不应识别为：

```text
model-name: qwen
attribute-tag: 3, 30b
```

类似规则：

| 输入 | 正确 model-name | 正确 attribute-tag |
|---|---|---|
| `qwen2.5-72b-instruct` | `qwen2.5` | `72b, instruct` |
| `glm-4.7` | `glm4.7` | 空 |
| `deepseek-r1-distill-qwen-32b` | `deepseek-r1` | `distill, qwen, 32b` |
| `minimax-m2.7-80b` | `minimax-m2.7` | `80b` |

### 3. 官方结果优先

对于官方库中存在的适配结果，预期输出会显式包含：

```text
[official]
```

或：

```text
【官方】
```

例如：

```text
qwen2.5 0.5b mindspeed a2
```

预期最终输出中应优先出现：

```text
Model Name: Qwen2.5-0.5B [official]
Framework: mindspeedllm
Hardware: A2,A3
Link: https://gitcode.com/Ascend/MindSpeed-LLM/tree/2.3.0/examples/mcore/qwen25
```

---

## 数据源

当前端到端测试对应两个数据源：

| 数据源 | URL |
|---|---|
| 官方库 | `https://raw.githubusercontent.com/a550580874/ascend-model-repo/refs/heads/main/data/ascend_model_adapters_official.json` |
| 总库 | `https://raw.githubusercontent.com/a550580874/ascend-model-repo/refs/heads/main/data/ascend_model_with_adapter-1-total.json` |

总库包含官方库。测试时需要关注：

1. 官方库命中的结果是否优先。
2. 总库中的三方结果是否仍能正常检索。
3. framework / hardware / attribute-tag 过滤后是否命中正确模型。
4. 只咨询 framework 时，不应误识别为某个具体模型。

---

## 安装依赖

```bash
pip install requests openpyxl urllib3
```

---

## 配置 Dify API Key

推荐使用环境变量，不要把 API Key 写死到脚本里：

```bash
export DIFY_API_KEY="你的 Dify App API Key"
```

Windows PowerShell：

```powershell
$env:DIFY_API_KEY="你的 Dify App API Key"
```

---

## 运行全量测试

```bash
python run_dify_e2e_match_regression_v5.py \
  --cases 模型识别Agent_端到端双层回归测试用例_v5.xlsx \
  --output 模型识别Agent_端到端双层回归测试结果_v5.xlsx \
  --sleep 3 \
  --no-verify
```

参数说明：

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--cases` | `模型识别Agent_端到端双层回归测试用例_v5.xlsx` | 测试用例文件。 |
| `--output` | `模型识别Agent_端到端双层回归测试结果_v5.xlsx` | 测试结果文件。 |
| `--url` | `https://api.dify.ai/v1/chat-messages` | Dify Chat Messages API 地址。 |
| `--api-key` | 环境变量 `DIFY_API_KEY` | Dify App API Key。 |
| `--sleep` | `2` | 每条用例之间的请求间隔，避免触发限流。 |
| `--retries` | `2` | 单条请求失败后的重试次数。 |
| `--retry-sleep` | `5` | 重试间隔，秒。 |
| `--timeout` | `120` | 单条请求超时时间，秒。 |
| `--limit` | `0` | 只跑前 N 条，0 表示全量。 |
| `--offset` | `0` | 从第 N 条后开始跑，便于断点续测。 |
| `--no-verify` | 关闭 | 关闭 SSL 证书校验。 |
| `--match-compare-mode` | `exact` | match 情况比较方式。 |
| `--output-compare-mode` | `placeholder` | 最终输出比较方式。 |

---

## 先跑小批量测试

建议调试阶段先跑前 5 条：

```bash
python run_dify_e2e_match_regression_v5.py \
  --limit 5 \
  --sleep 3 \
  --no-verify
```

从第 20 条开始跑 10 条：

```bash
python run_dify_e2e_match_regression_v5.py \
  --offset 20 \
  --limit 10 \
  --sleep 3 \
  --no-verify
```

---

## 比较逻辑

### 1. match 情况比较

脚本会从 Dify 最终回答中提取类似下面的行：

```text
【查询1】model-name: qwen3 attribute-tag: coder, 32b framwork:  hardware:  → 命中 10 个，仅展示前 8 个
```

提取后只保留：

```text
【查询1】model-name: qwen3 attribute-tag: coder, 32b framwork:  hardware:
```

然后与 Excel 的 `预期match情况` 比较。

默认模式：

```bash
--match-compare-mode exact
```

可选值：

| 模式 | 说明 |
|---|---|
| `exact` | 字段级归一化后完全一致。推荐默认使用。 |
| `contains` | 预期 match 是实际 match 的子串即可。 |
| `none` | 不校验 match。 |

> 注意：match 比较默认不会把中文 `[查询1]` 和英文 `[query 1]` 视为相同。这样可以检查“中文输入是否返回中文格式，英文输入是否返回英文格式”。

### 2. 最终输出比较

默认模式：

```bash
--output-compare-mode placeholder
```

支持 `<matches>` 和 `<shown>` 占位符，例如：

```text
【查询1】model-name: glm5 attribute-tag:  framwork:  hardware: a2 → 命中 <matches> 个，仅展示前 <shown> 个
```

实际输出中只要是：

```text
【查询1】model-name: glm5 attribute-tag:  framwork:  hardware: a2 → 命中 10 个，仅展示前 8 个
```

即可通过。

可选值：

| 模式 | 说明 |
|---|---|
| `placeholder` | 推荐默认。支持 `<matches>` / `<shown>` 通配。 |
| `contains` | 预期输出归一化后是实际输出子串即可。 |
| `exact` | 完全一致。只适合稳定输出。 |
| `none` | 不校验最终输出。 |

---

## 输出结果文件

脚本会生成：

```text
模型识别Agent_端到端双层回归测试结果_v5.xlsx
```

结果 Sheet 包含：

| 列名 | 说明 |
|---|---|
| `序号` | 测试序号。 |
| `输入` | 用户原始 query。 |
| `预期match情况` | Excel 中配置的预期 match。 |
| `实际match情况` | 从 Dify 最终回答中提取到的实际 match。 |
| `是否预期match` | match 是否通过。 |
| `预期输出` | Excel 中配置的最终输出预期。 |
| `实际输出` | Dify 返回的最终回答。 |
| `是否符合预期` | 最终输出是否通过。 |
| `错误信息` | 请求或比较过程中的异常。 |

汇总 Sheet 包含：

| 指标 | 说明 |
|---|---|
| `总用例数` | 实际执行的测试用例数。 |
| `match 通过数` | LLM / match 识别通过数量。 |
| `match 失败数` | LLM / match 识别失败数量。 |
| `最终输出通过数` | 最终检索输出通过数量。 |
| `最终输出失败数` | 最终检索输出失败数量。 |
| `双层均通过数` | match 和最终输出都通过的数量。 |
| `双层均通过率` | 双层均通过数 / 总用例数。 |

---

## 如何定位问题

### 情况 1：match 失败，最终输出也失败

通常说明 LLM 结构化识别阶段就错了。

例子：

```text
输入：qwen3-30B
预期match：model-name: qwen3 attribute-tag: 30b
实际match：model-name: qwen attribute-tag: 3, 30b
```

优先修改：

1. LLM 提示词。
2. structured output schema。
3. 模型名版本归一化规则。

### 情况 2：match 通过，最终输出失败

通常说明 LLM 识别没问题，但代码检索、过滤、排序有问题。

优先检查：

1. 数据源加载是否正确。
2. 官方库是否合并进总库。
3. 官方结果是否排序优先。
4. framework 归一化是否影响展示。
5. hardware 过滤是否正确。
6. attribute-tag 是否参与严格过滤。

### 情况 3：match 通过，最终输出只因命中数失败

如果只是命中数随数据源更新变化，可以继续使用 `<matches>` / `<shown>` 占位符，不要写死数字。

### 情况 4：英文输入返回中文格式

match 会失败，因为本测试集要求：

| 输入语言 | 预期输出格式 |
|---|---|
| 英文 | `[query 1] ... -> 13 matches, showing top 8` |
| 中文 | `【查询1】... → 命中 13 个，仅展示前 8 个` |

---

## 推荐回归流程

1. 修改 LLM 提示词或检索代码。
2. 先运行小批量：

   ```bash
   python run_dify_e2e_match_regression_v5.py --limit 5 --sleep 3 --no-verify
   ```

3. 查看 `是否预期match` 和 `是否符合预期` 两列。
4. 如果小批量通过，再跑全量：

   ```bash
   python run_dify_e2e_match_regression_v5.py --sleep 3 --no-verify
   ```

5. 对失败样例分类：
   - match 失败：LLM 识别问题。
   - match 通过但最终输出失败：代码检索/排序问题。
6. 修复后再次执行回归。
