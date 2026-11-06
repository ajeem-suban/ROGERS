from app.services.core_domain_model___crud_apis import CoreDomainModelCrudApisService

def test_core_domain_model___crud_apis_execution():
    service = CoreDomainModelCrudApisService()
    result = service.execute()
    assert result["status"] == "success"
    assert result["task"] == "Core Domain Model & CRUD APIs"
