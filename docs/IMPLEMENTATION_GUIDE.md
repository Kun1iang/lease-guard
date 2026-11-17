# 租约守护代码实现流程

本文按实际开发顺序解释每一步写了哪些代码、实现什么功能、用了什么技术。目标不是让你记住所有代码，而是能沿着数据从“上传合同”走到“风险报告”逐段读懂。

## 0. 先理解最终调用链

```text
React 页面
  → api.ts
  → FastAPI main.py
  → services.py
  → parsers.py
  → clauses.py
  → graph.py
  → rules.py + knowledge.py
  → SQLAlchemy 模型
  → 报告接口
  → ReviewWorkspace.tsx
```

最重要的学习顺序：

1. 先看 `frontend/src/types.ts`，理解前后端共享的数据形状。
2. 再看 `backend/app/models.py`，理解数据库存了什么。
3. 看 `backend/app/main.py`，理解 API 怎么接收请求。
4. 看 `backend/app/services.py`，理解完整业务流程。
5. 看 `backend/app/graph.py`，理解 Agent 如何把规则和证据编排起来。
6. 看 `frontend/src/components/ReviewWorkspace.tsx`，理解结果如何展示。

---

## 1. 创建双端工程

### 生成后端

使用的命令：

```powershell
uv init backend --bare --name lease-guard-backend --python 3.12 --vcs none
```

生成文件：

- `backend/pyproject.toml`
- `backend/.python-version`

技术说明：

- `uv` 管理 Python 虚拟环境和锁文件。
- Python 3.12 用于降低 OCR、SQLite、PDF 和 LangGraph 原生依赖的兼容风险。

### 生成前端

使用的命令：

```powershell
npm create vite@latest frontend -- --template react-ts
```

技术说明：

- React 管理交互状态。
- TypeScript 在编译期检查接口字段。
- Vite 提供开发服务器和生产构建。

对应文件：

- `frontend/package.json`
- `frontend/vite.config.ts`
- `frontend/index.html`

---

## 2. 配置后端

文件：`backend/app/config.py`

主要类：

- `Settings`
- `get_settings()`

实现了：

- 数据库地址。
- JWT 密钥和过期时间。
- 上传文件大小、最大页数。
- 试用账号和额度。
- 外部模型地址、模型名和开关。
- 存储目录。

技术：

- `pydantic-settings` 自动读取 `.env`。
- 使用 `Path` 计算公式中的存储目录。

为什么先写配置：

- API、JWT、数据库和模型服务都需要统一配置。
- 先集中配置，后面不会在多个文件里硬编码密钥和路径。

---

## 3. 建立数据库

文件：`backend/app/database.py`

主要对象：

- `Base`
- `engine`
- `SessionLocal`
- `get_db()`
- `create_tables()`

实现：

- 默认连接 SQLite。
- FastAPI 每个请求通过 `get_db()` 获取 Session。
- 请求结束后自动关闭 Session。

技术：

- SQLAlchemy 2.x ORM。
- `sessionmaker` 管理数据库会话。

### 为什么先用 SQLite

- 单机开发无需额外服务。
- 数据模型稳定后再换 PostgreSQL。
- 当前代码使用 SQLAlchemy，不把业务绑死在 SQLite 上。

文件：`backend/app/models.py`

主要模型：

| 模型 | 作用 |
|---|---|
| `User` | 账号、角色和额度 |
| `Document` | 合同文件元数据 |
| `DocumentPage` | 每页文本和 OCR 置信度 |
| `Clause` | 条款切分结果 |
| `ReviewJob` | 审阅任务状态 |
| `RiskFinding` | 单条风险 |
| `FindingEvidence` | 风险与合同原文的关联 |
| `QAAudit` | 问答范围与引用数量审计 |

学习重点：

- `RiskFinding` 和 `FindingEvidence` 必须分开。
- 风险是“结论”，Evidence 是“结论为什么成立”。
- 这种拆分让前端可以点击风险并跳转到原文。

---

## 4. 实现账号与 JWT

文件：`backend/app/security.py`

主要函数：

- `hash_password`
- `verify_password`
- `create_access_token`
- `decode_access_token`

技术：

- `pwdlib` + Argon2：密码只保存哈希，不保存明文。
- `PyJWT`：生成和校验登录令牌。

