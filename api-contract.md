# 接口约定

本项目不实现登录和权限控制。仅使用虚构资产元数据。

## 资产输入

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `asset_code` | string | 3–32 字符；正则 `^[A-Z][A-Z0-9-]{2,31}$`；唯一；不自动去空格 |
| `name` | string | 去首尾空格后 1–40 字符 |
| `owner` | string | 去首尾空格后 1–30 字符；使用虚构团队名称 |
| `sensitivity` | string | `public` / `internal` / `confidential` |

字段全部必填；不接受未知字段，不将数字自动转换为字符串。长度按 Python 字符数计算，不是 UTF-8 字节数。

## 路由

| 方法与路径 | 成功 | 常见错误 |
| --- | --- | --- |
| `POST /api/assets` | 201，返回资产 | 422 输入不合法；409 编码已存在 |
| `GET /api/assets?q=&limit=10&offset=0` | 200，`{total, items}` | 422 查询参数不合法 |
| `GET /api/assets/{id}` | 200，返回资产 | 404 不存在；422 ID 不合法 |
| `PUT /api/assets/{id}` | 200，返回更新资产 | 404 不存在；409 编码冲突；422 输入不合法 |
| `DELETE /api/assets/{id}` | 204，无响应体 | 404 不存在；422 ID 不合法 |
| `POST /api/quality/check` | 200，质量报告 | 422 请求结构不合法 |
| `POST /api/cases/evaluate` | 200，用例报告 | 422 请求结构不合法 |

`PUT` 为完整替换输入字段，不是部分更新。`id`、`created_at` 由服务生成，不能作为资产输入提交。更新不会改变创建时间。

列表 `limit` 为 1–100、`offset` 不小于 0；`q` 最长 80 字符。搜索按编码、名称、负责人子串匹配，`%`、`_` 和反斜杠按普通字符搜索，SQL 值使用参数绑定。

质量请求为 `{"records": [对象, ...]}`，1–1000 条。合法请求中的脏记录返回问题报告，不返回 422，也不会导入数据库。相同字符串编码的所有重复记录均标记问题。

## 用例格式

API 请求为 `{"cases": [用例, ...]}`，1–50 条。页面输入只需要内部数组。

```json
{
  "name": "正常新增",
  "method": "POST",
  "path": "/api/assets",
  "scenario": "valid_create",
  "body": {
    "asset_code": "DATA-001",
    "name": "Demo asset",
    "owner": "demo-team",
    "sensitivity": "internal"
  },
  "expected_status": 201,
  "expected_fields": {
    "asset_code": "DATA-001",
    "name": "Demo asset"
  }
}
```

- 用例字段不接受额外属性；`expected_fields` 可省略，最多 10 个顶层响应字段。
- `name` 为 1–120 字符。
- `expected_status` 为整数 `201`、`409` 或 `422`。
- `body` 允许包含非法资产值，以便测试异常路径。
- 只允许 `POST /api/assets`，不允许外部 URL、SQL、脚本或工具调用。
- 字段断言为顶层值相等，不能写表达式、嵌套路径或正则；缺失字段不能等同于 `null`。
- 每条用例新建独立临时数据库，结束后清理；不是在运行中的资产数据库上测试。

## 固定场景

| 标签 | 输入条件 | 通常预期 |
| --- | --- | --- |
| `valid_create` | 所有字段合法，空数据库 | 201 |
| `name_min` | 所有字段合法，去空格后名称恰好 1 字符 | 201 |
| `name_max` | 所有字段合法，去空格后名称恰好 40 字符 | 201 |
| `empty_name` | 唯一字段错误为名称过短，包括全空格 | 422 |
| `name_too_long` | 唯一字段错误为名称过长 | 422 |
| `invalid_code` | 唯一字段错误为编码正则不匹配 | 422 |
| `invalid_sensitivity` | 唯一字段错误为敏感级别枚举不合法 | 422 |
| `duplicate_code` | 字段合法；提交编码 `DUP-001` | 409 |

仅 `duplicate_code` 在测试前预先写入一条合法 `DUP-001` 资产。其他场景都是空数据库，因此将其他编码标记为 `duplicate_code` 并不能产生重复。

多字段错误可以执行并通过状态码断言，但不计入上述“单故障”场景覆盖。标签不匹配也不计入覆盖；报告单独显示 `scenario_matches: false`。8 个标签不是完整测试集，不包括权限、性能或生产安全保障。
