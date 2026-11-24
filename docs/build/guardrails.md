# Guardrails

Guardrails check requests before your app sees them (**input**) and answers before the caller sees them (**output**). They can **allow**, **redact** (change the text) or **block** (refuse with a message). Every decision is logged and recorded in the audit log, without the text itself.

```yaml
guardrails:
  - pii-redaction                      # emails, phone and card numbers never reach the model
  - prompt-injection                   # refuses "ignore your instructions…"
  - output-pii                         # redacts them in answers too
  - citations-required: { routes: [/chat] }
  - blocked-topics:
      topics: [{ name: legal advice, keywords: [lawsuit, sue] }]
      message: "I can't give legal advice. Please contact Legal."
```

## Built-in guardrails

| Guardrail | Stage | What it does | Settings |
|---|---|---|---|
| `pii-redaction` | model calls | redacts emails, phone numbers, card numbers (Luhn-checked), US SSNs and IP addresses in everything sent to a model provider | |
| `output-pii` | output | redacts the same in answers, also while streaming | |
| `prompt-injection` | input | refuses attempts to override the instructions | `threshold` (default 3; lower is stricter) |
| `blocked-topics` | input (or `stage: output` / `both`) | refuses subjects by keyword or pattern | `topics: [{name, keywords, patterns}]` |
| `max-input` | input | refuses requests with too much text | `chars` |
| `citations-required` | output | withholds answers that cite no document | `routes` |
| `presidio` | input (or `output` / `both`) | redacts **names, places** and other entities with Microsoft Presidio | `entities`, `score`, `language`, `model` |
| `azure-content-safety` | input and output | blocks hate, self-harm, sexual and violent content with Azure AI Content Safety; optional Prompt Shields | `severity`, `categories`, `prompt_shields`, `blocklists`, `endpoint`, `api_key_env` |

**Common settings on any guardrail:** `routes: [/chat]` (only these routes), `message:` (what the caller sees when blocked), `stage: input|output|both`, `dry_run: true`, `on_error: allow` (default is to refuse when a guardrail itself fails).

## Presidio (names and addresses)

Install it once in the server's Python:

```bash
pip install presidio-analyzer presidio-anonymizer
python -m spacy download en_core_web_sm
```

```yaml
guardrails:
  - presidio: { entities: [PERSON, LOCATION, EMAIL_ADDRESS, PHONE_NUMBER], score: 0.6, stage: both }
```

"Please ask Maria Garcia in Seattle to call back" becomes "Please ask [PERSON] in [LOCATION] to call back".

## Azure AI Content Safety

Create a Content Safety resource in Azure, then set `AZURE_CONTENT_SAFETY_ENDPOINT` and either `AZURE_CONTENT_SAFETY_KEY` or give the server a managed identity with the *Cognitive Services User* role.

```yaml
guardrails:
  - azure-content-safety:
      prompt_shields: true          # also stop jailbreak and indirect prompt attacks on input
      severity: 4                   # block at this severity or above (default 4)
      categories: [Hate, Violence]  # default: all four
      blocklists: [brand-terms]     # your custom lists in the resource
```

## Job results and published events

Output guardrails can also check what your background jobs return and what your app publishes to topics:

```yaml
guardrails:
  - presidio: { entities: [PERSON, LOCATION], jobs: ["*"] }
  - azure-content-safety: { events: [public-posts] }
```

A redaction changes what is stored; a block fails the job (without retries) or refuses the publish.

## Tune without breaking users: dry run

```yaml
guardrail_mode: dry-run      # all guardrails only log what they would do
```

Then look at `aiapp audit --type guardrail` and `aiapp trace`, adjust, and remove the line.

## Write your own in Python

```yaml
guardrails:
  - no-competitors: { handler: "guards:competitors", stage: both }
```

```python
from aiapp import guardrails

async def competitors(req):
    check = guardrails.Check.from_request(req)     # check.texts, check.stage, check.metadata
    if any("fabrikam" in t.lower() for t in check.texts):
        return guardrails.block("mentions a competitor", message="I can only talk about Contoso.")
    return guardrails.allow()
    # or: return guardrails.redact([t.replace("secret", "[redacted]") for t in check.texts], "removed secrets")
```

A plugin can call `app.models` too, to use a model as a classifier. It must answer within 10 seconds.
