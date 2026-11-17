# 租约守护

中国大陆住宅租赁合同风险审阅工作台。用户可以通过照片、PDF、DOCX 或粘贴文本提交合同，系统输出带原文、页码、规则依据和人工确认状态的风险报告。

## 已实现

- 用户注册、登录、JWT 鉴权。
- 预置试用账号和脱敏样例合同。
- PDF 文本解析、DOCX 解析、纯文本输入。
- 扫描 PDF / 图片 OCR 适配器（安装 `ocr` extra 后启用）。
- 16 条住宅租赁确定性风险规则。
- 条款切分和页码证据。
- LangGraph 规则、法律依据和原文证据校验流程。
- 只处理中国大陆住宅租赁问题的范围守卫。
- 带引用的租房知识问答。
- 外部 OpenAI 兼容模型适配器；未配置时使用确定性回答。
- 风险卡片、原文定位、用户确认/误报标记。
- 网页报告。
- 删除原始合同及其派生数据。

## 当前不包含

- PDF 导出和专用打印模板。
- 邮件验证、找回密码、第三方登录。
- PostgreSQL 迁移脚本。
- 真实律师审定的完整法律知识库。
- 真实 OCR 质量和真实模型质量评测。

## 本机启动

### 1. 后端

```powershell
cd backend
uv sync --python 3.12
Copy-Item .env.example .env
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

如需要图片和扫描件 OCR：

```powershell
uv sync --extra ocr
```

### 2. 前端

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

打开 `http://127.0.0.1:5173/`。

### 3. 试用账号

- 用户名：`trial`
- 密码：`LeaseGuard2026!`
- 页面上的“启动试用”会直接登录试用账号。

样例合同不会消耗正式审阅额度。

## 测试与检查

```powershell
cd backend
uv run pytest -q
uv run ruff check .

cd ..\frontend
npm run lint
npm run build
```

## 外部模型

修改 `backend/.env`：

```env
ENABLE_LLM=true
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=你的密钥
LLM_MODEL=deepseek-chat
```

外部模型只负责租房问答和摘要润色。风险发现、证据绑定和风险等级仍由确定性规则与代码校验控制。

## 目录

```text
lease-guard/
├── backend/
│   ├── app/
│   │   ├── parsers.py
│   │   ├── clauses.py
│   │   ├── rules.py
│   │   ├── knowledge.py
│   │   ├── graph.py
│   │   ├── services.py
│   │   └── main.py
│   └── tests/
├── frontend/
│   ├── src/components/
│   ├── src/api.ts
│   └── src/types.ts
├── docs/
│   └── IMPLEMENTATION_GUIDE.md
└── docker-compose.yml
```

## 重要边界

本产品用于合同风险预筛，不构成正式法律意见。风险结论必须由用户结合合同原文、付款凭证、房屋状况和可能的专业意见自行确认。
