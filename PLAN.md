# Ask Finance — Implementation Plan

## Overview
A Finance-focused AI Agent that lets users query financial data in natural language,
with role-based access control and a simple chat UI.

---

## How the System Works

### 1. Data Ingestion — How the system reads internal data

```
SAP / HFM / Data Lake
        │
        ▼
  CSV / Excel Export  ──►  data_loader.py  ──►  pandas DataFrame (in-memory)
                                │
                                ▼
                     RBAC filter applied
                     (rows stripped by BU / region / role)
                                │
                                ▼
                     Filtered data ready for query
```

- In the **prototype**, data is loaded from CSV files that simulate SAP/HFM exports.
- Each file has columns like `period`, `business_unit`, `region`, `revenue`, `opex`, `ebit`, etc.
- `data_loader.py` reads the CSV into a pandas DataFrame, then immediately applies an **RBAC filter** — rows outside the user's permitted BU/region are dropped before the LLM ever sees them.
- In **production**, this layer would be replaced by secure API calls to SAP RFC, SAP OData, or HFM REST endpoints — same interface, different source.

---

### Should we store financial data in a relational database?

**Yes — in production. No — for the prototype.**

| Environment | Storage | Why |
|---|---|---|
| **Prototype** | CSV → pandas in-memory | Simple, no infra needed, fast to build |
| **Production** | PostgreSQL (relational DB) | Persistent, multi-user, DB-level RBAC, audit logs, indexing |

#### Production data flow

```
SAP / HFM export
      │
      ▼
ETL pipeline (Airflow / dbt)
      │
      ▼
PostgreSQL tables                ← financial data lives here permanently
  ├── fact_pl                    (revenue, opex, ebit by BU/region/period)
  ├── fact_opex_detail            (opex breakdown by category)
  └── fact_project_roi            (project investment & returns)
      │
      ▼
Tool calls SQL with WHERE filters ← same RBAC logic, SQL instead of pandas
      │
      ▼
Claude generates answer
```

#### Prototype vs Production — only the data fetch changes

Prototype tool (pandas):
```python
df = df[df["business_unit"] == "Electronics"]
df = df[df["period"] == "2023-Q2"]
```

Production tool (SQL — same result, same interface):
```sql
SELECT * FROM fact_pl
WHERE business_unit = 'Electronics'
  AND region       = 'Asia'
  AND period       = '2023-Q2'
```

**The agent graph, tools interface, and Claude prompts stay identical.** Only the data fetch layer inside each tool is swapped. This is why the tool abstraction matters — the LLM never knows whether data came from a CSV or a database.

#### Why NOT embed financial data in pgvector

Financial rows are structured and exact — never embed them. The rule:

| Data | Storage | Query |
|---|---|---|
| P&L rows, Opex, EBIT, ROI numbers | CSV → pandas / PostgreSQL SQL table | Exact filter + arithmetic |
| Finance glossary, IFRS definitions | pgvector | Semantic search (`<=>`) |
| Policy docs, CFO commentary | pgvector | Semantic search (`<=>`) |
| LangGraph conversation state | PostgreSQL (regular rows) | Primary key lookup |

Simple test — **"Is there one correct answer?"**
- "What was Electronics Opex in Q2 2023?" → one correct answer → **pandas / SQL**
- "What does operating leverage mean?" → open-ended → **vector search**

Embedding financial numbers introduces approximation error into data that has zero tolerance for error. A CFO seeing `$2.28M` instead of `$2.30M` due to a vector retrieval miss is a material reporting error.

---

### 2. Understanding Financial Language — How the LLM knows finance terms

The system uses **two layers** to handle finance domain knowledge:

**Layer 1 — System Prompt (Finance Domain Context)**
Every request to Claude includes a system prompt that:
- Defines key financial terms: EBIT, Opex, Gross Margin, Variance, ROI, COGS, EBT, Cash Flow, etc.
- Explains the data schema (what each column means)
- Instructs the model to always cite source (BU, region, period) in answers
- Sets tone: concise, business-friendly, management-level language

Example excerpt from system prompt:
```
You are a Finance Business Partner AI assistant.
- EBIT = Gross Profit - Opex
- Opex Variance = (Actual Opex - Budget Opex) / Budget Opex * 100
- Always cite the data source: business unit, region, and period.
- If the user asks for a trend, return values across all available periods.
```

**Layer 2 — Tool Use (Structured Data Queries)**
Claude does NOT receive the raw CSV. Instead, it is given **tools** (functions) it can call:
- `get_pl_summary(bu, region, period)` — returns a filtered P&L table
- `get_opex_variance(bu, region, period, compare_period)` — calculates % variance
- `get_ebit_trend(bu, region, year)` — returns EBIT per quarter as a list
- `get_project_roi(project_name, year_range)` — returns ROI trend

