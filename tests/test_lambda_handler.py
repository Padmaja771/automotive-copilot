"""
Automotive Copilot: Unit Tests
===============================
Industry standard pytest script.
Tests our AWS Lambda S3 event validation logic to ensure
bad files (like .exe or massive files) are rejected securely.
"""

import pytest
import sys
import os

# Ensure the lambda directory is in the path to import the handler
sys.path.append(os.path.join(os.path.dirname(__file__), '../infrastructure/terraform/lambda'))

from handler import validate_s3_event

def test_validate_s3_event_success():
    # Mock a standard S3 put event matching our expected format
    mock_event = {
        "s3": {
            "bucket": {"name": "automotive-copilot-vehicle-docs-dev"},
            "object": {"key": "incoming/manual.pdf", "size": 1048576} # 1MB
        }
    }
    
    result = validate_s3_event(mock_event)
    
    assert result["extension"] == ".pdf"
    assert result["bucket"] == "automotive-copilot-vehicle-docs-dev"
    assert result["size_mb"] == 1.0
    assert result["filename"] == "manual.pdf"

def test_validate_s3_event_rejects_bad_extension():
    # Security test: ensure .docx or malicious files are blocked
    mock_event_bad_ext = {
        "s3": {
            "bucket": {"name": "automotive-copilot-vehicle-docs-dev"},
            "object": {"key": "incoming/virus.exe", "size": 1024}
        }
    }
    
    with pytest.raises(ValueError, match="unsupported extension"):
        validate_s3_event(mock_event_bad_ext)

def test_validate_s3_event_rejects_massive_files():
    # Cost-control test: ensure files larger than 50MB (our limit) are blocked
    mock_event_large = {
        "s3": {
            "bucket": {"name": "automotive-copilot-vehicle-docs-dev"},
            "object": {"key": "incoming/massive_manual.pdf", "size": 104857600} # 100MB
        }
    }
    
    with pytest.raises(ValueError, match="exceeds 50MB limit"):
        validate_s3_event(mock_event_large)
