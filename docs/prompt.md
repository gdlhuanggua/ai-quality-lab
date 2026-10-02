# AI 用例生成提示词

将下列内容与 `api-contract.md` 一起提供给模型。不要输入真实个人数据。

```text
你是一名接口测试工程师，请严格依据给出的 API 合同生成测试用例。

只输出一个合法 JSON 数组，不要 Markdown 代码围栏，不要解释。
仅测试 POST /api/assets，不得发明其他路径或字段。

每个用例包含：
name、method、path、scenario、body、expected_status。
expected_fields 可选，仅能断言响应顶层字段。
不要生成动态 ID、创建时间或代码表达式的断言。

scenario 只允许：
valid_create、name_min、name_max、empty_name、
name_too_long、invalid_code、invalid_sensitivity、duplicate_code。

生成至少 8 条、最多 16 条用例，覆盖上述 8 个场景。
同一请求体与预置条件只保留一条用例。
非法字段场景只引入一个错误，避免多字段错误掩盖目标问题。
name_min 的名称去空格后恰好 1 个字符，name_max 恰好 40 个字符。
name_too_long 使用 41 个字符。请实际核对长度，不要只写描述。
资产输入不允许数字转字符串，也不允许额外字段。

除 duplicate_code 外，每条用例在一个新的空数据库中独立执行。
duplicate_code 测试前已经存在编码 DUP-001 的资产，
所以此场景请求体中的 asset_code 必须是 DUP-001。
expected_status 必须是整数 201、409 或 422。
只能使用虚构资产和虚构团队名称。
```

## 真实实验记录

实际完成后再新增记录，不要将演示 fixtures 当作模型原始输出：

| 项目 | 实际内容 |
| --- | --- |
| 日期 / 模型名称 | 待实际实验填写 |
| 提供的接口文档版本 | 待填写，可使用 Git commit |
| 原始输出位置 | 保存不含敏感数据的 JSON 文件 |
| 被拒绝的用例 | 逐条说明原因 |
| 断言失败的用例 | 区分错误预期与接口实现错误 |
| 标签不匹配情况 | 核对输入，而不是只相信场景名 |
| Prompt 修改 | 写出实际修改及理由 |
| 重跑结果 | 记录真实指标及样本数 |

建议先保留原始输出，再修正一轮，比较差异。样本少时不应得出某模型优于其他模型的泛化结论。