Claude reads the user's question, decides which tool(s) to call and with what parameters, receives the structured result, then generates a natural language answer. This makes answers **grounded in real data**, not hallucinated.

---

### 3. Natural Language Q&A — Full request lifecycle

```
User types: "What was our Opex variance for Q2 in Electronics?"
        │
        ▼
FastAPI  POST /chat  { role: "bu_gm", question: "..." }
        │
        ▼
data_loader.py  →  load pl_report.csv  →  filter to Electronics BU only
        │
        ▼
agent.py  →  build messages:
    system: [finance domain prompt + schema]
    user:   "What was our Opex variance for Q2 in Electronics?"
    tools:  [get_pl_summary, get_opex_variance, get_ebit_trend, ...]
        │
        ▼
Claude API  →  decides to call get_opex_variance("Electronics", "all", "2023-Q2", "2023-Q1")
        │
        ▼
tools.py  →  runs pandas calculation on filtered DataFrame  →  returns result dict
        │
        ▼
Claude API  →  receives tool result  →  generates answer:
    "Electronics Opex in Q2 2023 was $2.3M, up 4.5% vs Q1 2023 ($2.2M).
     Source: pl_report.csv, Electronics BU, All Regions, 2023-Q2."
        │
        ▼
UI renders text answer + optional HTML table
```

---

### 4. Role-Based Access Control — How data is restricted

RBAC is enforced **before** any data reaches the LLM:

```
Request arrives with role="bu_gm", bu="Electronics"
        │
        ▼
rbac.py  →  looks up permissions:
    { allowed_bus: ["Electronics"], allowed_regions: ["*"], allowed_reports: ["pl", "opex", "roi"] }
        │
        ▼
data_loader.py  →  df = df[df["business_unit"].isin(allowed_bus)]
                →  df = df[df["region"].isin(allowed_regions)]  # "*" = all
        │
        ▼
Filtered DataFrame passed to tools — CFO-only rows never exist in memory for lower roles
```

This means even if Claude tried to ask for restricted data, the tool would return an empty result — the data physically does not exist in the filtered frame.

---

### 5. Output Generation

| Output Type  | How it's generated                                      |
|--------------|---------------------------------------------------------|
| Text answer  | Claude generates natural language from tool results     |
| Data table   | Tool returns dict → rendered as HTML table in the UI   |
| Excel export | openpyxl writes filtered DataFrame to `.xlsx` on demand |
| Chart        | matplotlib generates PNG from trend data (future)       |
| PowerPoint   | python-pptx builds slide deck from summary (future)     |

---

### 6. Multilingual Support

The system prompt includes an instruction:
```
Respond in the same language the user wrote in.
```
Claude natively supports Vietnamese, Thai, Japanese, Chinese, and other languages — no additional translation layer needed. The data queries and tool calls remain in English internally; only the final answer is localized.

---

### 7. Security Design

| Concern              | Mitigation                                                       |
|----------------------|------------------------------------------------------------------|
| Data leakage         | RBAC filter applied before LLM sees any data                    |
| Prompt injection     | System prompt hardened; tool inputs validated before execution   |
| Credential exposure  | API keys in environment variables, never in code                 |
| Audit trail          | Every query logged with role, timestamp, tools called            |
| SAP integration      | In production: OAuth2 / SAP SSO, TLS in transit, no data caching|

---

## Multi-Agent Architecture

### Why multi-agent?

The single ReAct agent works for simple Q&A. But as queries get more complex, one agent trying to do everything becomes a problem:

| Problem | Example | Why one agent struggles |
|---|---|---|
| Long tool chains | "Analyze P&L, then generate a PowerPoint" | Too many steps, context grows, model loses focus |
| Parallel work | "Compare Electronics vs Consumer Goods EBIT" | Must do two data pulls + analysis simultaneously |
| Specialized logic | "Is this variance within policy threshold?" | Needs a different prompt/persona than the data retrieval agent |
| Report generation | "Create a slide deck for Q3" | File generation is a separate concern from data Q&A |

---

### Supervisor Pattern (recommended for this system)

A **Supervisor agent** receives the user query, decides which specialist agent(s) to call, collects their results, and writes the final answer.

```
User query
    │
    ▼
┌─────────────────────────────────────┐
│         SUPERVISOR AGENT            │
│  - Understands intent               │
│  - Routes to specialist(s)          │
│  - Synthesizes final response       │
└──────┬──────┬──────┬────────────────┘
       │      │      │
       ▼      ▼      ▼
  ┌────────┐ ┌───────────┐ ┌──────────────┐
  │  Q&A   │ │ Analytics │ │   Report     │
  │ Agent  │ │  Agent    │ │   Agent      │
  │        │ │           │ │              │
  │ Tools: │ │ Tools:    │ │ Tools:       │
  │ - retrieve_data     │ │ - summarize  │ │ - excel_gen  │
  │ - summarize_data    │ │ - calc_var   │ │ - pptx_gen   │
  └────────┘ └───────────┘ └──────────────┘
```

