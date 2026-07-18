import pytest
from app.services.llm_narrator import LLMNarrator

@pytest.fixture
def narrator():
    return LLMNarrator()

@pytest.fixture
def mock_facts():
    return {
        "alert_id": 105,
        "primary_bottleneck": {
            "category": "CPU Bound",
            "severity": 0.85
        },
        "top_processes": [
            {
                "pid": 1024,
                "name": "python3",
                "cpu_percent": 85.5
            },
            {
                "pid": 5001,
                "name": "node",
                "cpu_percent": 15.2
            }
        ],
        "system_snapshot": {
            "load_avg_1": 4.5
        }
    }

def test_valid_output(narrator, mock_facts):
    # Output only uses PIDs, names, and numbers that exist in facts
    valid_narration = 'The system is "CPU Bound" due to process "python3" (PID 1024) consuming 85.5% CPU. Another factor is "node" using 15.2% CPU.'
    assert narrator.validate_narration(valid_narration, mock_facts) is True

def test_fabricated_pid(narrator, mock_facts):
    # Output uses PID 9999 which is not in facts
    invalid_narration = 'Process "python3" (PID 9999) is consuming too much CPU.'
    assert narrator.validate_narration(invalid_narration, mock_facts) is False

def test_fabricated_percentage(narrator, mock_facts):
    # Output uses 99.9% which is not in facts
    invalid_narration = 'The "python3" process is using 99.9% CPU.'
    assert narrator.validate_narration(invalid_narration, mock_facts) is False

def test_fabricated_process_name(narrator, mock_facts):
    # Output uses a quoted string that is not in facts
    invalid_narration = 'The system is slow because "malware.exe" is running.'
    assert narrator.validate_narration(invalid_narration, mock_facts) is False

def test_empty_response(narrator, mock_facts):
    # Empty response should be invalid
    assert narrator.validate_narration("", mock_facts) is False
    assert narrator.validate_narration(None, mock_facts) is False

def test_valid_decimal_numbers(narrator, mock_facts):
    # Test decimal numbers existing in the facts
    valid_narration = 'Load average is 4.5 and severity is 0.85.'
    assert narrator.validate_narration(valid_narration, mock_facts) is True
