from app.infrastructure.zabbix_service import (
    ZabbixService,
    ZabbixConnectionError
)
from app.infrastructure.google_sheets_service import GoogleSheetsService
from app.config.settings import Settings
from app.utils.logger import logger
from app.domain.incident_processor import IncidentProcessor
from app.domain.models import ProcessStats


class IncidentOrchestrator:
    """Orquestra coleta, processamento e atualização de incidentes
    entre Zabbix e Google Sheets. Zabbix é autoridade sobre status resolvido.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.zabbix = ZabbixService(settings=self.settings)
        self.sheets = GoogleSheetsService(settings=self.settings)
        self.processor = IncidentProcessor(
            allowed_groups=self.settings.allowed_groups,
            allowed_prefixes=self.settings.allowed_prefixes,
            dre_map=self.settings.dre_map,
            min_severity=self.settings.min_severity
        )

    # --------------------------------------------------
    # EXECUÇÃO PRINCIPAL
    # --------------------------------------------------

    def run(self) -> None:
        logger.info("🚀 Iniciando processamento de incidentes...")
        stats = ProcessStats()

        # 🔹 1. Buscar problemas ativos no Zabbix (value=0 → ativo)
        try:
            problems = self.zabbix.get_active_problems()
        except ZabbixConnectionError as e:
            logger.error(f"❌ Falha ao conectar no Zabbix: {e}")
            return

        stats.total_recebidos = len(problems)
        if not problems:
            logger.info("⚠ Nenhum incidente ativo encontrado.")
            return

        logger.info(f"🔎 Incidentes ativos encontrados: {len(problems)}")

        # 🔹 2. Mapear eventos → hostid
        event_ids = [p["eventid"] for p in problems]
        events = self.zabbix.get_events(event_ids)
        event_host_map = {
            ev["eventid"]: ev["hosts"][0]["hostid"]
            for ev in events if ev.get("hosts")
        }

        # 🔹 3. Mapear hosts → nome + grupos
        hostids = list(set(event_host_map.values()))
        hosts = self.zabbix.get_hosts(hostids)
        hosts_map = {
            h["hostid"]: {
                "name": h["name"],
                "groups": [g["name"] for g in h["groups"]]
            }
            for h in hosts
        }

        # 🔹 4. Buscar event_ids existentes na planilha
        eventids_planilha = self.sheets.get_all_event_ids()

        # 🔹 5. Processar novos incidentes
        novos_por_dre = self.processor.process(
            problems=problems,
            event_host_map=event_host_map,
            hosts_map=hosts_map,
            existing_event_ids=eventids_planilha,
            stats=stats
        )

        # 🔹 6. Detectar resolvidos no Zabbix (autoridade)
        todos_eventids = [
            eid
            for eventids in eventids_planilha.values()
            for eid in eventids
        ]

        resolvidos_por_dre = {}
        if todos_eventids:
            # 🔹 Buscar eventos existentes no Zabbix
            eventos = self.zabbix.get_events_by_ids(todos_eventids)

            # 🔹 Extrair recovery events para pegar data de resolução
            recovery_ids = [
                ev["r_eventid"]
                for ev in eventos
                if ev.get("r_eventid")
            ]

            recovery_map = {}
            if recovery_ids:
                recovery_events = self.zabbix.get_events_by_ids(recovery_ids)
                recovery_map = {
                    ev["eventid"]: ev["clock"]
                    for ev in recovery_events
                }

            # 🔹 Atualizar status de cada incidente baseado no Zabbix
            resolvidos_por_dre = self.processor.sincronizar_status(
                eventos=eventos,
                recovery_map=recovery_map,
                eventids_por_dre=eventids_planilha
            )

        stats.atualizados = sum(len(lista) for lista in resolvidos_por_dre.values())

        # 🔹 7. Escrever novos incidentes na planilha
        if novos_por_dre:
            self.sheets.append_incidents(novos_por_dre)

        # 🔹 8. Atualizar status resolvido na planilha
        if resolvidos_por_dre:
            self.sheets.sincronizar_status_planilha(resolvidos_por_dre)

        # 🔹 9. Log final consolidado
        logger.info("📊 ===== RELATÓRIO FINAL =====")
        logger.info(f"🔎 Total recebidos: {stats.total_recebidos}")
        logger.info(f"🆕 Novos: {stats.novos}")
        logger.info(f"🔁 Atualizados (resolvidos): {stats.atualizados}")
        logger.info(f"🚫 Ignorados: {stats.total_ignorados()}")
        logger.info("----- Detalhamento Ignorados -----")
        logger.info(f" - Severidade: {stats.ignorados_severidade}")
        logger.info(f" - Grupo: {stats.ignorados_grupo}")
        logger.info(f" - Prefixo: {stats.ignorados_prefixo}")
        logger.info(f" - Duplicados: {stats.ignorados_duplicados}")
        logger.info(f" - Host não encontrado: {stats.ignorados_host_nao_encontrado}")
        logger.info("===================================")