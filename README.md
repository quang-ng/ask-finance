# Ask Finance — AI-Powered Financial Q&A Platform

A finance-focused AI agent that enables users to query financial data using natural language, with role-based access control, multi-agent architecture, and comprehensive security features.

## 📋 Table of Contents
- [Project Features](#project-features)
- [System Architecture](#system-architecture)
- [File Structure](#file-structure)
- [Quick Start](#quick-start)
- [Data Layers](#data-layers)
- [Multiple Agent Architecture](#multiple-agent-architecture)
- [Tool System](#tool-system)
- [Retrieval & Knowledge System](#retrieval--knowledge-system)
- [Database Architecture](#database-architecture)
- [Security Architecture](#security-architecture)
- [Evaluation & Monitoring](#evaluation--monitoring)
- [Deployment Architecture](#deployment-architecture)
- [Key Design Decisions](#key-design-decisions)
- [Future Work & Optimization](#future-work--optimization)

---

## Project Features

### Core Capabilities
- **Natural Language Q&A**: Ask financial questions in plain English or multiple languages
- **Role-Based Access Control (RBAC)**: Data visibility restricted by user role, business unit, and region
- **Multi-Agent Architecture**: Specialized agents handle Q&A, analytics, and report generation
- **Inline Visualization**: Charts and tables rendered directly in the chat interface using Mermaid
- **Knowledge Base Integration**: Semantic search over finance glossary and policy documents
- **Conversation Memory**: Multi-turn conversations with persistent state
- **Excel Export**: Generate filtered financial reports on demand
- **Multilingual Support**: Respond in Vietnamese, Thai, Chinese, Japanese, and other languages

### Sample Use Cases
| Query | Agent | Output |
|---|---|---|
| "What was Electronics Opex in Q2?" | Q&A Agent | Exact number + source citation |
| "Show EBIT trend for 2023" | Q&A + Analytics | Numbers + Mermaid line chart |
| "Is our 4.5% Opex variance acceptable?" | Q&A + Knowledge | Policy-aware analysis |
| "Generate a P&L report for Consumer Goods" | Report Agent | Excel file download |
| "What does operating leverage mean?" | Q&A + Knowledge | Definition + context |

---

## System Architecture

### High-Level Request Flow

```mermaid
graph TD
    A["👤 User Input<br/>Role: analyst<br/>BU: Electronics<br/>Region: Asia"] -->|HTTP POST| B["🚀 FastAPI<br/>/chat endpoint<br/>async handler"]
    B -->|invoke| C["📊 LangGraph State Graph"]
    
    C --> D["🎯 Supervisor Agent<br/>Intent Classification<br/>Routing & Synthesis"]
    
    D -->|route| E["❓ Q&A Agent<br/>Data Retrieval<br/>Knowledge Search"]
    D -->|route| F["📈 Analytics Agent<br/>Calculations<br/>Variance Analysis"]
    D -->|route| G["📄 Report Agent<br/>Excel Generation<br/>File Output"]
    
    E -->|call tools| H["🗄️ Data & Knowledge<br/>CSV/SQL + pgvector<br/>RBAC Filtering"]
    F -->|call tools| H
    G -->|call tools| H
    
    H -->|return filtered data| I["✅ Response<br/>Text + Mermaid Charts<br/>Excel Links"]
    
    style A fill:#e1f5ff
    style B fill:#fff3e0
    style C fill:#f3e5f5
    style D fill:#fce4ec
    style E fill:#f1f8e9
    style F fill:#f1f8e9
    style G fill:#f1f8e9
    style H fill:#e0f2f1
    style I fill:#c8e6c9
```

### Key Components

| Component | Purpose | Technology |
|-----------|---------|-----------|
| **Frontend** | Chat UI + role selector + chart rendering | HTML/JS + Mermaid.js |
| **API Server** | HTTP endpoints + request handling | FastAPI + Uvicorn |
| **Agent Graph** | Multi-agent orchestration + routing | LangGraph |
| **LLM** | Natural language understanding + tool routing | Claude API (claude-sonnet-4-6) |
| **Data Loader** | CSV parsing + RBAC filtering | pandas |
| **Knowledge Store** | Semantic search over glossary & policies | PostgreSQL + pgvector |
| **Checkpointer** | Conversation state persistence | PostgreSQL + LangGraph checkpointer |
| **Observability** | Token usage, latency, tool call tracking | Langfuse |


---
## Key Design Decisions

### 1. Tool Use > Vector Embeddings for Financial Data
- **Why**: Financial queries need exact answers, not semantic approximations
- **Tradeoff**: Higher latency for complex multi-step calculations
- **Mitigation**: Cache results, use database indexes

### 2. Supervisor Pattern > Single ReAct Agent
- **Why**: Different tasks (data retrieval, analytics, report generation) benefit from specialized prompts
- **Tradeoff**: More complex state management, routing overhead
- **Mitigation**: Langfuse tracing to monitor routing efficiency

### 3. PostgreSQL + pgvector (not just relational)
- **Why**: Need both structured financial data AND semantic search for glossary
- **Tradeoff**: Operational complexity (two DB paradigms)
- **Mitigation**: Clear separation: financial data in tables, knowledge in vectors

### 4. CSV Prototype > Direct SQL
- **Why**: Fast to build, no DevOps, easy to understand for stakeholders
- **Tradeoff**: Not production-ready, single-user, no persistence
- **Mitigation**: Tool interface abstraction allows easy swap to SQL

---

## File Structure

```
ask-finance/
├── data/
│   ├── pl_report.csv              # P&L data (BU, region, period, metrics)
│   ├── opex_detail.csv            # Opex breakdown (categories)
│   ├── project_roi.csv            # Project ROI tracking
│   └── knowledge/
│       ├── finance_glossary.json  # EBIT, Opex, COGS definitions
│       └── budget_policy.json     # Variance thresholds, approval rules
│
├── app/
│   ├── __init__.py
│   ├── db.py                      # Database pool initialization
│   ├── data_ingestion/
│   │   ├── csv_loader.py          # Load CSV → DataFrame + markdown
│   │   └── csv_analyzer.py        # Statistical summaries
│   ├── finance_agent/
│   │   ├── __init__.py
│   │   ├── configuration.py       # RunnableConfig + Configuration schema
│   │   ├── state.py               # LangGraph State & InputState
│   │   ├── graph.py               # StateGraph + agent nodes
│   │   ├── tools.py               # Tool definitions (retrieve, summarize, export)
│   │   ├── rbac.py                # Role permissions matrix
│   │   ├── prompts.py             # System prompts for each agent
│   │   └── utils.py               # load_chat_model() helper
│   └── knowledge/
│       ├── __init__.py
│       └── vector_store.py        # pgvector initialization + search
│
├── static/
│   └── index.html                 # Frontend UI (role selector + chat + Mermaid)
│
├── outputs/                       # Generated Excel files
├── main.py                        # FastAPI server + routes
├── requirements.txt               # Python dependencies
├── .env                          # Secrets (not in git)
├── .env.example                  # Template for .env
├── docker-compose.yml            # PostgreSQL + app stack
├── Dockerfile                    # Container image
├── PLAN.md                       # Original implementation plan
├── README.md                     # This file
└── tests/
    ├── test_tools.py             # Tool unit tests
    ├── test_agent_flow.py        # Agent integration tests
    ├── test_rbac.py              # RBAC compliance tests
    └── test_retrieval.py         # Knowledge base search tests
```

---

## Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL (local or Docker)
- API Keys: `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`

### Local Setup

```bash
# Clone repo
git clone <repo>
cd ask-finance

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
ANTHROPIC_API_KEY=sk-...
GOOGLE_API_KEY=...
DATABASE_URL=postgresql://postgres:password@localhost:5432/ask_finance
EOF

# Start PostgreSQL (Docker)
docker-compose up -d postgres

# Initialize database
python -c "from app.db import init_pool; asyncio.run(init_pool())"

# Start dev server
python main.py
# Server available at http://localhost:8000
```

### Using the App

1. Open browser: `http://localhost:8000`
2. Select user: Alice (Analyst), Bob (BU GM), Carol (BU GM), David (Group CFO)
3. Type question: "What was Electronics Opex in Q2?"
4. View response with Mermaid chart

### Sample Queries by Role

**Analyst (Electronics, Asia only)**
- "Show me P&L for Electronics"
- "What's the EBIT trend?"

**BU GM (Electronics, all regions)**
- "Compare Opex across regions"
- "Generate a P&L report"

**Group CFO (all data)**
- "Which BU had highest margin?"
- "Create a variance analysis"

---

## Data Layers

### Structured Financial Data (Exact Queries)

**Layer 1: Storage**
- **Prototype**: CSV files in `data/` directory
  - `pl_report.csv`: P&L by business unit, region, quarter
  - `opex_detail.csv`: Opex breakdown by category
  - `project_roi.csv`: Project-level ROI tracking
- **Production**: PostgreSQL tables with indexed columns for fast filtering

**Layer 2: RBAC Filtering**
```python
# RBAC check applied before LLM sees any data
df = df[df["business_unit"].isin(allowed_bus)]      # Role-based BU restriction
df = df[df["region"].isin(allowed_regions)]          # Regional restriction
# Only filtered rows exist in memory — no data leakage risk
```

**Layer 3: Tool Interface**
```python
@tool
def retrieve_financial_data(data_type: str) -> str:
    """
    Retrieve financial data (PNL, OPEX, ROI) as markdown table.
    RBAC enforced inside tool — returns only user-accessible rows.
    """
```

### Schema (Example)

**pl_report.csv**
| period | business_unit | region | revenue | cogs | opex | ebit | net_income |
|--------|--------------|--------|---------|------|------|------|------------|
| 2023-Q1 | Electronics | Asia | 450M | 180M | 150M | 120M | 90M |
| 2023-Q1 | Electronics | Europe | 300M | 120M | 100M | 80M | 60M |

---

## Multiple Agent Architecture

### Agent Pattern: Supervisor + Specialists

The system uses a **Supervisor-Specialist** pattern where one supervisor routes between specialized agents:

```mermaid
graph LR
    A["📝 Input<br/>What was Electronics EBIT?<br/>Generate a report."]
    
    A -->|classify intent| B["🎯 Supervisor Agent<br/>Routes to specialists"]
    
    B -->|1st: data needed| C["❓ QA Agent"]
    C -->|calls| C1["retrieve_financial_data()"]
    C -->|calls| C2["summarize_financial_data()"]
    C -->|calls| C3["search_knowledge_base()"]
    
    C -->|result| D["🔄 Supervisor<br/>Synthesizes result"]
    
    D -->|2nd: report needed| E["📄 Report Agent"]
    E -->|calls| E1["generate_excel_report()"]
    
    E -->|result| F["✅ Output<br/>Text answer<br/>+ Excel file link"]
    
    style A fill:#e3f2fd
    style B fill:#fce4ec
    style C fill:#f1f8e9
    style C1 fill:#c8e6c9
    style C2 fill:#c8e6c9
    style C3 fill:#c8e6c9
    style D fill:#fce4ec
    style E fill:#f1f8e9
    style E1 fill:#c8e6c9
    style F fill:#a5d6a7
```

### Agents & Responsibilities

| Agent | Triggered When | Tools | System Prompt Focus |
|-------|---|---|---|
| **Supervisor** | Every request | None (reasoning only) | Intent classification, routing, answer synthesis |
| **Q&A Agent** | "What is...", "Show me...", "How much..." | `retrieve_financial_data`, `summarize_financial_data`, `search_knowledge_base` | Data retrieval, business context, source citation |
| **Analytics Agent** | "Variance...", "Trend...", "Compare..." | `retrieve_financial_data`, `summarize_financial_data` | Calculation, period-over-period analysis, ratio interpretation |
| **Report Agent** | "Generate...", "Create report...", "Export..." | `retrieve_financial_data`, `generate_excel_report` | File formatting, data aggregation |

### LangGraph Wiring

**Graph Structure**

```mermaid
graph TD
    START["🚀 START"]
    
    START -->|entry| SUP["🎯 Supervisor<br/>Intent Classification<br/>Route Decision"]
    
    SUP -->|qa question| QA["❓ QA Agent<br/>Data Retrieval"]
    SUP -->|analytics query| ANALYTICS["📈 Analytics Agent<br/>Calculations"]
    SUP -->|report needed| REPORT["📄 Report Agent<br/>Excel Generation"]
    SUP -->|end| END["✅ END<br/>Return Answer"]
    
    QA -->|has tools?| QA_ROUTE{"Tool<br/>Calls?"}
    QA_ROUTE -->|yes| QA_TOOLS["🔧 QA Tools<br/>Tool Execution"]
    QA_TOOLS -->|result| QA
    QA_ROUTE -->|no| SUP
    
    ANALYTICS -->|has tools?| ANALYTICS_ROUTE{"Tool<br/>Calls?"}
    ANALYTICS_ROUTE -->|yes| ANALYTICS_TOOLS["🔧 Analytics Tools<br/>Tool Execution"]
    ANALYTICS_TOOLS -->|result| ANALYTICS
    ANALYTICS_ROUTE -->|no| SUP
    
    REPORT -->|has tools?| REPORT_ROUTE{"Tool<br/>Calls?"}
    REPORT_ROUTE -->|yes| REPORT_TOOLS["🔧 Report Tools<br/>Tool Execution"]
    REPORT_TOOLS -->|result| REPORT
    REPORT_ROUTE -->|no| SUP
    
    style START fill:#c8e6c9
    style SUP fill:#fce4ec
    style QA fill:#f1f8e9
    style ANALYTICS fill:#f1f8e9
    style REPORT fill:#f1f8e9
    style QA_ROUTE fill:#fff9c4
    style ANALYTICS_ROUTE fill:#fff9c4
    style REPORT_ROUTE fill:#fff9c4
    style QA_TOOLS fill:#ffccbc
    style ANALYTICS_TOOLS fill:#ffccbc
    style REPORT_TOOLS fill:#ffccbc
    style END fill:#c8e6c9
```

**Python Implementation**

```python
# StateGraph defines the agent graph structure
workflow = StateGraph(State, input=InputState, config_schema=Configuration)

# Entry point → Supervisor
workflow.set_entry_point("supervisor")

# Supervisor routes to specialists or ends
workflow.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {
        "qa_agent": "qa_agent",
        "analytics_agent": "analytics_agent", 
        "report_agent": "report_agent",
        "__end__": END,
    },
)

# Each specialist has a ReAct loop: call LLM → route to tools → execute tools → back to LLM
workflow.add_conditional_edges("qa_agent", route_qa, {"tools": "qa_tools", "supervisor": "supervisor"})
workflow.add_edge("qa_tools", "qa_agent")

# Compile graph with PostgreSQL checkpointer for state persistence
graph = workflow.compile(checkpointer=checkpointer)
```

### State Management

All agents share a common **LangGraph State**:

```python
class State(TypedDict):
    messages: list[BaseMessage]          # Full conversation history
    user_role: str                       # Injected from RunnableConfig
    user_bu: str                         # Business unit
    user_region: str                     # Region
    active_agent: str                    # Current agent running
    retrieved_data: Optional[str]        # Data fetched (reused across agents)
    chart_specs: Optional[list[str]]     # Mermaid code blocks generated
    report_path: Optional[str]           # Path to generated Excel file
```

This allows the **Analytics Agent** to reuse data already fetched by the **Q&A Agent** — avoiding duplicate database queries.

---

## Tool System

### Tool Design Principles

1. **Tool = Function Call**: Each tool is a Python function Claude can invoke
2. **RBAC Inside Tool**: Permission checks happen inside tool logic, not in router
3. **Deterministic Output**: Tools return exact numbers, never approximations
4. **Markdown Format**: Data tables returned as markdown for readability

### Available Tools

#### Q&A Agent Tools

**`retrieve_financial_data(data_type: str) -> str`**
- Returns full financial data table as markdown
- Supports: `PNL`, `OPEX`, `ROI`
- RBAC applied: only user-accessible rows returned
- Use for: "Show me all P&L data", "What is total revenue?"

**`summarize_financial_data(data_type: str) -> str`**
- Returns statistical summary: min, max, mean, total
- Same data types as above
- Use for: "What's the average Opex?", "Highest EBIT across regions?"

**`search_knowledge_base(query: str) -> str`**
- Semantic search over finance glossary + policy documents
- Returns top 3 matching chunks
- Use for: "What is EBIT?", "Operating leverage definition?"

#### Analytics Agent Tools
- `retrieve_financial_data()`, `summarize_financial_data()`
- Specialized for trend, variance, ratio calculations
- System prompt includes formulas: variance = (curr - prior) / prior * 100

#### Report Agent Tools
- `retrieve_financial_data()`, `generate_excel_report()`
- Generates Excel files with proper formatting
- Returns download link: `/outputs/pnl_report_bu_gm_electronics.xlsx`

### Tool Execution Flow

```mermaid
graph TD
    A["Claude Model<br/>Decides Tool Call<br/>retrieve_financial_data<br/>data_type: OPEX"]
    
    A -->|invoke| B["⚙️ ToolNode Executes"]
    
    B --> B1["1️⃣ Extract arguments<br/>data_type = OPEX"]
    B1 --> B2["2️⃣ Get user context<br/>from RunnableConfig"]
    B2 --> B3["3️⃣ Retrieve RBAC<br/>permissions"]
    B3 --> B4["4️⃣ Load data<br/>CSV → DataFrame"]
    B4 --> B5["5️⃣ Apply filters<br/>BU + Region checks"]
    B5 --> B6["6️⃣ Convert to<br/>Markdown"]
    
    B6 -->|return| C["📊 Result Table<br/>period | business_unit | opex<br/>2023-Q1 | Electronics | 150M"]
    
    C -->|context| D["📝 Claude Generates<br/>Natural Language Answer<br/>with Source Citation"]
    
    style A fill:#e1f5ff
    style B fill:#fff3e0
    style B1 fill:#ffe0b2
    style B2 fill:#ffe0b2
    style B3 fill:#ffe0b2
    style B4 fill:#ffe0b2
    style B5 fill:#ffe0b2
    style B6 fill:#ffe0b2
    style C fill:#e0f2f1
    style D fill:#c8e6c9
```

---

## Retrieval & Knowledge System

### Two-Tier Retrieval Strategy

| Data Type | Retrieval Method | Why |
|-----------|-----------------|-----|
| Financial rows (P&L, Opex, ROI) | **Tool Use** (exact pandas/SQL filter) | One correct answer — zero tolerance for approximation |
| Finance glossary & policies | **Vector Search** (semantic similarity) | Open-ended definitions — similarity ranking sufficient |

### Knowledge Base Architecture

**What Gets Embedded**
```json
// data/knowledge/finance_glossary.json
[
  {
    "id": "ebit",
    "text": "EBIT (Earnings Before Interest and Tax) = Gross Profit - Operating Expenses.
             Measures core operating profitability before financing costs."
  },
  {
    "id": "operating_leverage",
    "text": "Operating leverage measures how sensitive EBIT is to revenue changes.
             High operating leverage = higher fixed costs, greater profit swings."
  }
]

// data/knowledge/budget_policy.json
[
  {
    "id": "opex_variance_policy",
    "text": "Opex variance above 5% requires BU GM approval.
             Above 10% requires Group CFO sign-off."
  }
]
```

**Embedding Pipeline**

```mermaid
graph LR
    A["📄 Load JSON<br/>finance_glossary.json<br/>budget_policy.json"]
    
    A -->|extract| B["📋 Text Chunks<br/>One term per doc<br/>Short definitions"]
    
    B -->|embed| C["🧠 Gemini<br/>text-embedding-001<br/>3072 dimensions"]
    
    C -->|store| D["🗄️ PostgreSQL<br/>knowledge_docs<br/>id | content | embedding<br/>vector3072"]
    
    E["🔍 Runtime<br/>User query"] -->|search| F["⚡ Cosine Search<br/>embedding <=><br/>ORDER BY distance"]
    
    F -->|return top-k| D
    
    style A fill:#e3f2fd
    style B fill:#e8f5e9
    style C fill:#fff3e0
    style D fill:#f1f8e9
    style E fill:#fce4ec
    style F fill:#fff9c4
```

**Search Flow**

```mermaid
graph TD
    A["👤 User Query<br/>What is operating leverage?"]
    
    A -->|classify| B["Claude<br/>Calls: search_knowledge_base"]
    
    B -->|invoke| C["🔍 Search Pipeline"]
    
    C --> C1["1️⃣ Embed query<br/>Gemini model<br/>[0.45, -0.23, ..., 0.12]<br/>3072 dimensions"]
    C1 --> C2["2️⃣ Cosine search<br/>PostgreSQL<br/>embedding <=> vector<br/>ORDER BY distance<br/>LIMIT 3"]
    
    C2 -->|return| D["📚 Top 3 Results<br/>1️⃣ Operating leverage<br/>EBIT sensitivity<br/>2️⃣ Fixed vs variable<br/>cost structure<br/>3️⃣ High leverage<br/>examples"]
    
    D -->|context| E["✍️ Claude Synthesizes<br/>Operating leverage measures<br/>EBIT sensitivity to revenue<br/>High leverage = profit swings"]
    
    style A fill:#e3f2fd
    style B fill:#f3e5f5
    style C fill:#fff3e0
    style C1 fill:#ffe0b2
    style C2 fill:#ffe0b2
    style D fill:#e8f5e9
    style E fill:#c8e6c9
```

### Why Tool Use for Financial Data?

Vector embeddings introduce **approximation error** — unsuitable for exact financial numbers:

**Example Failure Case (Vector Search)**
```
Data: Electronics Opex Q2 2023 = $2,300,000
      Electronics Opex Q1 2023 = $2,200,000

Semantic search "Electronics Q2 Opex" might return:
    - Q1 chunk (0.94 similarity) instead of Q2 (0.96 similarity)
    - Result: $2,200,000 instead of $2,300,000
    - Error: $100,000 loss — unacceptable for a CFO

Tool Use (Exact Match)
    - retrieve_financial_data("OPEX") → pandas filter on period + business_unit
    - Result: $2,300,000 — guaranteed correct
```

---

## Database Architecture

### Architecture Overview

```mermaid
graph TD
    subgraph "Financial Data Layer<br/>(Exact Queries)"
        PL["fact_pl<br/>P&L by BU/region/period"]
        OPEX["fact_opex_detail<br/>Opex breakdown"]
        ROI["fact_project_roi<br/>Project ROI"]
    end
    
    subgraph "Knowledge Layer<br/>(Semantic Search)"
        DOCS["knowledge_docs<br/>id | content | embedding<br/>vector3072"]
    end
    
    subgraph "State Layer<br/>(Conversation Memory)"
        CHECKPOINTS["langgraph_checkpoints<br/>thread_id | state_json"]
    end
    
    TOOLS1["retrieve_financial_data<br/>SQL queries + indexing"] -->|exact match| PL
    TOOLS1 --> OPEX
    TOOLS1 --> ROI
    
    TOOLS2["search_knowledge_base<br/>Cosine similarity search"] -->|embedding <>| DOCS
    
    TOOLS3["Conversation State<br/>Per-user isolation"] -->|thread lookup| CHECKPOINTS
    
    style PL fill:#e0f2f1
    style OPEX fill:#e0f2f1
    style ROI fill:#e0f2f1
    style DOCS fill:#f1f8e9
    style CHECKPOINTS fill:#fff3e0
```

### Production Database Schema

**PostgreSQL + pgvector**

```sql
-- Financial data (exact queries)
CREATE TABLE fact_pl (
    id SERIAL PRIMARY KEY,
    period VARCHAR(10),
    business_unit VARCHAR(100),
    region VARCHAR(50),
    revenue DECIMAL(15,2),
    cogs DECIMAL(15,2),
    opex DECIMAL(15,2),
    ebit DECIMAL(15,2),
    net_income DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_pl_bu_region_period ON fact_pl(business_unit, region, period);

CREATE TABLE fact_opex_detail (
    id SERIAL PRIMARY KEY,
    period VARCHAR(10),
    business_unit VARCHAR(100),
    region VARCHAR(50),
    headcount DECIMAL(15,2),
    marketing DECIMAL(15,2),
    it DECIMAL(15,2),
    travel DECIMAL(15,2),
    other DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE fact_project_roi (
    id SERIAL PRIMARY KEY,
    project_name VARCHAR(200),
    business_unit VARCHAR(100),
    year INT,
    investment DECIMAL(15,2),
    roi_pct DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Knowledge base (semantic search)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE knowledge_docs (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(3072),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_knowledge_embedding ON knowledge_docs USING ivfflat (embedding vector_cosine_ops);

-- LangGraph conversation state & checkpoints
CREATE TABLE langgraph_checkpoints (
    id SERIAL PRIMARY KEY,
    thread_id VARCHAR(100),
    timestamp TIMESTAMP,
    channel VARCHAR(100),
    value JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_checkpoints_thread ON langgraph_checkpoints(thread_id, timestamp);
```

### Prototype vs Production

| Aspect | Prototype | Production |
|--------|-----------|-----------|
| **Data Source** | CSV files in `/data` | SAP RFC / OData API |
| **Financial Data** | pandas in-memory | PostgreSQL relational tables |
| **Knowledge Base** | JSON files | PostgreSQL + pgvector |
| **Checkpointing** | In-memory | PostgreSQL LangGraph checkpointer |
| **ETL** | Manual CSV | Airflow / dbt pipeline |
| **Scalability** | Single-user | Multi-user with connection pooling |

### Database Initialization

```python
# app/db.py
DATABASE_URL = "postgresql+asyncpg://user:password@localhost/ask_finance"

async def init_pool():
    """Create async connection pool"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    return create_async_engine(DATABASE_URL, pool_size=10, max_overflow=20)

async def init_vector_store(pool):
    """Load knowledge base into pgvector"""
    # Create vector extension
    # Load JSON documents → embed → insert into knowledge_docs
```

---

## Security Architecture

### Defense Layers

#### 1. Role-Based Access Control (RBAC)

**How it works**

```mermaid
graph TD
    A["📥 Request<br/>role: analyst<br/>user_bu: Electronics"]
    
    A -->|lookup| B["🔐 rbac.py<br/>Permission Lookup"]
    
    B --> C["✅ Permissions Found<br/>allowed_bus: Electronics<br/>allowed_regions: Asia<br/>allowed_reports: PNL, OPEX"]
    
    C -->|apply| D["🔄 data_loader.py<br/>DataFrame Filter"]
    
    D --> E["Filter 1<br/>business_unit == Electronics"]
    E --> F["Filter 2<br/>region == Asia"]
    F --> G["Filtered DataFrame<br/>Only accessible rows"]
    
    G -->|pass to| H["🤖 Claude LLM<br/>Has ONLY filtered data"]
    
    H -->|result| I["✅ Response<br/>CFO-only data<br/>never visible<br/>to analyst"]
    
    style A fill:#e3f2fd
    style B fill:#fce4ec
    style C fill:#c8e6c9
    style D fill:#fff3e0
    style E fill:#ffe0b2
    style F fill:#ffe0b2
    style G fill:#e0f2f1
    style H fill:#f3e5f5
    style I fill:#c8e6c9
```

**Role Matrix**

| Role | Accessible BUs | Accessible Regions | Data Types | Can Export |
|------|---|---|---|---|
| **Analyst** | Own BU only | Own region | PNL, OPEX | ❌ No |
| **BU GM** | Own BU (all regions) | All | PNL, OPEX, ROI | ✅ Yes |
| **Group CFO** | All | All | All | ✅ Yes |

#### 2. Prompt Injection Prevention

**Hardened System Prompt**
```python
SYSTEM_PROMPT = """You are a Finance Business Partner AI.
You have access to the following financial data types: PNL, OPEX, ROI.

CRITICAL RULES:
1. Only call tools with valid data_type values: PNL, OPEX, ROI
2. Always cite data source: business_unit, region, period
3. Never invent or hallucinate numbers — only use tool results
4. If user asks for unauthorized data, explain why you can't access it
5. For multilingual: respond in user's language, keep financial terms in English
"""
```

**Input Validation**
```python
@tool
def retrieve_financial_data(data_type: str, config: RunnableConfig) -> str:
    # Validate data_type
    if data_type.upper() not in ["PNL", "OPEX", "ROI"]:
        return f"Invalid data_type: {data_type}"
    
    # Check RBAC
    if not is_data_type_allowed(config.role, data_type):
        return f"Access denied: {config.role} cannot access {data_type}"
    
    # Safe filtering
    df = filter_dataframe(df, allowed_bus, allowed_regions)
    return dataframe_to_markdown(df)
```

#### 3. Credential Management

**Environment Variables Only**
```bash
# .env (never committed)
GOOGLE_API_KEY=xxx
ANTHROPIC_API_KEY=xxx
DATABASE_URL=postgresql://...
```

**No hardcoded credentials in code** — all fetched from `os.environ`

#### 4. Conversation Privacy

**Per-User Thread Isolation**
```python
config = {
    "configurable": {
        "thread_id": user_session_id,      # Each user has unique thread
        "role": user_role,
        "user_bu": user_bu,
    }
}
# Checkpointer stores state per thread_id
# Users cannot access other users' conversations
```

#### 5. Data in Transit

- **TLS/HTTPS**: All API calls encrypted
- **Secure Headers**: No caching of sensitive data
- **Rate Limiting**: (Optional) Add FastAPI rate limiter for API endpoints

#### 6. Audit Logging

```python
# Every query logged
logger.info(f"User: {user}, Role: {role}, Tools: {tools_used}, DataSources: {data_sources}")

# Langfuse traces
trace = {
    "thread_id": thread_id,
    "user": user,
    "role": role,
    "tools_called": tools_used,
    "token_usage": {"input": 1500, "output": 300},
    "latency_ms": 2500,
    "timestamp": datetime.now().isoformat()
}
```

---

## Evaluation & Monitoring

### Evaluation Metrics

| Dimension | Method | Target | How to Test |
|-----------|--------|--------|-----------|
| **Accuracy** | Compare LLM answer to direct pandas calculation | 100% match | Unit tests with known P&L data |
| **RBAC Compliance** | Verify each role sees only permitted data | 0 unauthorized rows | Role-based test suite |
| **Explainability** | Check every answer cites source | 100% citations | Regex check for "period", "BU", "region" |
| **Response Latency** | End-to-end time from POST to response | < 5 seconds | Langfuse traces |
| **Tool Accuracy** | Tool returns match expected pandas output | 100% match | CSV-based golden tests |

### Monitoring Setup

**Langfuse Integration**
```python
# Every LangGraph run traced
from langfuse.callback import langfuse_context

result = await graph.ainvoke(
    {"messages": [...]},
    config=config,
)
# Auto-traces:
# - Token usage (input, output, cache hits)
# - Tool calls (name, latency, args, results)
# - Agent routing (which agent ran)
# - Total latency
```

**Key Metrics to Monitor**
```
POST /chat latency:
    - Median: target < 3 seconds
    - P95: target < 5 seconds
    - P99: target < 10 seconds

Token usage:
    - Avg tokens per query
    - Cache hit rate
    - Cost per query

Tool call success:
    - Success rate by tool
    - Failure reasons
    - RBAC rejections

Agent routing:
    - % queries routed to each agent
    - Agent success rates
    - Tool call counts by agent
```

### Testing Strategy

**Unit Tests**
```python
# test_tools.py
def test_retrieve_financial_data_respects_rbac():
    config = Configuration(role="analyst", user_bu="Electronics", user_region="Asia")
    result = retrieve_financial_data("PNL", config)
    # Assert result contains only Electronics + Asia rows
    assert "Consumer Goods" not in result  # unauthorized BU

def test_retrieve_financial_data_invalid_type():
    config = Configuration(role="analyst", user_bu="Electronics", user_region="Asia")
    result = retrieve_financial_data("INVALID", config)
    assert "Unknown data type" in result
```

**Integration Tests**
```python
# test_agent_flow.py
@pytest.mark.asyncio
async def test_qa_agent_calculates_variance():
    # Mock question: "What's the Opex variance Q2 vs Q1?"
    result = await graph.ainvoke(
        {"messages": [HumanMessage("What's the Opex variance Q2 vs Q1?")]},
        config={"configurable": {...}}
    )
    # Extract answer from result
    answer = extract_answer(result)
    # Verify: (Q2_opex - Q1_opex) / Q1_opex matches calculation
    assert "4.5%" in answer or similar_number(answer, 4.5)
```

---

## Deployment Architecture

### Architecture Overview

```mermaid
graph TB
    subgraph "Development"
        DEV["💻 Local<br/>Python 3.12<br/>Uvicorn dev server<br/>SQLite/PostgreSQL"]
    end
    
    subgraph "Containerization"
        DOCKER["🐳 Docker Image<br/>Python 3.12 slim<br/>All dependencies<br/>Health checks"]
        COMPOSE["📦 docker-compose<br/>App + PostgreSQL<br/>One command startup"]
    end
    
    subgraph "Production Deployment"
        LB["⚖️ Load Balancer<br/>Traffic distribution"]
        APP1["🚀 App Replica 1<br/>8000 port"]
        APP2["🚀 App Replica 2<br/>8000 port"]
        APP3["🚀 App Replica 3<br/>8000 port"]
        DB["🗄️ PostgreSQL RDS<br/>Managed service<br/>Daily backups"]
    end
    
    DEV -->|build| DOCKER
    DOCKER -->|compose| COMPOSE
    COMPOSE -->|push to registry| LB
    
    LB -->|route| APP1
    LB -->|route| APP2
    LB -->|route| APP3
    
    APP1 -->|query| DB
    APP2 -->|query| DB
    APP3 -->|query| DB
    
    style DEV fill:#e3f2fd
    style DOCKER fill:#fff3e0
    style COMPOSE fill:#fff3e0
    style LB fill:#fce4ec
    style APP1 fill:#c8e6c9
    style APP2 fill:#c8e6c9
    style APP3 fill:#c8e6c9
    style DB fill:#e0f2f1
```

### Containerization

**Dockerfile**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose (Development)

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: ask_finance
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  app:
    build: .
    environment:
      DATABASE_URL: postgresql://postgres:password@postgres:5432/ask_finance
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      GOOGLE_API_KEY: ${GOOGLE_API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      - postgres
    volumes:
      - .:/app

volumes:
  postgres_data:
```

### Production Deployment

**Kubernetes Deployment (Optional)**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ask-finance
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ask-finance
  template:
    metadata:
      labels:
        app: ask-finance
    spec:
      containers:
      - name: ask-finance
        image: ask-finance:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: ask-finance-secrets
              key: database-url
        resources:
          limits:
            cpu: "2"
            memory: "4Gi"
          requests:
            cpu: "1"
            memory: "2Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
```

### Infrastructure Requirements

| Component | Environment | Spec |
|-----------|---|---|
| **App Server** | Prototype | Single machine, Python 3.12, 2GB RAM |
| **App Server** | Production | Load balancer + 3+ replicas, 4GB RAM each |
| **Database** | Prototype | Local PostgreSQL |
| **Database** | Production | Managed PostgreSQL (AWS RDS / Azure Database), daily backups |
| **Storage** | Both | Local `/outputs` for Excel files (or S3 for production) |
| **LLM** | Both | Claude API (usage-based billing) |

---

## Future Work & Optimization

### Roadmap Timeline

```mermaid
timeline
    title Ask Finance — Product Roadmap
    
    section Near-Term (1-3 months)
        Production SAP Integration : Active
        Vector Search (pgvector) : Active
        Multi-Step Planning Agent : In Planning
        Streaming Responses : In Planning
    
    section Medium-Term (3-6 months)
        PowerPoint Generation : Planned
        Real-Time Data Connectors : Planned
        Customizable Dashboard : Planned
    
    section Long-Term (6+ months)
        Fine-Tuning Domain Model : Research
        Multi-User Collaboration : Research
        Advanced Analytics Agents : Research
```

### Near-Term (1-3 months)

#### 1. Production SAP Integration
```
Replace CSV files with real SAP connections:
- RFC function calls to SAP HANA
- OData APIs for master data (GL accounts, cost centers)
- OAuth2 SSO integration with corporate directory
```

#### 2. Advanced Vector Search
```
Migrate ChromaDB → PostgreSQL + pgvector:
- Store policy documents, CFO commentary, analyst notes
- Auto-embed on document upload
- Reranking: semantic search + keyword matching
```

#### 3. Multi-Step Planning Agent
```
Add Planning Agent for complex queries:
- "What's driving Electronics' margin compression? What if we cut headcount 10%?"
- Breaks into steps: fetch data → analyze → simulate → report
- Uses Claude's extended thinking for complex calculations
```

#### 4. Streaming Responses
```
Implement token-by-token streaming:
- Frontend receives chunks in real-time
- Better UX: "thinking...", "calling retrieve_financial_data...", text streaming
- Current: /chat/stream endpoint (ready to activate)
```

### Medium-Term (3-6 months)

#### 5. PowerPoint Report Generation
```python
from pptx import Presentation

def generate_pptx(data_type, charts, summary):
    prs = Presentation()
    # Slide 1: Executive summary
    # Slide 2: Key metrics (KPIs)
    # Slide 3: Trends (with Mermaid → PNG)
    # Slide 4: Variance analysis
    prs.save(f"/outputs/report_{timestamp}.pptx")
```

#### 6. Real-Time Data Connectors
```
Additional data sources:
- Live currency / FX rates (for international variance analysis)
- Headcount data from HRIS (payroll forecasting)
- Project management systems (actual vs budget spend)
```

#### 7. Customizable Dashboard
```
Replace static /dashboard with:
- Role-based KPI cards (user can customize which metrics)
- Saved queries / favorites
- Custom report templates
- Alert thresholds (e.g., "notify me if variance > 10%")
```

### Long-Term (6+ months)

#### 8. Fine-Tuning Domain Model
```
Fine-tune Claude on:
- Historical Q&A pairs + ground truth answers
- Custom finance terminology
- Company-specific accounting policies
- Result: lower hallucination, faster routing
```

#### 9. Multi-User Collaboration
```
Add to state:
- Comments on data points
- Annotation layer
- Collaborative editing of reports
- Audit trail of changes
```

#### 10. Advanced Analytics
```
New agents for:
- Variance driver decomposition (Opex = Δheadcount + Δrates + Δspend)
- Forecasting (trend-based, regression)
- Anomaly detection (flag unusual variances)
- Scenario modeling ("What if revenue drops 5%?")
```

### Performance Optimization

#### Database Optimization
```sql
-- Add indexing strategy
CREATE INDEX idx_pl_bu ON fact_pl(business_unit);
CREATE INDEX idx_pl_region ON fact_pl(region);
CREATE INDEX idx_pl_period ON fact_pl(period);

-- Materialized views for common queries
CREATE MATERIALIZED VIEW v_pl_summary AS
SELECT period, business_unit, SUM(revenue) as total_revenue
FROM fact_pl
GROUP BY period, business_unit;
```

#### Caching Strategy
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def load_pl_report(user_bu: str):
    # Cache filtered DataFrames for frequent users
    # TTL: 1 hour (refresh on schedule)
```

#### Prompt Optimization
```
Current: ~800 token system prompt
Optimized: 
- Compress examples (remove unused cases)
- Use instruction-following format (reduces reasoning steps)
- Add few-shot examples (3-5, not 10)
Target: < 500 tokens (10% reduction in every query cost)
```

### Cost Optimization

```mermaid
graph LR
    subgraph "Current State"
        C1["2,500 tokens/query"]
        C2["Full re-embed weekly"]
        C3["Single RDS instance"]
        C4["3 app replicas 24/7"]
    end
    
    subgraph "Optimized State"
        O1["1,500 tokens/query<br/>-40%"]
        O2["Incremental updates<br/>-70%"]
        O3["Read replicas + cache<br/>-20%"]
        O4["2 + autoscaling<br/>-25%"]
    end
    
    C1 -->|compress prompt| O1
    C2 -->|smart invalidation| O2
    C3 -->|scale horizontally| O3
    C4 -->|auto scale down| O4
    
    style C1 fill:#ffcdd2
    style C2 fill:#ffcdd2
    style C3 fill:#ffcdd2
    style C4 fill:#ffcdd2
    style O1 fill:#c8e6c9
    style O2 fill:#c8e6c9
    style O3 fill:#c8e6c9
    style O4 fill:#c8e6c9
```

### Security Roadmap

- [ ] Rate limiting by user/role
- [ ] IP allowlist for corporate network
- [ ] End-to-end encryption for data at rest
- [ ] Compliance auditing: SOC 2, GDPR, HIPAA
- [ ] Advanced threat detection (anomaly scoring on queries)
- [ ] Regular penetration testing

---


## Support & Contribution

### Getting Help
- Check [PLAN.md](./PLAN.md) for detailed architecture decisions
- Review [app/finance_agent/prompts.py](./app/finance_agent/prompts.py) for agent system prompts
- Browse test files for example queries and expected outputs

### Contributing
1. Fork the repository
2. Create a feature branch
3. Add tests for new tools or agents
4. Ensure all tests pass
5. Submit a pull request

---

## License

MIT License (or your preferred license)

---

**Last Updated**: 2026-04-25  
**Author**: Quang Nguyen (quangnv1400@gmail.com)  
**Status**: Prototype (feature-complete, ready for production planning)