---

### How it maps to LangGraph

LangGraph implements multi-agent as a graph where each agent is a node, and the supervisor decides which edge to follow:

```python
# Each agent is a node in the same StateGraph
workflow = StateGraph(State)

workflow.add_node("supervisor", supervisor_node)
workflow.add_node("qa_agent", qa_node)
workflow.add_node("analytics_agent", analytics_node)
workflow.add_node("report_agent", report_node)

# Supervisor routes to the right agent
workflow.add_conditional_edges(
    "supervisor",
    route_to_agent,   # returns "qa_agent" | "analytics_agent" | "report_agent" | "__end__"
)

# Each agent reports back to supervisor after finishing
workflow.add_edge("qa_agent", "supervisor")
workflow.add_edge("analytics_agent", "supervisor")
workflow.add_edge("report_agent", "supervisor")

workflow.set_entry_point("supervisor")
```

The supervisor sees the conversation history + each agent's result, and decides: done → `__end__`, or needs more → route to another agent.

---

### Agent responsibilities

| Agent | Triggered when | Tools | Output |
|---|---|---|---|
| **Supervisor** | Every request | None — reasoning only | Routes to specialist(s), writes final answer |
| **Q&A Agent** | Simple data questions | `retrieve_financial_data`, `summarize_financial_data`, `search_knowledge_base` | Text answer + Mermaid charts |
| **Analytics Agent** | Variance, trend, comparison, ratio queries | `calc_variance`, `get_trend`, `compare_periods` | Numbers + Mermaid charts |
| **Report Agent** | "Generate a report / slide / export" | `generate_excel`, `generate_pptx` | File download link |

---

### Should the Q&A Agent use vector embeddings?

**Partially — depends on the question type.**

The Q&A agent receives two fundamentally different question types and uses a different retrieval method for each:

| Question type | Example | Retrieval method | Why |
|---|---|---|---|
| **Data question** | "What was Opex in Q2?" | Tool use → pandas / SQL | One correct numerical answer — must be exact |
| **Knowledge question** | "What is EBIT margin?" | Vector search → pgvector | Open-ended definition — similarity is fine |
| **Mixed** | "Is our Q2 variance within policy?" | Tool use + vector search | Needs the number AND the policy threshold |

#### How the Q&A agent decides

Claude picks the right tool based on the question. Both tools are available; it calls one or both:

```
User: "What was Electronics Opex in Q2 2023?"
    │
    ▼  data question
    └── retrieve_financial_data("OPEX")  →  pandas filter  →  exact number

User: "What does operating leverage mean?"
    │
    ▼  knowledge question
    └── search_knowledge_base("operating leverage")  →  pgvector <=>  →  definition

User: "Is our 4.5% Opex variance acceptable?"
    │
    ▼  mixed — both tools called
    ├── retrieve_financial_data("OPEX")  →  gets the variance number
    └── search_knowledge_base("opex variance policy")  →  gets the policy rule
        │
        ▼
    "4.5% is within the 5% threshold per Budget Policy 2023."
```

#### Tool definitions

```python
@tool
def retrieve_financial_data(data_type: str, config: RunnableConfig) -> str:
    # RBAC check via config.role
    # Returns CSV rows as markdown table
    # Use for: numbers, trends, P&L rows

@tool
def search_knowledge_base(query: str, config: RunnableConfig) -> str:
    # Semantic search over pgvector embeddings
    # Returns relevant chunks: glossary, policy docs, CFO commentary
    # Use for: definitions, policy rules, contextual explanations
```

#### Summary rule

```
Question has a number answer  →  tool use (pandas / SQL)
Question has a text answer    →  vector search (pgvector)
Question needs both           →  tool use first, then vector search for context
```

Financial data rows never go into pgvector. Only knowledge documents — glossary, policies, management commentary — are embedded.

---

### Shared state between agents

All agents read from and write to the same **LangGraph State** object:

```python
class State(TypedDict):
    messages: list[BaseMessage]      # full conversation history
    user_role: str                   # injected from RunnableConfig
    user_bu: str                     # injected from RunnableConfig
    active_agent: str                # which agent is currently running
    retrieved_data: str | None       # data fetched by Q&A agent (reused by others)
    chart_specs: list[str] | None    # Mermaid code blocks generated so far
    report_path: str | None          # file path if report agent generated a file
```

This way the **Analytics Agent** can reuse data already fetched by the **Q&A Agent** — no double data loading.

---

### Routing logic (supervisor decision)

The supervisor uses a simple prompt to classify intent:

