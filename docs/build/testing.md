# Test and evaluate

Two kinds of checks:

| | `aiapp test` | `aiapp eval` |
|---|---|---|
| Models | scripted fakes (fast, free, repeatable) | your real models |
| Checks | your code and app behaviour | answer quality |
| Where | `tests/` | `evals/*.yaml` |
| Use in CI | always | on a schedule or before release |

## Tests: `aiapp test`

`aiapp test` starts a throwaway server, deploys a copy of the app with every model replaced by a script, and runs `tests/`. Everything else is real: routes, workers, storage, document search, jobs, workflows and guardrails.

```python
# tests/test_leave.py
from aiapp.testing import AppTest

class Leave(AppTest):
    def test_answers_from_the_policy(self):
        self.models.reply("Employees get 25 days of paid leave [1].", when="leave")
        r = self.client.chat("How many days of leave do I get?")
        self.assertIn("25 days", r.text)
        self.assertEqual(r.citations[0]["source"], "README.md")
        self.assertIn("25 days of paid annual leave", self.models.last.system)   # the passage reached the model

    def test_model_outage_is_handled(self):
        self.models.fail(503, times=None)
        r = self.client.chat("How many days of leave do I get?")
        self.assertIn("unavailable", r.text.lower())
```

```bash
aiapp test                # all tests
aiapp test -k Leave -v    # some, verbosely
```

**Useful tools in tests:**

| | |
|---|---|
| `self.models.reply(text, when="word")` | script an answer (when the prompt contains a word) |
| `self.models.fail(503, times=1)` | make the model fail (`times=None`: always) |
| `self.models.json({...})` | script a JSON answer (for `.json()` calls) |
| `self.models.tool_call("lookup_order", {...}, then="…")` | script an agent calling a tool, then answering |
| `self.models.transcript("…")` | script a speech-to-text result |
| `self.models.last`, `self.models.calls` | what was sent to the model |
| `self.client.chat(...)`, `.post(route, json)`, `.get(...)`, `.upload(...)` | call the app |
| `self.harness.key("approver")` | an API key with roles |
| `self.harness.wait_jobs()`, `.logs()`, `.cli(...)` | jobs, audit records, any CLI command |

### pytest

Install pytest in the server's Python and run `aiapp test --pytest`. Fixtures:

```python
def test_answers_from_the_policy(aiapp_client, aiapp_models):
    aiapp_models.reply("Employees get 25 days of paid leave [1].", when="leave")
    assert "25 days" in aiapp_client.chat("How many days of leave do I get?").text

def test_approver_can_list(aiapp_client, aiapp_key):
    key = aiapp_key("approver")
    ...
```

`aiapp` (the harness), `aiapp_models`, `aiapp_client`, `aiapp_key`.

## Evaluations: `aiapp eval`

Golden cases, run against the deployed app with real models:

```yaml
# evals/golden.yaml
cases:
  - name: annual leave
    input: How many days of paid annual leave do employees get?
    expect:
      contains: ["25"]
      not_contains: ["I don't know"]
      citations: { min: 1 }
      max_latency_ms: 8000
      judge: States that employees get 25 days of paid annual leave per year.   # graded by a model
  - name: double charge is billing
    route: /classify
    body: { text: "I was charged twice for my order" }
    expect:
      json: { label: billing }            # dotted paths to expected values, e.g. "result.label"
```

To upload a file instead, use `file: samples/invoice.pdf` (and `query: { wait: 60 }` for extraction).

Other checks: `status`, `regex`, `citations: { min: 1, sources: [leave.md] }`. `tags:` group cases.

```bash
aiapp eval                               # pass/fail per case, compared with the last run
aiapp eval --min-pass 0.9 --no-regress   # as a CI gate
aiapp eval --history                     # past runs (also in the console's Evals tab)
```

New apps come with starter cases.
