# 票小智（InvoiceAgent）产品需求文档 (PRD)

## 文档信息

| 项目 | 内容 |
| --- | --- |
| 产品名称 | 票小智（InvoiceAgent）—— 数电发票报销 AI 助手 |
| Slogan | 一键接入，AI 自动核销报销 |
| 文档版本 | v1.0.0 |
| 文档状态 | Draft（待评审） |
| 编写日期 | 2026-06-15 |
| 修订记录 | v1.0.0 / 2026-06-15 / 初稿，基于 InvoiceWorker 内部系统封装产品化 |
| 适用范围 | 产品、研发、测试、运营、商务、客户成功团队 |
| 关联系统 | InvoiceWorker（内部 PoC 原型） |

---

## 1. 产品概述

### 1.1 产品愿景

构建中国中小企业财务领域最易用、最可信赖的"数电发票全生命周期 AI 处理中枢"。让企业财务从重复的发票核对、邮件下载、报销单填写、PDF 比对中彻底解放出来，让 AI Agent 7×24 小时自动完成"收—核—报—档"全流程，实现"零人工触达"的发票报销自动化。

### 1.2 产品定位

- **品类**：面向中小企业财务部门的 AI Agent SaaS 产品（垂直领域 Agent）。
- **场景**：数电发票（全电发票）从员工提交到企业入账归档的全链路自动化处理。
- **差异点**：
  1. 多模态大模型（qwen-vl 系列）直接读取 PDF/图片发票，无需 OCR 模板。
  2. 邮箱 + 手工 + 上传三通道融合，覆盖企业 90% 以上发票来源。
  3. 以"全量发票基础信息表"为唯一可信源，匹配-核销-报销三阶闭环。
  4. 开箱即用：注册即可用，30 分钟完成接入。

### 1.3 目标用户画像

| 用户角色 | 规模特征 | 核心痛点 | 期望价值 |
| --- | --- | --- | --- |
| 财务主管（决策者） | 50–500 人企业 | 月底报销审核压力大、错单频发 | 月节约 30% 财务工时，错单率 < 1% |
| 财务专员（核心使用者） | 1–5 人小型财务团队 | 每月手工核对 200+ 张发票、Excel 与 PDF 来回切换 | AI 自动核销、一键导出报销单 |
| 报销员工（高频用户） | 全员 | 不会填报销单、找不到发票 PDF | 微信/邮箱提交即可，状态实时通知 |
| IT 管理员（接入者） | 1–2 人 IT | 担心数据安全、对接 ERP/钉钉成本高 | 标准 OpenAPI、私有化部署可选 |
| 老板（付费决策者） | 总经理/CFO | 关心 ROI、合规与税务风险 | 月度报表清晰、留痕可审计 |

### 1.4 核心价值主张

1. **降本**：单张发票处理成本由人工 ¥3 降至 AI ¥0.1（按量计费）。
2. **提速**：月末报销周期由 5 天缩短至 1 天。
3. **降错**：发票号、金额、抬头自动比对，避免人工肉眼对账失误。
4. **合规**：所有操作可审计、可回溯，满足内控与税务稽查留痕要求。
5. **易用**：面向"非技术财务"，全中文向导式操作，零代码接入邮箱与 ERP。

---

## 2. 系统架构设计

### 2.1 整体架构图（文字描述）