```
Intent → Agent mapping:
- "what is", "show me", "how much"     → qa_agent
- "variance", "trend", "compare"       → analytics_agent
- "generate", "create report", "slide" → report_agent
- "summarize this month's P&L"         → qa_agent → report_agent (chain)
```

For complex queries that need multiple agents, the supervisor calls them **sequentially** (result of first feeds into second).

---

### Prototype vs Production

| Scope | Agents |
|---|---|
| **Prototype (this build)** | Supervisor + Q&A Agent + Analytics Agent |
| **Production** | Add Report Agent, Retrieval Agent (vector search), Planning Agent (multi-step) |

For the prototype, the Report Agent is optional — the Q&A and Analytics agents already return Mermaid charts inline.

---

## Data Query Strategy — Tool Use vs Vector Embeddings

### Two approaches compared

| Approach | How it works | Best for |
|---|---|---|
| **Tool Use (current plan)** | Claude calls a Python function → pandas query on DataFrame → returns exact numbers | Structured data: P&L, Opex, EBIT, ROI tables |
| **Vector Embedding (RAG)** | Text chunks embedded as vectors → semantic search finds relevant chunks → LLM reads them | Unstructured text: policy docs, analyst notes, management commentary |

---

### Why NOT an embedding database for financial data

Financial data like P&L rows are **structured and exact** — not text documents. Embedding databases are designed to answer "find me something *similar* to this" — but finance queries need exact answers:

| Query | Expected answer | Vector search result |
|---|---|---|
| "Opex Q2 2023 Electronics" | `$2,300,000` exactly | Returns *similar-sounding* rows — might return Q1 or Q3 |
| "EBIT margin FY2023" | `(EBIT / Revenue) * 100` calculated | Returns chunks that *mention* EBIT margin — not the number |
| "Variance vs last quarter" | `(2300000 - 2200000) / 2200000` | No subtraction capability — just retrieves text |

The fundamental mismatch:
- **Embedding search** = approximate similarity → wrong for numbers
- **Pandas filter** = exact match + arithmetic → correct for numbers

If you embedded `pl_report.csv` rows as vectors and searched for "Electronics Q2 Opex", you might get Q1 back (0.94 similarity score) instead of Q2 (0.96) — and that 2% error on a $2M number is a $40K mistake. Unacceptable for finance.

### Why Tool Use is better for financial tables

Financial data like P&L and Opex lives in structured rows/columns. The queries are precise:
- "Opex for Electronics Q2 2023" → filter 2 columns, return 1 number
- "EBIT trend 2023" → group by quarter, return 4 numbers
- "Variance vs last quarter" → subtract two cells, divide, multiply by 100

These are **deterministic calculations** — there is one correct answer. If you embed a CSV as vectors and do semantic search, you risk:
- Retrieving the wrong quarter's chunk
- Missing rows because embedding similarity is approximate
- Getting a "close enough" answer instead of the exact number

Tool use gives Claude a **calculator**, not a guess. Claude decides *what* to query; Python calculates *exactly*.

```
User: "Opex variance Q2 vs Q1 for Electronics?"
        │
        ▼ Tool Use
Claude calls: get_opex_variance(bu="Electronics", period="2023-Q2", compare="2023-Q1")
        │
        ▼ pandas
result = (2300000 - 2200000) / 2200000 * 100  →  4.55%
        │
        ▼ Claude answers
"Electronics Opex increased 4.55% in Q2 2023 vs Q1 2023 ($2.3M vs $2.2M)."
```

---


### So the full data architecture is:

```
Financial data (P&L, Opex, ROI)          Knowledge & Memory
        │                                         │
        ▼                                         ▼
  CSV files (prototype)               PostgreSQL + pgvector
  SAP/HFM API (production)            ├── LangGraph checkpoints
        │                             ├── Conversation memory
        ▼                             └── Finance glossary embeddings
  pandas filter (RBAC)                            │
        │                                         ▼
        └──────────────► Claude ◄────── Semantic search (pgvector <=>)
                            │
                            ▼
                      Final answer + Mermaid charts
```

**Financial data never goes into pgvector** — it stays in CSV/SQL tables with exact pandas/SQL queries. pgvector handles memory and knowledge, not financial facts.

---

### When to ADD vector embeddings (as a complement)

Embeddings are valuable for the **knowledge layer** — not the data layer:

| Use case | What to embed | Why |
|---|---|---|
| Finance glossary | IFRS definitions, accounting terms | User asks "what is EBITDA?" — LLM retrieves the definition |
| Policy documents | Budget policies, variance thresholds | "Is a 5% Opex variance acceptable?" — LLM retrieves the policy |
| Management commentary | Previous CFO summaries, board notes | "What did management say about Electronics last year?" |
| SAP field mapping | SAP GL account codes → plain English | Translate raw SAP data labels to business terms |

---

### Recommendation for this prototype

