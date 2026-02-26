from datetime import datetime
from typing import List, Dict, Set
from collections import defaultdict

from app.domain.models import Incident, ProcessStats
from app.utils.logger import logger
from app.utils.normalizar import normalizar


class IncidentProcessor:
    """Processa incidentes recebidos do Zabbix e aplica regras de negócios."""

    def __init__(
        self,
        allowed_groups: List[str],
        allowed_prefixes: List[str],
        dre_map: Dict[str, str],
        min_severity: int
    ):
        self.allowed_groups = [normalizar(g) for g in allowed_groups]
        self.allowed_prefixes = [normalizar(p) for p in allowed_prefixes]
        self.dre_map = {normalizar(k): v for k, v in dre_map.items()}
        self.min_severity = min_severity

    # ---------------------------------------
    # ATUALIZA STATUS BASEADO NO ZABBIX
    # ---------------------------------------
    def sincronizar_status(
        self,
        eventos: List[dict],
        recovery_map: Dict[str, str],
        eventids_por_dre: Dict[str, Set[str]]) -> Dict[str, List[Tuple[str, int, str]]]:
        """
        Atualiza status dos incidentes de acordo com o Zabbix.
        Somente marca como resolvido se o Zabbix realmente indicar resolução.
        """

        resultado = defaultdict(list)

        eventos_map = {str(ev["eventid"]): ev for ev in eventos}

        for dre, ids_planilha in eventids_por_dre.items():
            for eid in ids_planilha:

                ev = eventos_map.get(eid)

                # 🔹 Evento não retornado pelo Zabbix → mantém status atual (não altera)
                if not ev:
                    continue

                value = int(ev.get("value", 0))

                if value == 0:
                    # Ativo no Zabbix → status 0, sem data de resolução
                    resultado[dre].append((eid, 0, ""))
                    continue

                # Verifica se tem r_eventid ou recovery_map
                recovery_clock = ev.get("r_clock") or recovery_map.get(str(ev.get("r_eventid", "")))

                if recovery_clock:
                    data_resolucao = datetime.fromtimestamp(int(recovery_clock)).strftime("%d/%m/%Y %H:%M:%S")
                    resultado[dre].append((eid, 1, data_resolucao))
                else:
                    # Se não houver informação de resolução, não marca como resolvido
                    continue

        return dict(resultado)
    

    # ---------------------------------------
    # PROCESSA NOVOS INCIDENTES
    # ---------------------------------------
    def process(
        self,
        problems: List[dict],
        event_host_map: Dict[str, str],
        hosts_map: Dict[str, dict],
        existing_event_ids: Dict[str, Set[str]],
        stats: ProcessStats
    ) -> Dict[str, List[Incident]]:
        """
        Processa problemas ativos do Zabbix e filtra novos incidentes
        de acordo com grupo, prefixo e severidade.
        """

        incidents_by_dre: Dict[str, List[Incident]] = {}

        for p in problems:
            eventid = str(p["eventid"])
            severity = int(p["severity"])

            # 🔹 Filtro severidade
            if severity < self.min_severity:
                stats.ignorados_severidade += 1
                logger.debug(f"Ignorado {eventid}: severidade {severity} < {self.min_severity}")
                continue

            # 🔹 Filtra host
            hostid = event_host_map.get(eventid)
            if not hostid or hostid not in hosts_map:
                stats.ignorados_host_nao_encontrado += 1
                logger.debug(f"Ignorado {eventid}: host não encontrado")
                continue

            host_info = hosts_map[hostid]
            host = host_info["name"]
            grupos = [normalizar(g) for g in host_info["groups"]]

            # 🔹 Filtro grupo permitido
            if not any(g in self.allowed_groups for g in grupos):
                stats.ignorados_grupo += 1
                logger.debug(f"Ignorado {eventid}: grupo(s) {grupos} não permitido(s)")
                continue

            # 🔹 Filtro prefixo do host
            host_upper = normalizar(host)
            if not any(host_upper.startswith(prefix) for prefix in self.allowed_prefixes):
                stats.ignorados_prefixo += 1
                logger.debug(f"Ignorado {eventid}: prefixo {host_upper} não permitido")
                continue

            # 🔹 Determinar DRE
            municipio = normalizar(host.split("-")[-1].strip())
            dre = self.dre_map.get(municipio, "DRE - OUTROS")

            # 🔹 Evitar duplicados
            event_ids = existing_event_ids.setdefault(dre, set())
            if eventid in event_ids:
                stats.ignorados_duplicados += 1
                logger.debug(f"Ignorado {eventid}: já existe na DRE {dre}")
                continue
            event_ids.add(eventid)
            stats.novos += 1

            # 🔹 Criar objeto Incident
            data = datetime.fromtimestamp(int(p["clock"]))
            incident = Incident(
                event_id=eventid,
                data=data,
                host=host,
                municipio=municipio,
                descricao=p["name"],
                severidade=severity,
                dre=dre,
                status=0,                # Status inicial = ativo
                data_resolucao=""         # Sem data de resolução ainda
            )

            incidents_by_dre.setdefault(dre, []).append(incident)

        total_incidentes = sum(len(v) for v in incidents_by_dre.values())
        logger.info(f"📈 Total de incidentes processados: {total_incidentes}")
        logger.info(f"📈 Novos incidentes adicionados: {stats.novos}")
        return incidents_by_dre