```
┌──────────────────────────────────────────────────────────────────┐
│                        接入层（Access Layer）                     │
│  Web 控制台 │ 钉钉/企微小程序 │ OpenAPI │ Webhook │ 邮箱机器人      │
└────────────────────┬─────────────────────────────────────────────┘
                     │  HTTPS / WSS / OAuth2
┌────────────────────▼─────────────────────────────────────────────┐
│                       网关层（API Gateway）                       │
│   认证鉴权 │ 限流熔断 │ 多租户路由 │ 请求审计 │ 加密                │
└────────────────────┬─────────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────────┐
│                   AI Agent 编排层（Orchestrator）                 │
│  任务调度器 │ 工作流引擎 │ Agent 路由 │ 上下文管理 │ Tool 注册中心   │
└─┬──────────┬──────────┬──────────┬──────────┬──────────┬─────────┘
  │          │          │          │          │          │
  ▼          ▼          ▼          ▼          ▼          ▼
┌────┐   ┌────┐    ┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐
│导入│   │邮箱│    │视觉  │   │报销  │   │规则  │   │通知  │
│Agent│  │Agent│   │识别  │   │Agent │   │Agent │   │Agent │
│    │   │    │    │Agent │   │      │   │      │   │      │
└─┬──┘   └─┬──┘    └─┬────┘   └─┬────┘   └─┬────┘   └─┬────┘
  │        │         │          │           │         │
┌─▼────────▼─────────▼──────────▼───────────▼─────────▼──────────┐
│                         能力服务层                               │
│  Excel Parser │ IMAP Fetcher │ LLM Provider │ PDF Renderer │     │
│  规则引擎     │ 工作流引擎    │ 通知中心     │ 文件存储      │     │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                      数据与基础设施层                            │
│  PostgreSQL │ Redis │ 对象存储(OSS/MinIO) │ 消息队列 │ 监控告警  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Agent 模块划分

| Agent 名称 | 职责 | 关键工具（Tool） |
| --- | --- | --- |
| 导入 Agent | 解析全量发票基础信息表（xlsx），去重入库 | excel_parser, dedup_checker |
| 邮箱 Agent | 周期拉取邮件，通过主题/附件名提取发票号 | imap_fetcher, regex_matcher, attachment_downloader |
| 视觉识别 Agent | 调用 qwen-vl 多模态模型识别 PDF/图片中的发票号、金额 | llm_vision, pdf_to_image, field_extractor |
| 报销 Agent | 组装报销单、生成报销单 PDF、关联发票明细 | reimb_compiler, pdf_renderer, signature |
| 规则 Agent | 执行企业自定义匹配/审批规则 | rule_engine, expression_eval |
| 通知 Agent | 邮件/钉钉/企微/短信多通道消息推送 | dingtalk_bot, wecom_bot, smtp_sender |

### 2.3 部署模式

| 模式 | 适用客户 | 数据存储 | LLM 调用 | 价格策略 |
| --- | --- | --- | --- | --- |
| **公有云 SaaS（默认）** | 50–200 人企业 | 多租户 PostgreSQL（Schema 隔离） | 公共 DashScope 通道 | 按量/订阅 |
| **专属云（VPC）** | 200–500 人、对数据敏感 | 独立数据库实例 | 独立 LLM 配额 | 年费 + 服务费 |
| **私有化部署** | 国企、金融、有合规强约束 | 客户内网 PostgreSQL | 客户自备 LLM API Key 或本地 Qwen 模型 | License + 实施费 |
| **混合模式** | 集团总部 SaaS + 子公司私有 | SaaS 主控台 + 边缘数据节点 | 双通道 | 定制 |

### 2.4 与第三方系统集成方案

| 系统类别 | 代表产品 | 集成方式 | 同步内容 |
| --- | --- | --- | --- |
| ERP | 用友 U8/NC、金蝶 K3/EAS | OpenAPI + 凭证导出 | 发票、报销单、入账凭证 |
| 协同办公 | 钉钉、企业微信、飞书 | 应用市场 + 机器人 | 提交、审批、通知 |
| 邮件系统 | Exchange、腾讯企业邮、阿里云邮 | IMAP/EWS | 拉取发票邮件 |
| 税务系统 | 全国增值税发票查验平台 | HTTP 转发 | 发票真伪查验 |
| 报销/费控 | 易快报、汇联易 | Webhook + OpenAPI | 单据状态同步 |

---

## 3. 功能需求规格

### 3.1 租户管理模块

> 解决多企业、多组织、多用户的隔离与权限治理。

**用户故事**

- **US-3.1.1** 作为 IT 管理员，我希望注册企业租户并完成实名认证，以便开通票小智服务。
  - AC1：通过手机号 + 邮箱 + 营业执照上传，10 分钟内完成租户初始化。
  - AC2：每个租户分配唯一 `tenant_id`，所有数据物理隔离或 Schema 隔离。
  - AC3：未完成实名前仅可使用试用额度（≤ 50 张发票）。

- **US-3.1.2** 作为 IT 管理员，我希望批量邀请部门员工，以便快速开通账号。
  - AC1：支持 Excel 批量导入 / 钉钉/企微通讯录同步。
  - AC2：被邀请人通过邮件/短信链接 24 小时内激活。
  - AC3：账号支持禁用、重置密码、强制下线。

- **US-3.1.3** 作为财务主管，我希望为不同角色配置不同权限，以便财务数据按需访问。
  - AC1：内置"超级管理员/财务主管/财务专员/普通员工"四角色，可自定义。
  - AC2：权限粒度到模块 + 操作（如"报销单-审批"）。
  - AC3：变更操作有审计日志。

- **US-3.1.4** 作为超级管理员，我希望按部门/项目划分预算，以便费用归集。
  - AC1：支持多级部门树（≥ 5 级）。
  - AC2：报销单可关联部门、项目、成本中心。
  - AC3：预算超额时提示并需上级审批。

- **US-3.1.5** 作为租户老板，我希望切换企业（多企业兼任老板），以便统一管理。
  - AC1：同一手机号可绑定多个 `tenant_id`。
  - AC2：登录后可一键切换企业上下文。

### 3.2 发票数据导入模块

> 以全量发票基础信息表（xlsx）为唯一可信源。

**用户故事**

- **US-3.2.1** 作为财务专员，我希望从税务局下载的 xlsx 直接上传，以便建立月度发票底账。
  - AC1：支持税务局标准模板（数电发票查询导出结果）。
  - AC2：单文件 ≤ 50MB，发票数 ≤ 5 万行。
  - AC3：解析失败行单独导出 error.xlsx 供修正。

- **US-3.2.2** 作为财务专员，我希望系统自动去重，以便避免同一发票号多次入库。
  - AC1：以 `数电票号 + 开票日期` 为唯一键去重。
  - AC2：重复行不入库但写入"导入日志"。
  - AC3：去重比例在导入完成页可视化。

- **US-3.2.3** 作为财务专员，我希望查看历史导入批次，以便回滚错误数据。
  - AC1：每次导入生成一条 `import_batch` 记录。
  - AC2：支持按批次回滚（软删除 + 恢复）。
  - AC3：回滚后关联的报销单需提示关联失效。

- **US-3.2.4** 作为财务主管，我希望按月/季度查看发票总量、金额，以便快速掌握盘子。
  - AC1：仪表盘展示按月柱图、按部门饼图、按品名 Top10。
  - AC2：可下钻到明细列表。

- **US-3.2.5** 作为开发者，我希望通过 API 上传发票数据，以便对接 ERP 自动同步。
  - AC1：`POST /api/v1/invoices/import` 支持 multipart 与 JSON。
  - AC2：异步任务返回 `task_id`，通过 Webhook 通知结果。

### 3.3 邮箱自动核销模块

> 自动从企业邮箱拉取发票邮件并核销底账。

**用户故事**

- **US-3.3.1** 作为财务专员，我希望配置一个或多个邮箱账号，以便自动收件。
  - AC1：支持 IMAP / Exchange / OAuth2（QQ、网易、企业微信邮、Gmail）。
  - AC2：密码/Token 加密存储（AES-256-GCM）。
  - AC3：连通性测试通过后才可保存。

- **US-3.3.2** 作为财务专员，我希望系统每隔 X 分钟自动拉取邮件，以便实时核销。
  - AC1：拉取频率可配置（5/15/30/60 分钟）。
  - AC2：拉取范围可设白名单发件人、关键词、时间窗口。
  - AC3：单次拉取 ≤ 200 封，超出分批。

- **US-3.3.3** 作为系统，我希望从邮件主题/附件名/正文中提取数电发票号，以便核销。
  - AC1：内置正则识别 20 位数电票号准确率 ≥ 99%。
  - AC2：未识别邮件进入"待人工确认"队列。
  - AC3：识别出的发票号若不在底账中，标记为"孤儿发票"。

- **US-3.3.4** 作为财务专员，我希望邮箱核销结果有清晰的状态标识，以便审计。
  - AC1：每张发票具有 `匹配状态`：未匹配 / 邮箱已匹配 / 手工已匹配 / 已报销。
  - AC2：匹配记录关联邮件原文与附件。

- **US-3.3.5** 作为财务专员，我希望对邮箱拉取异常收到告警，以便及时处理。
  - AC1：连续 3 次拉取失败发邮件 + 站内信告警。
  - AC2：账号密码失效自动标红并暂停拉取。

### 3.4 AI 视觉识别匹配模块

> 通过多模态大模型识别 PDF/图片发票字段并比对底账。

**用户故事**

- **US-3.4.1** 作为财务专员，我希望上传单张/多张发票 PDF/图片，以便 AI 自动识别。
  - AC1：支持 PDF、JPG、PNG，单文件 ≤ 10MB，批量 ≤ 50 张。
  - AC2：识别字段：数电票号、开票日期、销方、购方、金额、税额。
  - AC3：识别耗时 P95 ≤ 8 秒/张。

- **US-3.4.2** 作为系统，我希望识别结果与底账自动比对，以便核销。
  - AC1：发票号完全匹配视为命中。
  - AC2：金额 / 销方 / 抬头任一不一致时，标"疑似异常"并要求确认。
  - AC3：未在底账中的发票标"孤儿"，可一键加入底账。

- **US-3.4.3** 作为财务专员，我希望对 AI 识别错误的字段手动修正，以便回流训练。
  - AC1：识别结果可逐字段编辑。
  - AC2：修改记录留痕，作为 Bad Case 反馈到优化通道。

- **US-3.4.4** 作为财务主管，我希望查看 AI 识别准确率与置信度，以便评估效果。
  - AC1：仪表盘展示日/周/月识别准确率。
  - AC2：低置信度（< 0.85）发票自动进入"复核队列"。

- **US-3.4.5** 作为开发者，我希望通过 API 调用识别能力，以便嵌入自有产品。
  - AC1：`POST /api/v1/recognize` 接收 base64 或 URL。
  - AC2：单次请求计 1 次识别量。

### 3.5 报销流程管理模块

> 支持员工提交、主管审批、财务复核、生成报销单 PDF。

**用户故事**

- **US-3.5.1** 作为报销员工，我希望选择一张或多张已核销的发票生成报销单，以便提交报销。
  - AC1：仅"已匹配"或"已识别"的发票可被勾选。
  - AC2：报销单自动汇总金额、税额、张数。
  - AC3：可填写报销事由、关联项目、成本中心。

- **US-3.5.2** 作为部门主管，我希望按预设流程审批报销单，以便控制费用。
  - AC1：内置流程：员工 → 部门主管 → 财务专员 → 财务主管。
  - AC2：金额阈值可触发额外审批节点（≥ 5 万走 CFO）。
  - AC3：支持加签、转交、退回。

- **US-3.5.3** 作为财务专员，我希望一键导出报销单 PDF + 发票清单，以便归档打印。
  - AC1：PDF 含报销单封面、发票清单页、签名位、二维码。
  - AC2：附件可打包为 ZIP（PDF + 原始发票 PDF）。

- **US-3.5.4** 作为报销员工，我希望随时查看报销单状态，以便不再追问。
  - AC1：状态：草稿 / 审批中 / 通过 / 驳回 / 已打款。
  - AC2：流转节点可视化。

- **US-3.5.5** 作为财务主管，我希望按月对账已报销发票，以便防止重复报销。
  - AC1：同一发票号 + 同一报销人不可重复报销。
  - AC2：跨月重复报销系统提示。

### 3.6 开放 API 与集成模块

> 让票小智成为企业财务体系的"中枢能力"。

**用户故事**

- **US-3.6.1** 作为开发者，我希望使用 API Key + Secret 调用接口，以便接入 ERP。
  - AC1：控制台可创建/吊销 API Key。
  - AC2：HMAC-SHA256 签名校验。
  - AC3：所有调用计入日志，可按 Key 维度统计。

- **US-3.6.2** 作为开发者，我希望订阅事件（Webhook），以便实时同步。
  - AC1：事件类型：invoice.imported、invoice.matched、reimb.approved、reimb.paid。
  - AC2：失败自动重试 5 次（指数退避）。
  - AC3：可在控制台查看推送历史与重发。

- **US-3.6.3** 作为开发者，我希望对接钉钉/企微，以便用户在 IM 内审批。
  - AC1：提供官方应用模板，授权后即可使用。
  - AC2：审批结果回写票小智。

- **US-3.6.4** 作为开发者，我希望调用税务发票查验 API，以便核验真伪。
  - AC1：传入发票号、开票日期、金额校验码。
  - AC2：返回真/伪 + 详细信息。

- **US-3.6.5** 作为 ERP 厂商，我希望以 OEM 方式嵌入票小智，以便对外输出能力。
  - AC1：提供白标控制台、SSO 登录。
  - AC2：分润结算按月。

### 3.7 监控与告警模块

> 保障 SLA、定位故障、产品自身可观测。

**用户故事**

- **US-3.7.1** 作为运维，我希望查看系统级仪表盘，以便掌握健康度。
  - AC1：核心指标：QPS、P95、错误率、LLM 成功率、邮箱拉取成功率。
  - AC2：分租户视图。

- **US-3.7.2** 作为运维，我希望对关键指标异常告警，以便及时介入。
  - AC1：错误率 > 1%、P95 > 2s、LLM 失败率 > 5% 触发告警。
  - AC2：告警通道：钉钉、企微、邮件、电话。

- **US-3.7.3** 作为客户成功，我希望看到客户使用情况，以便主动服务。
  - AC1：每个租户的活跃度、用量、留存可视化。
  - AC2：临近额度上限自动通知销售。

- **US-3.7.4** 作为审计员，我希望查询任意操作的审计日志，以便追溯责任。
  - AC1：保存 ≥ 180 天，关键操作 ≥ 3 年。
  - AC2：日志不可篡改（哈希链）。

- **US-3.7.5** 作为运维，我希望进行混沌演练，以便验证容灾。
  - AC1：每季度一次故障注入演练。
  - AC2：核心链路 RTO ≤ 30 分钟。

---

## 4. API 接口设计规格

### 4.1 认证机制

- **方式 1（用户态）**：账号密码 → JWT（HS256），有效期 2 小时，Refresh Token 7 天。
- **方式 2（机器态）**：API Key + Secret，HMAC-SHA256 签名。
  - 签名串：`HTTP-METHOD\nURI\nTIMESTAMP\nNONCE\nBODY-SHA256`
  - Header：`X-Tenant-Id`、`X-Api-Key`、`X-Timestamp`、`X-Nonce`、`X-Signature`
- **多租户路由**：所有请求必须携带 `X-Tenant-Id`，网关层校验后注入下游。
- **限流**：默认 100 QPS / 租户，可按套餐升级。

### 4.2 接口总览表

| 模块 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| 认证 | POST | /api/v1/auth/login | 账号密码登录 |
| 认证 | POST | /api/v1/auth/refresh | 刷新 Token |
| 租户 | POST | /api/v1/tenants | 创建租户 |
| 租户 | GET | /api/v1/tenants/me | 当前租户信息 |
| 用户 | POST | /api/v1/users/invite | 邀请用户 |
| 发票 | POST | /api/v1/invoices/import | 上传 xlsx 导入 |
| 发票 | GET | /api/v1/invoices | 发票列表（分页） |
| 发票 | GET | /api/v1/invoices/{id} | 发票详情 |
| 邮箱 | POST | /api/v1/emails/configs | 创建邮箱配置 |
| 邮箱 | POST | /api/v1/emails/fetch | 立即拉取 |
| 识别 | POST | /api/v1/recognize | 视觉识别单/批 |
| 匹配 | POST | /api/v1/match/manual | 手动匹配 |
| 报销 | POST | /api/v1/reimbursements | 创建报销单 |
| 报销 | POST | /api/v1/reimbursements/{id}/submit | 提交审批 |
| 报销 | POST | /api/v1/reimbursements/{id}/approve | 审批 |
| 报销 | GET | /api/v1/reimbursements/{id}/pdf | 导出 PDF |
| Webhook | POST | /api/v1/webhooks | 注册 Webhook |
| 监控 | GET | /api/v1/metrics | 监控指标 |

### 4.3 核心接口详细定义

#### 4.3.1 发票导入 `POST /api/v1/invoices/import`

请求（multipart/form-data）：

```
file: <xlsx 文件>
batch_name: "2026-06 月度底账"
async: true
```

响应（202 Accepted）：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "imp_20260615_abc123",
    "status": "queued",
    "estimated_seconds": 30,
    "callback_url": "https://yourapp.com/webhook/invoice"
  }
}
```

