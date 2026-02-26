from dataclasses import dataclass
from datetime import datetime


@dataclass
class Incident:
    event_id: str
    data: datetime
    host: str
    municipio: str
    descricao: str
    severidade: int
    dre: str
    status: int = 0
    data_resolucao: str = ""

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "data": self.data.strftime("%d/%m/%Y %H:%M:%S"),
            "host": self.host,
            "municipio": self.municipio,
            "descricao": self.descricao,
            "severidade": self.severidade,
            "dre": self.dre,
            "status": self.status,
            "data_resolucao": self.data_resolucao,
        }


@dataclass
class ProcessStats:
    total_recebidos: int = 0
    novos: int = 0
    atualizados: int = 0

    ignorados_severidade: int = 0
    ignorados_grupo: int = 0
    ignorados_prefixo: int = 0
    ignorados_duplicados: int = 0
    ignorados_host_nao_encontrado: int = 0

    def total_ignorados(self) -> int:
        return (
            self.ignorados_severidade
            + self.ignorados_grupo
            + self.ignorados_prefixo
            + self.ignorados_duplicados
            + self.ignorados_host_nao_encontrado
        )

    def total_processados(self) -> int:
        return self.novos + self.atualizados
