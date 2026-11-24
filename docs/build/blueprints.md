# The ten blueprints

A blueprint is a complete app type. `aiapp new BLUEPRINT NAME --provider PROVIDER` creates a working app you can deploy at once; every setting in its `ai-app.yaml` is commented.

| Blueprint | What it does | Main route | Built-in page |
|---|---|---|---|
| `knowledge-chat` | Answers from your documents with citations; remembers the conversation | `POST /chat` (streams) | chat |
| `customer-support` | Answers from documents, calls your tools (order lookup…), asks a person before sensitive actions (refunds), hands off to a person | `POST /chat` | chat |
| `document-extraction` | Fields from PDFs, scans, photos and Office files, as JSON with page and quote evidence | `POST /extract` (upload) | upload |
| `summarization` | Summaries and key points of long documents | `POST /summarize` | upload |
| `classification` | Sorts texts into your labels (tickets, emails…), one at a time or in batches | `POST /classify` | try-it |
| `meeting-notes` | Recordings or transcripts to decisions, action items with owners, and open questions | `POST /notes` (upload) | upload |
| `content` | A brief to an outline and a draft, then human review with revisions | `POST /drafts` | review |
| `insights` | Questions about data in PostgreSQL, SQL Server or CSV files: the model writes read-only SQL, and you see the queries | `POST /ask` | ask |
| `code-assistant` | Questions about a codebase (Git or folder), citing files and lines | `POST /chat` | chat |
| `workflow-agent` | An agent with your tools and MCP servers; chosen tools wait for a person's approval | `POST /run` | runs |

The page is at `http://SERVER:8080/apps/NAME/`.

## Highlights

### knowledge-chat
Put documents in `policies/` (or any folder), `aiapp source add ./policies/`, deploy. Add [connectors](documents.md) for SharePoint, Git, websites and more. Turn on `citations-required` to withhold answers the documents don't support.

### customer-support
Write your tools in `tools.py` (`@app.tool` functions). Tools listed under `support.approval_required` (such as `refund_order`) become approval requests instead of running. Handoffs to a person are published to the `support.handoffs` topic; consume them with a [subscription](jobs-events.md).

### document-extraction
Describe the fields in `schema.json` (JSON Schema) and any rules in `instructions.md`. Upload with `POST /extract` (multipart or raw body); add `?wait=60` to wait for the result, otherwise poll the returned job. Every field comes with the page and quote it was found in.

### insights
```yaml
insights:
  files: [./data/]       # CSV files become SQLite tables named after the files
  databases:             # use a login that can only read
    - { name: sales, driver: postgres, dsn: "${SALES_DB}", tables: [orders, customers], max_rows: 200 }
  instructions: "Amounts are in EUR. Quarters are calendar quarters."
```
The answer includes the SQL that was run.

### workflow-agent
```yaml
agent:
  instructions: >
    You are the support agent for an online shop. Look up the facts with the tools first.
  max_steps: 10
  approval_required: [refund_order]    # waits for: aiapp approve, or /apps/NAME/_approvals/
  approval_timeout: 24h
mcp:                                   # tools from MCP servers, too
  - { name: files, command: [npx, -y, "@modelcontextprotocol/server-filesystem", ./data] }
```

!!! tip
    Each new app includes `.github/copilot-instructions.md`, which teaches GitHub Copilot and other coding assistants how this SDK works, so they suggest correct code.