任务完成 Webhook：

```json
{
  "event": "invoice.imported",
  "tenant_id": "t_8a9f1c",
  "task_id": "imp_20260615_abc123",
  "data": {
    "total_rows": 1280,
    "success": 1265,
    "duplicated": 12,
    "failed": 3,
    "error_file_url": "https://oss.../error_imp_20260615_abc123.xlsx"
  },
  "timestamp": 1781000000,
  "signature": "sha256=..."
}
```

#### 4.3.2 视觉识别 `POST /api/v1/recognize`

请求：

```json
{
  "files": [
    { "type": "url", "value": "https://oss.../invoice_1.pdf" },
    { "type": "base64", "value": "JVBERi0xLjQKJ..." }
  ],
  "auto_match": true,
  "match_strategy": "strict"
}
```

响应：

```json
{
  "code": 0,
  "data": {
    "results": [
      {
        "file_index": 0,
        "invoice_no": "26337000000406417193",
        "invoice_date": "2026-06-07",
        "seller": "杭州传达网络科技有限公司",
        "buyer": "示例科技有限公司",
        "amount": 1280.00,
        "tax": 76.80,
        "confidence": 0.98,
        "match_status": "matched",
        "matched_invoice_id": "inv_92a8e1"
      },
      {
        "file_index": 1,
        "invoice_no": null,
        "confidence": 0.42,
        "match_status": "low_confidence",
        "error": "图片模糊，请重新上传"
      }
    ],
    "billing": { "recognize_count": 2 }
  }
}
```

