"""A guardrail is a handler that returns allow, redact or block. It sees the
request's texts (input) and the answer (output). It may call app.models too,
to use a model as a classifier."""

from aiapp import guardrails

COMPETITORS = ("fabrikam", "northwind")


async def competitors(req):
    check = guardrails.Check.from_request(req)
    if any(name in t.lower() for t in check.texts for name in COMPETITORS):
        return guardrails.block("mentions a competitor")
    return guardrails.allow()
