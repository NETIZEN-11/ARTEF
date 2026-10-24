from app.core.exceptions import (
    TargetAgentError,
    TargetAgentTimeoutError,
    TargetAgentUnavailableError,
)


def test_target_agent_errors_construct_with_their_codes():
    # These subclasses used to pass three arguments to a two-argument base class, so every
    # target timeout / HTTP error surfaced as a TypeError instead.
    timeout = TargetAgentTimeoutError("http://agent/chat", 5)
    unavailable = TargetAgentUnavailableError("http://agent/chat", 503)

    assert isinstance(timeout, TargetAgentError) and timeout.code == "TARGET_AGENT_TIMEOUT"
    assert timeout.details == {"url": "http://agent/chat", "timeout": 5}
    assert unavailable.code == "TARGET_AGENT_UNAVAILABLE"
    assert unavailable.details["status_code"] == 503
    assert TargetAgentError("boom").code == "TARGET_AGENT_ERROR"