#### 4.3.3 创建报销单 `POST /api/v1/reimbursements`

请求：

```json
{
  "title": "2026-06 差旅报销-张三",
  "applicant_id": "u_001",
  "department_id": "d_010",
  "project_id": "p_2026Q2",
  "reason": "上海客户拜访差旅",
  "invoice_ids": ["inv_92a8e1", "inv_92a8e2", "inv_92a8e3"]
}
```

响应：

```json
{
  "code": 0,
  "data": {
    "id": "reimb_20260615_001",
    "code": "BX202606150001",
    "status": "draft",
    "total_amount": 3850.00,
    "total_tax": 230.50,
    "invoice_count": 3,
    "created_at": "2026-06-15T10:23:11+08:00"
  }
}
```

#### 4.3.4 报销单 PDF 导出 `GET /api/v1/reimbursements/{id}/pdf`

请求：`GET /api/v1/reimbursements/reimb_20260615_001/pdf?with_attachments=true`

响应（200，application/pdf 或 application/zip）：直接返回二进制流，文件名 `BX202606150001.pdf`。

#### 4.3.5 邮箱拉取 `POST /api/v1/emails/fetch`

请求：

```json
{
  "config_id": "ec_001",
  "since": "2026-06-01T00:00:00+08:00",
  "max_messages": 200
}
```