| Layer | Approach | Reason |
|---|---|---|
| Structured financial data (CSV) | **Tool Use only** | Deterministic, exact, no hallucination risk |
| Finance knowledge / glossary | **Embeddings (optional)** | Good for explaining terms and policies |
| Production SAP/HFM data | **Tool Use via API** | Same pattern, replace CSV with API call |

**For the prototype: implement Tool Use first.** Add embeddings in a second pass only for the knowledge base (glossary + policy docs). This keeps the system simple, accurate, and explainable.

---

## Stack
- **Backend:** Python + FastAPI
- **Frontend:** Simple HTML/JS (single page, no framework — renders Mermaid charts)
- **Agent Framework:** LangGraph (`StateGraph` with ReAct loop — same pattern as reference repo)
- **LLM:** Claude API (claude-sonnet-4-6) with tool use
- **Observability:** Langfuse (trace every agent run, tool call, token usage)
- **Data:** Mock CSV files simulating SAP/HFM exports

> **Reference:** Architecture aligned with [tam159/ai_finance](https://github.com/tam159/ai_finance) — single ReAct agent, LangGraph StateGraph, role-injected via `RunnableConfig`, Mermaid chart output.

---

## File Structure
```
ask-finance/
├── data/
│   ├── pl_report.csv              # P&L by BU, region, quarter (mock SAP export)
│   ├── opex_detail.csv            # Opex breakdown by category
│   └── project_roi.csv            # Project-level ROI tracking
├── app/
│   ├── data_ingestion/
│   │   ├── csv_loader.py          # CSV → markdown table (for LLM context)
│   │   └── csv_analyzer.py        # CSV → statistical summary
│   ├── finance_agent/
│   │   ├── configuration.py       # RunnableConfig: model, role, system_prompt
│   │   ├── state.py               # LangGraph State & InputState schemas
│   │   ├── graph.py               # LangGraph StateGraph (ReAct loop)
│   │   ├── tools.py               # retrieve_financial_data, summarize_financial_data
│   │   ├── prompts.py             # System prompt with Mermaid chart instructions
│   │   └── utils.py               # load_chat_model helper
├── static/
│   └── index.html                 # Chat UI (role selector + chat + Mermaid renderer)
├── main.py                        # FastAPI server
└── requirements.txt
```

---

## UI Design
- **Role selector** dropdown: Analyst / BU GM / Group CFO
- **Chat input** box — type a question, press Send
- **Response area** — renders text answer + optional data table
- Role is simulated via dropdown (no login required for prototype)

---

## Request Flow
1. User selects role → types question → hits Send
2. FastAPI receives `POST /chat` with `{ role, question }`
3. `data_loader.py` loads and filters CSVs based on role permissions
4. `agent.py` calls Claude API with tool definitions and filtered data context
5. Claude invokes tools to query data, then generates a structured answer
6. Response (text + optional table) is returned to the UI

---

## Role-Based Access Control (RBAC)

### Role permissions matrix

| Role       | Accessible BUs         | Accessible Regions | Report Types                           |
|------------|------------------------|--------------------|----------------------------------------|
| Analyst    | Assigned BU only       | Assigned region    | P&L, Opex                              |
| BU GM      | Own BU (all regions)   | All regions        | P&L, Opex, Project ROI                 |
| Group CFO  | All BUs                | All regions        | All: P&L, Opex, ROI, Cash Flow         |

### Role profiles (simulated users)

| User (mock)     | Role       | BU              | Region  |
|-----------------|------------|-----------------|---------|
| alice@corp.com  | Analyst    | Electronics     | Asia    |
| bob@corp.com    | BU GM      | Electronics     | All     |
| carol@corp.com  | BU GM      | Consumer Goods  | All     |
| david@corp.com  | Group CFO  | All             | All     |

### How RBAC is enforced (step by step)

1. Request arrives with `role` and `user_bu` (e.g. role=`bu_gm`, bu=`Electronics`)
2. `rbac.py` looks up the role → returns `{ allowed_bus, allowed_regions, allowed_reports }`
3. `data_loader.py` filters the DataFrame:
   ```python
   df = df[df["business_unit"].isin(allowed_bus)]      # restrict BU
   df = df[df["region"].isin(allowed_regions)]          # restrict region
   ```
4. Only the filtered DataFrame is passed to tools — restricted rows are physically removed from memory
5. Claude cannot access data it was never given — even if it tries to call a tool with restricted parameters, the result will be empty

### What each role sees (example: "Show me all EBIT")

- **Analyst (Electronics / Asia):** EBIT for Electronics, Asia only
- **BU GM (Electronics):** EBIT for Electronics, all regions
- **Group CFO:** EBIT for all BUs, all regions

---

## Agent Design — LangGraph Multi-Agent Graph

The system uses a **Supervisor + Specialist** pattern. Each agent is a node in one `StateGraph`. The reference repo shows a single ReAct loop — this builds on top of that pattern by adding a supervisor that routes between multiple specialist agents.

#### Full graph

```
__start__
    │
    ▼
supervisor  ◄─────────────────────────────────────┐
    │                                               │
    ▼                                               │
route_to_agent                                      │
    │                                               │
    ├── "qa_agent"        ──► qa_node       ────────┤
    │                          │  ReAct loop:       │
    │                          │  call_model ◄──┐   │
    │                          │      │         │   │
    │                          │  route_output  │   │
    │                          │      ├─ tools ─┘   │
    │                          │      └─ done ───────┤
    │                                               │
    ├── "analytics_agent" ──► analytics_node ───────┤
    │                          │  (same ReAct loop) │
    │                                               │
    ├── "report_agent"    ──► report_node    ────────┤
    │                          │  (same ReAct loop) │
    │                                               │
    └── "__end__"         ──► __end__
```

Each specialist agent is its own **ReAct loop** (call_model ↔ tools), identical to the reference repo pattern. The supervisor wraps them and decides who runs next.

#### LangGraph wiring

```python
workflow = StateGraph(State, input=InputState, config_schema=Configuration)

# Supervisor node
workflow.add_node("supervisor", supervisor_node)

# Specialist nodes — each is a compiled sub-graph (ReAct loop)
workflow.add_node("qa_agent",        qa_agent_node)
workflow.add_node("analytics_agent", analytics_agent_node)
workflow.add_node("report_agent",    report_agent_node)

# Supervisor routes to specialists
workflow.add_conditional_edges(
    "supervisor",
    route_to_agent,   # returns "qa_agent" | "analytics_agent" | "report_agent" | "__end__"
)

# All specialists return to supervisor after finishing
workflow.add_edge("qa_agent",        "supervisor")
workflow.add_edge("analytics_agent", "supervisor")
workflow.add_edge("report_agent",    "supervisor")

workflow.set_entry_point("supervisor")
graph = workflow.compile()
```

#### Key points
- `supervisor_node`: Calls Claude with no tools — reasoning only. Classifies intent, routes, and synthesizes the final answer.
- `qa_node`, `analytics_node`, `report_node`: Each is a full ReAct loop (same pattern as reference repo) with its own tool set and system prompt.
- Role is injected once via `RunnableConfig` → available to every node via `Configuration.from_runnable_config(config)`.
- Every node run is traced in **Langfuse** (tokens, latency, tool calls, which agent ran).

## LLM Tool Definitions

Tools check `config.role` before returning data — RBAC is enforced inside the tool, not in the router:

| Tool | Description | RBAC check |
|---|---|---|
| `retrieve_financial_data(data_type)` | Returns full CSV as markdown table | role must be in allowed_roles for that data_type |
| `summarize_financial_data(data_type)` | Returns statistical summary (min, max, mean, totals) | same role check |

Supported `data_type` values: `PNL`, `OPEX`, `ROI`

Role → data access map:
- `analyst` → PNL (own BU/region only), OPEX
- `bu_gm` → PNL (own BU all regions), OPEX, ROI
- `group_cfo` → all data types, all BUs, all regions

---

## Data Files (Mock)
- `pl_report.csv`: revenue, COGS, gross profit, Opex, EBIT, net income by BU/region/quarter
- `opex_detail.csv`: Opex broken down by category (headcount, marketing, IT, travel) by BU/region/quarter
- `project_roi.csv`: project name, year, investment, return, ROI % by BU

---

## Chart Generation in the Chatbox

### How it works end-to-end

```
Claude response text
    │
    │  Contains mixed content:
    │  "Electronics EBIT grew 32%..."
    │  ```mermaid
    │  xychart-beta
    │    title "EBIT Trend"
    │    ...
    │  ```
    │  "The main driver was..."
    │
    ▼
Frontend (index.html)
    │
    ├─ Split response into text blocks and ```mermaid blocks
    │
    ├─ Text blocks  →  render as HTML paragraph
    │
    └─ Mermaid blocks  →  mermaid.js  →  render as inline SVG chart
```

No image files, no server-side rendering — charts are generated **directly in the browser** from the code string Claude wrote.

---

### Step 1 — System prompt tells Claude to write Mermaid

The system prompt instructs Claude to always include charts:

```
After answering, create 1-3 Mermaid charts to visualize key findings.
Use ONLY these types:

pie title Revenue by BU
    "Electronics" : 450
    "Consumer Goods" : 300

xychart-beta
    title "EBIT Trend"
    x-axis [Q1-23, Q2-23, Q3-23, Q4-23]
    y-axis "EBIT ($M)" 0 --> 5
    line [2.8, 3.0, 3.3, 3.7]
```

Rules enforced in prompt (from reference repo — prevents parser errors):
- Only `pie` and `xychart-beta` — no flowchart, no sequence diagram
- No apostrophes in axis labels: `Q1-23` ✓  `Q1'23` ✗
- One data series per chart (no mixed bar+line)
- Max 10–12 data points per axis

---

### Step 2 — Backend returns raw text (including Mermaid fences)

FastAPI returns the full Claude response as a plain string. No pre-processing needed:

```json
{
  "answer": "Electronics EBIT grew from $2.8M in Q1 to $3.7M in Q4 2023, a 32% increase.\n\n```mermaid\nxychart-beta\n    title \"Electronics EBIT 2023\"\n    x-axis [Q1-23, Q2-23, Q3-23, Q4-23]\n    y-axis \"EBIT ($M)\" 0 --> 5\n    line [2.8, 3.0, 3.3, 3.7]\n```\n\nThe growth was driven by..."
}
```

---

### Step 3 — Frontend parses and renders

The UI splits the response on ` ```mermaid ` fences, then passes each block to `mermaid.js`:

```html
<!-- Load mermaid.js from CDN — no install needed -->
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<script>mermaid.initialize({ startOnLoad: false, theme: 'default' });</script>
```

```javascript
async function renderResponse(text) {
  // Split on ```mermaid ... ``` blocks
  const parts = text.split(/(```mermaid[\s\S]*?```)/g);

  for (const part of parts) {
    if (part.startsWith('```mermaid')) {
      // Extract code between fences
      const code = part.replace(/```mermaid\n?/, '').replace(/```$/, '');

      // Create a div, let mermaid render SVG into it
      const div = document.createElement('div');
      div.className = 'mermaid';
      div.textContent = code;
      chatbox.appendChild(div);

      await mermaid.run({ nodes: [div] }); // renders SVG in-place
    } else {
      // Plain text — render as paragraph
      const p = document.createElement('p');
      p.textContent = part;
      chatbox.appendChild(p);
    }
  }
}
```

---

### What the user sees

```
┌─────────────────────────────────────────────────┐
│  Electronics EBIT grew 32% in FY2023, from      │
│  $2.8M in Q1 to $3.7M in Q4.                    │
│                                                  │
│  ┌──── EBIT Trend (SVG chart) ────────────┐     │
│  │  4 ┤                          ●        │     │
│  │  3 ┤          ●       ●               │     │
│  │  2 ┤  ●                               │     │
│  │    └──Q1-23──Q2-23──Q3-23──Q4-23──   │     │
│  └────────────────────────────────────────┘     │
│                                                  │
│  The growth was driven by Asia region revenue.   │
└─────────────────────────────────────────────────┘
```

Charts are inline SVG — they scale, look clean, and require zero extra dependencies beyond the CDN script tag.

---

### Output Formats Summary

| Format | Mechanism | Where rendered |
|---|---|---|
| Text answer | Claude natural language | HTML `<p>` in chatbox |
| Pie chart | Claude writes Mermaid → `mermaid.js` renders SVG | Inline in chatbox |
| Bar / Line chart | Claude writes Mermaid xychart-beta → SVG | Inline in chatbox |
| Excel export (future) | openpyxl on server → file download | Browser download |
| PowerPoint (future) | python-pptx on server → file download | Browser download |

---

## Evaluation Design
| Dimension           | Method                                                         |
|---------------------|----------------------------------------------------------------|
| Accuracy            | Compare LLM output to direct pandas calculation ground truth  |
| RBAC compliance     | Test each role receives only permitted data                    |
| Explainability      | Check every answer cites source (file, period, BU, region)    |
| Security            | Verify filtered data never leaks across role boundaries        |
| Response time       | Log end-to-end latency per query, target < 5s                  |

---

## Vector Embeddings — Demo Implementation

A lightweight knowledge base using **ChromaDB** (in-memory, no server needed) to answer finance definition and policy questions.

### What gets embedded

```
data/
├── knowledge/
│   ├── finance_glossary.json    # EBIT, Opex, ROI, Variance, COGS, etc.
│   └── budget_policy.json       # Variance thresholds, approval limits
```

Each entry is a short text chunk — one term or one policy rule per document:
```json
[
  { "id": "ebit", "text": "EBIT (Earnings Before Interest and Tax) = Gross Profit - Operating Expenses. Measures core operating profitability before financing costs." },
  { "id": "opex_variance_policy", "text": "Opex variance above 5% requires BU GM approval. Above 10% requires Group CFO sign-off." }
]
```

### Stack for demo

| Component | Choice | Why |
|---|---|---|
| Vector store | **ChromaDB** (in-memory) | Zero config, no Docker, runs in Python process |
| Embedding model | **Claude / OpenAI text-embedding-3-small** | Small, fast, cheap |
| Search | Cosine similarity (`<=>` equivalent) | Built into ChromaDB |

### How it's built at startup

```python
# app/knowledge/vector_store.py
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