文件：`backend/app/dependencies.py`

主要函数：

- `get_current_user`

流程：

```text
Authorization: Bearer <token>
  → HTTPBearer 读取 token
  → decode_access_token 获取 user_id
  → 查询 User
  → 注入到 API 函数
```

文件：`backend/app/seed.py`

作用：

- 首次启动创建 `trial` 试用账号。
- 密码来自配置。

文件：`backend/app/main.py`

账号接口：

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/trial`
- `GET /api/auth/me`

---

## 5. 定义 API 数据结构

文件：`backend/app/schemas.py`

主要 Schema：

- `RegisterRequest`
- `TokenResponse`
- `DocumentOut`
- `ReviewOut`
- `FindingOut`
- `EvidenceOut`
- `QaRequest`
- `QaResponse`

技术：

- Pydantic 自动校验请求。
- `model_config = {"from_attributes": True}` 允许直接从 ORM 模型转换。

为什么需要 Schema：

- 数据库模型不等于 API 模型。
- API 只返回前端需要的字段。
- 错误字段会在请求进入业务前被拦截。

---

## 6. 实现文档解析

文件：`backend/app/parsers.py`

主要类：

- `ParsedPage`
- `ParsedDocument`
- `RapidOcrAdapter`

主要函数：

- `parse_upload`
- `parse_pdf`
- `parse_docx`
- `parse_image`
- `parse_text`

技术：

| 文件类型 | 技术 |
|---|---|
| PDF 文本 | PyMuPDF |
| PDF 扫描页 | PyMuPDF 渲染 + RapidOCR |
| DOCX | python-docx |
| JPG/PNG/WEBP | RapidOCR |
| TXT | UTF-8 解码 |

重要逻辑：

- PDF 每页先尝试文本层。
- 少于 30 个有效字符时自动走 OCR。
- 每页保留页码和 OCR 置信度。
- OCR 组件按需加载，未安装时不会影响其他文件类型启动。

学习重点：

```python
document = pymupdf.open(stream=data, filetype="pdf")
```

这里从内存读取 PDF，而不是先依赖磁盘路径。

---

## 7. 切分合同条款

文件：`backend/app/clauses.py`

主要函数：

- `classify_clause`
- `segment_clauses`

实现：

1. 识别“第一条”“一、”“1.”等编号。
2. 将每一条正文切成 `ClauseRecord`。
3. 根据押金、租金、费用、维修、解约等关键词分类。

为什么规则前要先切分：

- 规则需要知道风险在哪个条款。
- 用户需要看到条款标题。
- 后续可对不同类型的条款使用不同规则。

---

## 8. 编写确定性风险规则

文件：`backend/app/rules.py`

主要结构：

- `Rule`
- `RuleMatch`
- `RULES`
- `evaluate_rules`

已实现 16 类规则，例如：

- 押金退还期限不明确。
- 押金扣除条件过宽。
- 维修责任全部转移。
- 提前解约责任不明确。
- 房东入户程序不明确。
- 自动续租。
- 缺少交接清单。
- 合同存在空白字段。
- 单方涨租空间过宽。

每条规则做三件事：

```text
识别合同信号
  → 抽取原文句子
  → 给出风险说明、影响、建议和法律知识 ID
```

学习重点：

- 为什么不让 LLM 直接判断所有风险？
- 因为规则可以重复、可测试、成本低，也不会每次输出不同的风险清单。
- LLM 只负责在规则结果基础上解释。

---

## 9. 建立租房知识库

文件：

- `backend/app/knowledge.py`
- `backend/app/data/legal_kb.json`

主要对象：

- `KnowledgeEntry`
- `is_rental_scope`
- `is_rental_contract`
- `retrieve`
- `citation_for_id`
- `deterministic_answer`

实现：

1. 从 JSON 加载租房知识。
2. 使用关键词和中文二元组打分。
3. 返回最相关的 3 条知识。
4. 每条回答携带来源、条款、版本和链接。

范围守卫：

```text
包含押金、租金、维修、退租等词
  → 允许回答

包含劳动、婚姻、刑事等词
  → OUT_OF_SCOPE
