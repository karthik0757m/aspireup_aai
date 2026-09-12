import pytest
from access import require_ai_access

def test_hosted_ai_fails_closed(monkeypatch):
    monkeypatch.setenv('RENDER','true')
    monkeypatch.delenv('DEMO_ACCESS_CODE',raising=False)
    with pytest.raises(ValueError,match='not configured'): require_ai_access('')

def test_access_code(monkeypatch):
    monkeypatch.setenv('DEMO_ACCESS_CODE','unit-test-code')
    with pytest.raises(ValueError): require_ai_access('wrong')
    require_ai_access('unit-test-code')

def test_local_demo_no_code(monkeypatch):
    monkeypatch.delenv('RENDER',raising=False)
    monkeypatch.delenv('DEMO_ACCESS_CODE',raising=False)
    require_ai_access('')