响应：

```json
{
  "code": 0,
  "data": {
    "fetched": 87,
    "with_invoice": 65,
    "matched": 60,
    "unmatched": 5,
    "duration_ms": 12300
  }
}
```

#### 4.3.6 通用错误码

| code | http | 含义 |
| --- | --- | --- |
| 0 | 200 | 成功 |
| 40001 | 400 | 参数错误 |
| 40101 | 401 | 未登录或 Token 失效 |
| 40301 | 403 | 无权限 |
| 40401 | 404 | 资源不存在 |
| 42901 | 429 | 限流 |
| 50001 | 500 | 服务内部错误 |
| 50301 | 503 | LLM 上游不可用 |

---

## 5. 数据模型设计

### 5.1 核心实体关系

```
Tenant (1) ──< (N) User
Tenant (1) ──< (N) Department ──< (N) User
Tenant (1) ──< (N) Invoice (主表) ──< (N) InvoiceDetail (明细)
Tenant (1) ──< (N) EmailConfig ──< (N) EmailMessage
Tenant (1) ──< (N) ManualMatch ──> (1) Invoice
Tenant (1) ──< (N) Reimbursement ──< (N) ReimbursementItem ──> (1) Invoice
Tenant (1) ──< (N) ApiKey
Tenant (1) ──< (N) Webhook
```

### 5.2 多租户数据隔离策略

