from app.services.telemetry_ingestion___validation import TelemetryIngestionValidationService

def test_telemetry_ingestion___validation_execution():
    service = TelemetryIngestionValidationService()
    result = service.execute()
    assert result["status"] == "success"
    assert result["task"] == "Telemetry Ingestion & Validation"
