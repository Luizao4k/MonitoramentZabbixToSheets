import pytest
from app.infrastructure.zabbix_service import ZabbixService
from app.config.settings import Settings


@pytest.mark.integration
def test_busca_problemas():
    settings = Settings()


    service = ZabbixService(settings=settings)


    problems = service.get_active_problems()

    assert isinstance(problems, list)