| 隔离级别 | 适用套餐 | 实现方式 | 优劣 |
| --- | --- | --- | --- |
| 行级（默认） | 标准版 | 所有表带 `tenant_id`，查询强制注入 | 成本低、运维简单；隔离性中等 |
| Schema 级 | 旗舰版 | 每租户独立 Schema，连接池路由 | 较强隔离；备份恢复独立 |
| 实例级 | 私有部署 | 独立数据库实例 | 强隔离；运维成本高 |

**通用原则**：
- ORM 层默认拦截器自动追加 `tenant_id` 条件，防越权。
- 所有索引以 `(tenant_id, ...)` 起始，避免热点扫描。
- 软删除字段 `deleted_at`，物理删除按合规策略 90/180/365 天。

### 5.3 关键表结构设计

#### 5.3.1 tenants 租户表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | varchar(32) PK | 租户 ID（t_前缀） |
| name | varchar(128) | 企业名称 |
| credit_code | varchar(32) | 统一社会信用代码 |
| plan | varchar(16) | 套餐：trial/standard/pro/enterprise |
| status | varchar(16) | active/suspended/closed |
| quota_invoice | int | 月发票额度 |
| quota_recognize | int | 月识别额度 |
| created_at | timestamptz | 创建时间 |
| updated_at | timestamptz | 更新时间 |

#### 5.3.2 users 用户表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | varchar(32) PK | 用户 ID |
| tenant_id | varchar(32) FK | 租户 ID |
| username | varchar(64) | 登录账号 |
| password_hash | varchar(128) | bcrypt |
| phone | varchar(20) | 手机号 |
| email | varchar(128) | 邮箱 |
| role | varchar(32) | super_admin/finance_lead/finance/employee |
| department_id | varchar(32) | 部门 |
| status | varchar(16) | active/disabled |
| last_login_at | timestamptz | 最近登录 |
| created_at | timestamptz |  |

#### 5.3.3 invoices 发票主表（基于现有 invoice.py 扩展）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | varchar(32) PK | 发票 ID |
| tenant_id | varchar(32) FK | 租户 ID |
| invoice_no | varchar(32) | 数电票号（20 位） |
| invoice_date | date | 开票日期 |
| seller_name | varchar(255) | 销方 |
| seller_taxno | varchar(32) | 销方税号 |
| buyer_name | varchar(255) | 购方 |
| buyer_taxno | varchar(32) | 购方税号 |
| total_amount | decimal(14,2) | 价税合计 |
| amount | decimal(14,2) | 金额（不含税） |
| tax | decimal(14,2) | 税额 |
| match_status | varchar(16) | unmatched/email_matched/manual_matched/reimbursed |
| match_method | varchar(16) | email/manual/api |
| source_batch_id | varchar(32) | 导入批次 |
| pdf_url | varchar(512) | 关联 PDF 存储路径 |
| created_at | timestamptz |  |
| updated_at | timestamptz |  |

唯一约束：`(tenant_id, invoice_no, invoice_date)`。

#### 5.3.4 invoice_details 发票明细表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | varchar(32) PK |  |
| tenant_id | varchar(32) |  |
| invoice_id | varchar(32) FK |  |
| goods_name | varchar(255) | 货物或应税劳务名称 |
| spec | varchar(128) | 规格型号 |
| unit | varchar(32) |  |
| quantity | decimal(18,4) |  |
| unit_price | decimal(18,4) |  |
| amount | decimal(14,2) |  |
| tax_rate | decimal(6,4) |  |
| tax | decimal(14,2) |  |
| match_method | varchar(16) | 同主表 |

#### 5.3.5 email_configs 邮箱配置

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | varchar(32) PK |  |
| tenant_id | varchar(32) |  |
| protocol | varchar(16) | imap/exchange/oauth2 |
| host | varchar(128) |  |
| port | int |  |
| username | varchar(128) |  |
| password_enc | text | AES-256-GCM 加密 |
| use_ssl | boolean |  |
| fetch_interval_min | int | 拉取频率 |
| filter_keywords | jsonb | 主题/发件人白名单 |
| status | varchar(16) | active/disabled/error |
| last_fetch_at | timestamptz |  |

#### 5.3.6 reimbursements 报销单

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | varchar(32) PK |  |
| tenant_id | varchar(32) |  |
| code | varchar(32) | 业务单号 BXyyyymmddxxxx |
| title | varchar(255) |  |
| applicant_id | varchar(32) | 申请人 |
| department_id | varchar(32) |  |
| project_id | varchar(32) |  |
| reason | text |  |
| total_amount | decimal(14,2) |  |
| total_tax | decimal(14,2) |  |
| invoice_count | int |  |
| status | varchar(16) | draft/submitted/approving/approved/rejected/paid |
| current_node | varchar(64) |  |
| created_at | timestamptz |  |
| approved_at | timestamptz |  |
| paid_at | timestamptz |  |

#### 5.3.7 reimbursement_items 报销明细

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | varchar(32) PK |  |
| reimbursement_id | varchar(32) FK |  |
| invoice_id | varchar(32) FK |  |
| amount | decimal(14,2) | 本次报销金额（支持部分报销） |