client = chromadb.Client()  # in-memory for demo
collection = client.create_collection(
    name="finance_knowledge",
    embedding_function=OpenAIEmbeddingFunction(model_name="text-embedding-3-small")
)

def load_knowledge_base():
    docs = load_json("data/knowledge/finance_glossary.json")
    docs += load_json("data/knowledge/budget_policy.json")
    collection.add(
        ids=[d["id"] for d in docs],
        documents=[d["text"] for d in docs],
    )
```

Called once at FastAPI startup — embeddings generated and stored in memory.

### The `search_knowledge_base` tool

```python
@tool
def search_knowledge_base(query: str) -> str:
    results = collection.query(query_texts=[query], n_results=3)
    chunks = results["documents"][0]
    return "\n\n".join(chunks)
```

Claude calls this when the question is a definition or policy query. Returns the top 3 matching chunks as plain text.

### Full flow for a knowledge question

```
User: "What is EBIT and how is it calculated?"
    │
    ▼
Q&A Agent → Claude decides → knowledge question
    │
    └── search_knowledge_base("EBIT calculation")
            │
            ▼
        ChromaDB cosine search
            │
            ▼
        "EBIT = Gross Profit - Operating Expenses..."
            │
            ▼
        Claude answers: "EBIT stands for Earnings Before Interest and Tax.
        It is calculated as: EBIT = Gross Profit − Opex.
        Source: finance_glossary"
