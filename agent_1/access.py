"""Protect hosted model calls while keeping the offline demonstration open."""
import hmac
import os


def require_ai_access(entered_code):
    expected = os.getenv('DEMO_ACCESS_CODE', '')
    if os.getenv('RENDER') and not expected:
        raise ValueError('AI access is not configured. The owner must set DEMO_ACCESS_CODE in Render. Offline demo remains available.')
    if expected and not hmac.compare_digest(str(entered_code).encode(), expected.encode()):
        raise ValueError('Enter the evaluator access code to run Gemini AI.')