#### 5.3.8 audit_logs 审计日志

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigserial PK |  |
| tenant_id | varchar(32) |  |
| user_id | varchar(32) |  |
| action | varchar(64) | login/import/recognize/approve/... |
| resource_type | varchar(32) |  |
| resource_id | varchar(32) |  |
| ip | inet |  |
| user_agent | text |  |
| payload | jsonb |  |
| hash_chain | varchar(64) | 链式哈希，防篡改 |
| created_at | timestamptz |  |

---

## 6. 非功能性需求

### 6.1 性能要求

| 指标 | 目标值 |
| --- | --- |
| Web 页面首屏 | < 1.5s（4G 网络） |
| 普通 API P95 | < 300ms |
| 视觉识别 P95 | < 8s/张 |
| 邮箱拉取 200 封 | < 60s |
| 单租户最大发票量 | 1000 万行（PostgreSQL 分区表） |
| 并发租户 | ≥ 5000 |

### 6.2 安全要求

- 全站 HTTPS，TLS 1.2+。
- 密码 bcrypt（cost=12），邮箱密码 AES-256-GCM，密钥由 KMS 管理。
- 敏感字段脱敏展示（如银行卡、身份证）。
- 防 OWASP Top 10：SQL 注入、XSS、CSRF、SSRF、越权。
- 审计日志哈希链，180 天热数据 + 3 年冷归档。
- 通过等保三级、ISO 27001（目标）。

### 6.3 可用性要求

| 项目 | 目标 |
| --- | --- |
| 服务可用性 SLA | 99.9%（月度） |
| 故障 RTO | ≤ 30 分钟 |
| 数据 RPO | ≤ 5 分钟 |
| 数据备份 | 每日全量 + 实时 WAL，异地双活 |
| 大版本发布 | 灰度 1% → 10% → 全量，可秒级回滚 |

### 6.4 扩展性要求

- 微服务化：按 Agent 维度拆分，独立扩缩容。
- LLM Provider 可插拔：Qwen-VL / GPT-4o / 国内合规模型可切换。
- 工作流引擎可视化：审批流可由租户自定义。
- 国际化预留：i18n 资源文件，时区/币种/税制可配置。

---

## 7. 商业化设计

### 7.1 定价模型

| 套餐 | 月费（含税） | 包含发票数 | 包含识别数 | 用户数 | 邮箱数 |
| --- | --- | --- | --- | --- | --- |
| Trial（试用） | 0 | 50 | 30 | 3 | 1 |
| Starter | ¥299/月 | 500 | 300 | 10 | 1 |
| Standard | ¥999/月 | 2000 | 1500 | 30 | 3 |
| Pro | ¥2999/月 | 8000 | 6000 | 100 | 10 |
| Enterprise | 商务洽谈 | 不限 | 不限 | 不限 | 不限 |

超额部分按量计费：
- 发票存储 ¥0.05/张
- AI 识别 ¥0.10/次
- PDF 导出 ¥0.02/份

### 7.2 功能分级矩阵

| 功能 | Trial | Starter | Standard | Pro | Enterprise |
| --- | :---: | :---: | :---: | :---: | :---: |
| 发票导入 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 邮箱核销 | × | ✓ | ✓ | ✓ | ✓ |
| AI 视觉识别 | ✓(限量) | ✓ | ✓ | ✓ | ✓ |
| 报销审批流 | × | 单级 | 多级 | 多级+条件 | 自定义 |
| OpenAPI | × | × | ✓ | ✓ | ✓ |
| Webhook | × | × | ✓ | ✓ | ✓ |
| 钉钉/企微 | × | × | ✓ | ✓ | ✓ |
| ERP 对接 | × | × | × | ✓ | ✓ |
| 私有化部署 | × | × | × | × | ✓ |
| SLA 99.9% | × | × | ✓ | ✓ | ✓ |
| 专属客服 | × | × | × | ✓ | ✓ |

### 7.3 计量与计费机制

- **计量维度**：发票存储数（去重后）、AI 识别次数、API 调用次数、用户数、存储空间。
- **采集**：每次业务事件实时写 Kafka，分钟级落计量库。
- **结算**：自然月结，月初 1 号生成账单，3 个工作日内出具发票。
- **超量策略**：默认按超量单价扣费；可设置硬封顶（达到上限后停服）。
- **预付费**：按年订阅享 8 折，按 3 年享 6 折。
- **代金券**：支持渠道分销码、首月免费、邀请奖励。

---

## 8. 发布路线图

### Phase 1：MVP（第 1–2 月）

**目标**：内部 InvoiceWorker 原型 → 多租户 SaaS Demo，签约 3 家种子客户。

- 多租户改造：行级隔离、JWT 鉴权、API Key。
- 数据库迁移：SQLite → PostgreSQL，所有表加 `tenant_id`。
- 复用现有四步骤功能（导入、邮箱、视觉识别、报销）。
- 控制台基础页面（登录、租户、用户、发票、报销）。
- 部署到公有云 K8s，灰度域名。
- **里程碑**：3 家种子客户上线试用，月处理发票 ≥ 1000 张。