```

### Demo vs Production path

| | Demo | Production |
|---|---|---|
| Vector store | ChromaDB in-memory | PostgreSQL + pgvector |
| Persistence | Lost on restart | Persisted in DB |
| Embedding | At startup from JSON | ETL pipeline re-embeds on doc update |
| Scale | ~100 docs | Thousands of docs |

The `search_knowledge_base` tool interface stays identical — only the store behind it changes.

---

## Multilingual Support

Claude natively understands and responds in Vietnamese, Thai, Japanese, Chinese, and other languages — **no translation layer needed**. The only change required is a one-line instruction in the system prompt.

### How it works

```
User types in Vietnamese: "Cho tôi biết EBIT của Electronics Q2 2023?"
    │
    ▼
FastAPI detects language from request header or UI locale selector
    │
    ▼
system prompt includes: "Respond in the same language the user wrote in."
    │
    ▼
Claude calls tools (internally in English — data queries stay English)
    │
    ▼
Claude answers in Vietnamese:
    "EBIT của bộ phận Electronics trong Q2 2023 là $3.0 triệu,
     tăng 7.1% so với Q1 2023 ($2.8 triệu).
     Nguồn: pl_report.csv, Electronics, Tất cả khu vực, 2023-Q2."
```

### Key design points

| Concern | Approach |
|---|---|
| **Tool calls** | Always in English — `data_type="PNL"`, filters use English column names |
| **Financial terms** | Claude keeps standard terms (EBIT, Opex, ROI) untranslated in the answer — they are internationally recognised |
| **System prompt** | Add one line: `"Respond in the same language the user wrote in."` |
| **Locale detection** | UI sends `Accept-Language` header or user picks language from a dropdown |
| **No extra cost** | Claude handles translation natively — no external translation API needed |

### System prompt addition (demo)

```python
SYSTEM_PROMPT = """You are a Finance Business Partner AI assistant.
...
Respond in the same language the user wrote in.
Keep financial terms (EBIT, Opex, ROI, P&L, COGS) in their standard English form.
System time: {system_time}"""
```

### UI — language selector (optional for demo)

A simple dropdown in the chat UI lets the user pick their language. The selected locale is sent with every request. If omitted, Claude auto-detects from the question text.

```
[ Language: 🌐 Auto-detect ▼ ]   ← default
           Vietnamese
           Thai
           Japanese
           English
```

### Supported languages (Claude native)
Vietnamese, Thai, Japanese, Simplified Chinese, Traditional Chinese, Korean, French, German, Spanish, Indonesian, Malay — and more. No configuration required.

---

## Future Enhancements
1. **Real SAP connector** — replace CSVs with SAP RFC/OData API calls
2. **Vector embeddings (production)** — migrate ChromaDB → PostgreSQL + pgvector, add ETL pipeline for re-embedding on doc update
3. **Multi-language glossary** — translate finance_glossary.json into local languages for knowledge base search in Vietnamese/Thai
4. **PowerPoint output** — use python-pptx to generate slide summaries
5. **Audit log** — log every query + role + data accessed for compliance
6. **SSO / real RBAC** — integrate with corporate identity provider (Azure AD, Okta)
7. **Streaming responses** — use Claude streaming API for faster perceived response time
