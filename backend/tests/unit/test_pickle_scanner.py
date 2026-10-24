"""The pickle scanner must detect code-executing pickles without ever loading them."""
import collections
import os
import pickle

import pytest

from app.security.model_scanner.detectors import PickleDetector


class _Malicious:
    def __reduce__(self):
        return (os.system, ("echo should-never-run",))


@pytest.mark.parametrize("protocol", [2, 4])
def test_detects_os_system_payload(tmp_path, protocol):
    path = tmp_path / "model.pkl"
    path.write_bytes(pickle.dumps(_Malicious(), protocol=protocol))

    findings = PickleDetector()._scan_pickle_file(path)

    assert [f.finding_type for f in findings] == ["dangerous_import"]
    assert findings[0].metadata["name"] == "system"


@pytest.mark.parametrize(
    "payload", [{"weights": [1.0, 2.0]}, collections.OrderedDict(layer=1), [1, "two", 3.0]]
)
def test_plain_data_is_not_flagged(tmp_path, payload):
    path = tmp_path / "model.pkl"
    path.write_bytes(pickle.dumps(payload, protocol=4))

    assert PickleDetector()._scan_pickle_file(path) == []


def test_scanner_never_unpickles(tmp_path, monkeypatch):
    path = tmp_path / "model.pkl"
    path.write_bytes(pickle.dumps(_Malicious(), protocol=4))

    def _fail(*_args, **_kwargs):
        raise AssertionError("scanner must not unpickle untrusted files")

    monkeypatch.setattr(pickle, "load", _fail)
    monkeypatch.setattr(pickle, "loads", _fail)

    assert PickleDetector()._scan_pickle_file(path)
