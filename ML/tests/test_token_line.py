"""The per call token usage line matches the format the ML service parses.

The Bun ML service greps stdout for this exact shape to feed the Cost Dashboard,
so the format is a contract. This test pins it.
"""

import re
import logging

from ML.utils import _record_token_usage
from ML.mock_llm import MockResponse

# Mirrors the regex in backend/ml-service/index.ts
BUN_REGEX = re.compile(
    r"\[([^\]]+)\] Token usage: in=(\d+), out=(\d+), cost=\$([0-9.]+), latency=([0-9.]+)s"
)


def test_token_line_matches_service_regex(caplog):
    response = MockResponse("some output", input_tokens=120, output_tokens=45)
    with caplog.at_level(logging.INFO, logger="office_chain"):
        entry = _record_token_usage("CEO", response, [("system", "hi")], latency=1.23)

    assert entry["input_tokens"] == 120
    assert entry["output_tokens"] == 45

    matches = [BUN_REGEX.search(m) for m in caplog.messages]
    matches = [m for m in matches if m]
    assert matches, f"no token line matched the service regex in {caplog.messages}"

    office, tin, tout, cost, latency = matches[0].groups()
    assert office == "CEO"
    assert int(tin) == 120
    assert int(tout) == 45
    assert float(cost) >= 0.0
    assert float(latency) == 1.23