```

为什么这里不用向量库：

- 当前知识条目少。
- 确定性关键词排序更容易理解和测试。
- 数据规模扩大后再切换 BM25 + pgvector。

---

## 10. 接入外部模型

文件：`backend/app/llm.py`

主要函数：

- `redact_pii`
- `LLMService.answer_rental_question`
- `LLMService.summarize_review`

技术：

- OpenAI Chat Completions 兼容接口。
- `httpx.AsyncClient` 发起异步请求。
- 未配置密钥或请求失败时自动退回确定性结果。

隐私：

- 身份证号、手机号、银行卡号和常见地址在发送前替换。
- 模型只接收必要的知识片段和问题。

学习重点：

外部模型不是系统唯一路径：

```text
有模型 → 用模型润色回答
无模型/模型失败 → 使用知识库拼接回答
```

这是 fail-soft 设计。

---

## 11. LangGraph 证据链

文件：`backend/app/graph.py`

State：

- `pages`
- `matches`
- `findings`

节点：

| 节点 | 功能 |
|---|---|
| `run_rules` | 执行所有规则 |
| `attach_legal_basis` | 为风险附加知识引用 |
| `verify_evidence` | 核验原文和页码 |

图：

```text
START
  → run_rules
  → attach_legal_basis
  → verify_evidence
  → END
```

证据校验：

```text
规则给出的 quote
  → 去除空白
  → 检查是否在对应页文本中
  → 存在则 verified=true
```

缺失条款：

- `kind="absence"`。
- 不伪造原文。
- 状态标记为需要人工核实。

---

## 12. 编排一次完整审阅

文件：`backend/app/services.py`

主要函数：

- `create_text_document`
- `create_uploaded_document`
- `create_review`
- `create_sample_review`
- `process_review`
- `answer_rental_question`
- `delete_document`

`process_review` 是最重要的学习函数：

```text
读取任务
  → 更新为 running
  → 读取所有合同页
  → 切分条款
  → 执行 LangGraph
  → 保存风险
  → 保存证据
  → 生成摘要
  → 更新为 succeeded
```

失败时会：

- 记录 `status=failed`。
- 保存错误类型。
- 关闭数据库 Session。

后台任务：

- `BackgroundTasks.add_task(process_review, job.id)`。
- 首版使用进程内后台任务，避免引入 Redis 和独立 Worker。

---

## 13. 实现 FastAPI 路由

文件：`backend/app/main.py`

主要接口：

| 方法 | 路径 | 功能 |
|---|---|---|
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/trial` | 试用登录 |
| POST | `/api/documents/upload` | 上传合同文件 |
| POST | `/api/documents/text` | 提交合同文本 |
| POST | `/api/reviews` | 创建审阅 |
| POST | `/api/reviews/sample` | 样例审阅 |
| GET | `/api/reviews` | 历史任务 |
| GET | `/api/reviews/{id}/report` | 网页报告数据 |
| POST | `/api/rental-qa` | 租房知识问答 |
| DELETE | `/api/documents/{id}` | 删除合同 |

启动流程：

```text
lifespan
  → 创建存储目录
  → 创建数据库表
  → 创建试用账号
```

生产构建：

- 如果存在 `frontend/dist`，FastAPI 会直接提供前端页面。
- 开发时使用 Vite 代理 `/api` 到 8000 端口。

---

## 14. 定义前端类型与请求层

文件：

- `frontend/src/types.ts`
- `frontend/src/api.ts`

`types.ts`：

- 定义 `User`、`Review`、`Finding`、`Evidence`、`Report` 等接口。

`api.ts`：

- `request()` 统一添加 JWT。
- 统一处理非 2xx 错误。
- `api.trial/login/upload/startReview/getReport/ask` 对应后端接口。
- `pollReview()` 定时读取审阅状态，直到完成或失败。

学习重点：

组件不直接写 `fetch`，而是统一经过 `api.ts`。这样改接口地址或鉴权方式时只改一个文件。

---

## 15. 登录与公开页

文件：

- `frontend/src/App.tsx`
- `frontend/src/components/Landing.tsx`
- `frontend/src/components/AuthForm.tsx`

`App.tsx`：

```text
有 token
  → /auth/me
  → 有效则进入 Workspace
  → 无效则清理 token
无 token
  → Landing
```

