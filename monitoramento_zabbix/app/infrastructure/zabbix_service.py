from pyzabbix.api import ZabbixAPI, ZabbixAPIException
from app.config.settings import Settings
from app.utils.logger import logger

class ZabbixConnectionError(Exception):
    """Erro de conexão com o Zabbix."""
    pass

class ZabbixService:

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.zapi: ZabbixAPI | None = None
        self._conectar()

    def _conectar(self) -> None:
        try:
            self.zapi = ZabbixAPI(self.settings.zabbix_url, timeout=30)
            self.zapi.login(api_token=self.settings.zabbix_token)
            logger.info(f"✅ Conectado ao Zabbix: {self.settings.zabbix_url}")

        except ZabbixAPIException as e:
            raise ZabbixConnectionError(
                f"Erro de autenticação/API no Zabbix: {e}"
            ) from e

        except Exception as e:
            raise ZabbixConnectionError(
                f"Erro de conexão (Rede/Proxy): {e}"
            ) from e
                    
    # -----------------------------

    def get_active_problems(self) -> list[dict]:
        if not self.zapi:
            raise ZabbixConnectionError("Zabbix API não inicializada.")

        return self.zapi.event.get(
            output=["eventid", "name", "severity", "clock", "value"],
            value=0,
            sortfield="eventid",
            sortorder="DESC"
        )

    # -----------------------------

    def get_events_by_ids(self, event_ids: list[str]) -> list[dict]:
        if not event_ids:
            return []

        try:
            return self.zapi.event.get(
                eventids=[int(e) for e in event_ids 
                if str(e).strip().isdigit()],
                output=[
                    "eventid",
                    "clock",
                    "value",
                    "r_eventid"
                ]
            )
        except ZabbixAPIException as e:
            logger.exception("Erro ao buscar eventos por ID")
            raise
    # -----------------------------

    def get_recovery_events(self, recovery_ids: list[str]) -> list[dict]:
        if not recovery_ids:
            return []

        return self.zapi.event.get(
            eventids=[int(e) for e in recovery_ids],
            output=[
                "eventid",
                "clock"
            ]
        )

    # -----------------------------

    def get_events(self, event_ids: list[str]) -> list[dict]:
        if not event_ids:
            return []

        return self.zapi.event.get(
            eventids=event_ids,
            output=["eventid"],
            selectHosts="extend"
        )

    # -----------------------------

    def get_hosts(self, hostids: list[str]) -> list[dict]:
        if not hostids:
            return []

        return self.zapi.host.get(
            hostids=hostids,
            output=["name"],
            selectGroups=["name"]
        )