### Phase 2：标准化（第 3–4 月）

**目标**：商业化产品 GA，签约 30+ 家付费客户。

- 计量计费系统、订阅与开发票流程。
- 钉钉 / 企微应用上线。
- 完整审批流引擎（含金额阈值、加签、转交）。
- OpenAPI v1 + Webhook + SDK（Python、Java）。
- 监控告警体系（Prometheus + Grafana + 钉钉机器人）。
- 客户成功后台与主动服务流程。
- **里程碑**：MRR ≥ ¥5 万，NPS ≥ 40。

### Phase 3：智能化（第 5–8 月）

**目标**：AI 体验领先，构建数据飞轮。

- 视觉识别准确率 ≥ 99%，引入 RAG + 自训练 Bad Case。
- 智能审批助理：自动判断异常、推荐审批意见。
- 智能记账：自动生成会计凭证草稿。
- 报销机器人（IM 内对话式提交报销）。
- 自动化测试覆盖率 ≥ 80%，混沌演练机制。
- 通过等保三级。
- **里程碑**：MRR ≥ ¥30 万，月处理发票 ≥ 100 万张。

### Phase 4：生态化（第 9–12 月）

**目标**：开放平台与行业方案。

- 开放平台：插件市场、第三方开发者、白标 OEM。
- 行业方案包：连锁餐饮、IT 服务、咨询业、制造业。
- 多 LLM 接入（私有化模型、合规模型）。
- 国际化：英文版 + 港澳台税制适配。
- 与头部 ERP（用友、金蝶）官方应用市场上架。
- **里程碑**：ARR ≥ ¥1500 万，付费客户 ≥ 500 家。

---

## 9. 风险与依赖

### 9.1 技术风险

| 风险 | 等级 | 应对 |
| --- | --- | --- |
| LLM 上游限流/涨价 | 高 | 多 Provider、本地 Qwen-VL 备选、自训练蒸馏模型 |
| 视觉识别准确率达不到承诺 | 中 | Bad Case 反馈 + 提示词工程 + 人工复核兜底 |
| SQLite → PostgreSQL 迁移数据不一致 | 中 | 双写比对 + 灰度切换 + 回滚预案 |
| 多租户越权漏洞 | 高 | ORM 拦截器 + 自动化越权扫描 + 红蓝对抗 |
| 邮箱 IMAP 频繁触发反垃圾 | 中 | OAuth2 优先 + 拉取频率自适应 |

### 9.2 业务风险

| 风险 | 等级 | 应对 |
| --- | --- | --- |
| 数电发票政策变化 | 高 | 与税务政策跟踪团队建立机制，2 周内适配 |
| 头部 ERP 自建发票模块 | 中 | 通过深度集成绑定客户、做行业纵深 |
| 客户数据合规担忧 | 高 | 数据加密、ISO 27001、私有化部署可选 |
| 价格战 | 中 | 强化 AI 识别准确率与 ROI 案例 |
| 客户使用门槛 | 中 | 30 分钟接入向导、视频教程、专属 CSM |

### 9.3 外部依赖

- **DashScope（通义千问）**：核心 LLM 能力提供方，需签订 SLA，准备多 Provider 备选。
- **税务总局发票查验平台**：真伪查验外部依赖，限频处理。
- **钉钉/企微/飞书**：开放平台审批流入口，需通过应用审核。
- **公有云（阿里云/腾讯云）**：基础设施，签订 99.95% 可用性 SLA。
- **支付/开票**：对接微信、支付宝、网商银行电子发票。

---

## 附录

### 附录 A 术语表

| 术语 | 含义 |
| --- | --- |
| 数电发票 | 全面数字化的电子发票，由全国统一电子发票服务平台开具 |
| 数电票号 | 20 位长度的数电发票编号，唯一标识 |
| 全量发票基础信息表 | 从税务局导出的当期全部发票 xlsx 清单 |
| 核销 | 将员工提交的发票与底账匹配并标记已使用 |
| 多模态大模型 | 能同时处理文本与图像的 LLM，如 Qwen-VL |
| Agent | 具备目标-感知-行动闭环的 AI 自主体 |
| Tool | Agent 可调用的能力函数（API、规则、模型） |
| 租户 | 一个独立企业客户，对应一份隔离数据 |
| RTO | 恢复时间目标 |
| RPO | 恢复点目标 |

### 附录 B 参考文档

1. 《国家税务总局关于全面数字化的电子发票推广应用的公告》。
2. InvoiceWorker 项目 README 及 backend/frontend 源码。
3. DashScope Qwen-VL 官方 API 文档。
4. 阿里云 / 腾讯云 SaaS 多租户最佳实践白皮书。
5. OWASP Top 10 (2023)。
6. ISO/IEC 27001:2022 信息安全管理体系。
7. 中国信通院《AI Agent 技术与应用研究报告》。
8. 钉钉、企业微信、飞书开放平台文档。

---

> 本文档为内部协作底稿，所有数据与目标值需在评审后写入 OKR/Roadmap。任何对外披露需经产品负责人审核。