`Landing`：

- 说明产品和边界。
- 显示真实审阅 UI 示意。
- 提供“启动试用”。
- 登录/注册表单。

`AuthForm`：

- 登录和注册切换。
- 表单校验。
- 错误展示。
- 请求状态展示。

---

## 16. 工作台与上传

文件：

- `frontend/src/components/Workspace.tsx`
- `frontend/src/components/ReviewWorkspace.tsx`

`Workspace` 管理三个主要视图：

```text
dashboard
new
review
knowledge
```

上传流程：

```text
选择文件或粘贴文本
  → api.upload / api.submitText
  → api.startReview
  → pollReview
  → api.getReport
  → ReviewWorkspace
```

为什么前端要轮询：

- 文档解析和规则运行不是瞬间完成。
- 后端返回 `job_id` 后，前端每 700ms 查询一次状态。
- UI 始终显示当前阶段和进度。

---

## 17. 审阅工作台

文件：`frontend/src/components/ReviewWorkspace.tsx`

主要状态：

- `tab`：风险、问答、报告。
- `filter`：全部、高风险、中风险、待核实。
- `selectedId`：当前风险。
- `pageNo`：当前合同页。

左侧：

- 页码列表。
- 合同页文本。
- 选中风险后高亮对应 quote。

右侧：

- 风险摘要。
- 风险卡片。
- 风险影响。
- 协商建议。
- 法律依据。
- 用户确认和误报标记。

报告标签：

- 风险总数。
- 高风险数。
- 待核实数。
- 逐项风险和建议。
- 免责声明。

---

## 18. 租房问答

文件：`frontend/src/components/KnowledgePanel.tsx`

流程：

```text
输入问题
  → /api/rental-qa
  → 显示回答
  → 显示来源卡片
  → 显示限制说明
```

如果接口返回 `in_scope=false`：

- 使用不同样式显示拒绝原因。

这意味着知识问答与合同审阅共用账号和额度，但问题范围被后端严格控制。

---

## 19. 测试策略

后端测试：

- `tests/test_core.py`
- `tests/test_api.py`

覆盖：

- 样例合同条款切分。
- 风险规则命中。
- 原文证据校验。
- 非租房问题拒绝。
- PII 脱敏。
- 试用账号登录。
- 样例审阅报告。
- 租房问答引用。

前端检查：

- `npm run lint`
- `npm run build`

设计检查：

- 1440、1024、820、768、390 布局检查。
- 320px 横向溢出检查。
- 文案检查。
- 性能检查。

---

## 20. 目前建议你怎么学习

### 第一轮：跟着请求走

1. 在 `frontend/src/api.ts` 找 `sampleReview`。
2. 在 `backend/app/main.py` 找 `/api/reviews/sample`。
3. 在 `backend/app/services.py` 找 `create_sample_review` 和 `process_review`。
4. 在 `backend/app/graph.py` 看规则和证据节点。
5. 在 `backend/app/rules.py` 改一条规则的说明。
6. 运行后端测试，观察哪些测试失败。

### 第二轮：跟着数据走

1. `Document` 保存什么？
2. `DocumentPage` 为什么需要页码？
3. `RiskFinding` 为什么不能直接保存一大段模型文本？
4. `FindingEvidence` 为什么需要 `verified`？
5. 前端怎样根据 `page_no` 跳转到原文？

### 第三轮：跟着失败走

1. 把 PDF 改成空文件，观察解析失败。
2. 关闭模型配置，观察问答退回确定性回答。
3. 删除 OCR extra，观察 OCR 页面提示。
4. 输入“劳动合同怎么赔”，观察范围守卫拒绝。
5. 把某个风险 quote 改错，观察证据核验变成待核实。

---

## 21. 下一阶段可以继续学习的方向

1. 用真实 PDF 测试页码和条款切分。
2. 安装 OCR extra，测试照片和扫描 PDF。
3. 配置外部模型，测试租房问答和摘要。
4. 把 SQLite 迁移到 PostgreSQL。
5. 用 Redis + ARQ 替换进程内后台任务。
6. 建立 30 份合同标注集，计算召回率和引用正确率。
7. 增加 PDF 导出。
8. 加入更严格的日志、追踪和删除任务。
