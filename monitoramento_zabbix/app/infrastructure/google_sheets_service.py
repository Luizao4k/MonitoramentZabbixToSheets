import gspread
from gspread import Spreadsheet
from oauth2client.service_account import ServiceAccountCredentials
from app.domain.models import Incident
from app.config.settings import Settings
from app.utils.logger import logger
from datetime import datetime
import sys


class GoogleSheetsService:
    """Gerencia leitura e escrita de incidentes no Google Sheets."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.expected_dres = settings.expected_dres

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]

        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                "secrets/service_account.json",
                scope
            )
            client: gspread.Client = gspread.authorize(creds)
            self.spreadsheet: Spreadsheet = client.open(self.settings.spreadsheet_name)
            logger.info("✅ Conectado ao Google Sheets")
        except Exception:
            logger.exception("❌ Falha crítica ao conectar ao Google Sheets")
            raise

    # -----------------------------
    # Estrutura
    # -----------------------------
    def _load_worksheets(self) -> dict[str, gspread.Worksheet]:
        try:
            return {ws.title: ws for ws in self.spreadsheet.worksheets()}
        except Exception:
            logger.exception("❌ Erro ao carregar worksheets")
            raise

    def ensure_structure(self) -> dict[str, gspread.Worksheet]:
        """Garante que todas as abas esperadas existam"""
        try:
            worksheets = self._load_worksheets()
            if "_TEMPLATE" not in worksheets:
                raise ValueError("A aba '_TEMPLATE' não foi encontrada.")
            template = worksheets["_TEMPLATE"]

            for dre in self.expected_dres:
                if dre not in worksheets:
                    new_sheet = template.copy_to(self.spreadsheet.id)
                    new_ws = self.spreadsheet.get_worksheet_by_id(new_sheet["sheetId"])
                    new_ws.update_title(dre)
                    worksheets[dre] = new_ws

            return worksheets
        except Exception:
            logger.exception("❌ Falha ao garantir estrutura da planilha")
            raise

    # -----------------------------
    # Sanitização
    # -----------------------------
    def _sanitize_value(self, value):
        if isinstance(value, datetime):
            return value.strftime("%d/%m/%Y %H:%M:%S")
        if value is None:
            return ""
        return value

    def _sanitize_rows(self, rows):
        return [
            [self._sanitize_value(value) for value in row]
            for row in rows
        ]

    # -----------------------------
    # Leitura
    # -----------------------------
    def get_all_event_ids(self) -> dict[str, set[str]]:
        """Retorna todos os event_ids por DRE"""
        try:
            worksheets = self._load_worksheets()
            eventids_por_dre: dict[str, set[str]] = {}
            for dre in self.expected_dres:
                ws = worksheets.get(dre)
                if not ws:
                    eventids_por_dre[dre] = set()
                    continue
                col_eventids = ws.col_values(1)[1:]
                eventids_por_dre[dre] = {eid.strip() for eid in col_eventids if eid and eid.strip().isdigit()}
            return eventids_por_dre
        except Exception:
            logger.exception("❌ Falha ao obter todos os EVENT_IDs")
            raise

    # -----------------------------
    # Escrita de novos incidentes
    # -----------------------------
    def append_incidents(self, incidents_by_dre: dict[str, list[Incident]]) -> None:
        worksheets = self.ensure_structure()
        for dre, incidents in incidents_by_dre.items():
            if not incidents:
                continue
            ws = worksheets[dre]
            rows = [
                [
                    inc.event_id,
                    inc.data.strftime("%d/%m/%Y %H:%M:%S"),
                    inc.host,
                    inc.municipio,
                    inc.descricao,
                    inc.severidade,
                    0,      # Status inicial = ativo
                    ""      # Data de resolução vazia
                ]
                for inc in incidents
            ]
            ws.append_rows(self._sanitize_rows(rows), value_input_option="USER_ENTERED")

    # -----------------------------
    # Atualização de status resolvido
    # -----------------------------
    def sincronizar_status_planilha(
    self,
    atualizacoes: dict[str, list[tuple[str, int, str]]]) -> None:

        try:
            worksheets = self._load_worksheets()

            for dre, eventos in atualizacoes.items():

                if dre not in self.expected_dres:
                    logger.error(f"❌ DRE inválida recebida: {dre}")
                    raise ValueError(f"DRE inválida recebida: {dre}")

                if not eventos:
                    continue

                ws = worksheets.get(dre)

                if not ws:
                    logger.warning(f"⚠ Aba não encontrada ao atualizar resolvidos: {dre}")
                    continue

                # 🔹 Lê toda a aba de A até H (ou até coluna necessária)
                # Evita múltiplas chamadas de col_values
                todas_linhas = ws.get("A2:H")  # ignora header
                if not todas_linhas:
                    todas_linhas = []

                # 🔹 Mapear EVENT_ID → índice da linha no Google Sheets
                mapa_linhas = {linha[0].strip(): idx + 2 for idx, linha in enumerate(todas_linhas) if linha}

                # 🔹 Atualizações em memória
                updates = []

                for event_id, novo_status, data_resolucao in eventos:
                    row = mapa_linhas.get(str(event_id))
                    if not row:
                        continue

                    # 🔹 Evita sobrescrever se já estiver resolvido
                    status_atual = todas_linhas[row - 2][6] if len(todas_linhas[row - 2]) > 6 else ""
                    if str(status_atual) == "1":
                        continue

                    updates.append({
                        "range": f"G{row}:H{row}",
                        "values": [[novo_status, data_resolucao]]
                    })

                    # Atualiza em memória para referência interna
                    if len(todas_linhas[row - 2]) < 8:
                        # garante que existam 8 colunas
                        todas_linhas[row - 2] += [""] * (8 - len(todas_linhas[row - 2]))
                    todas_linhas[row - 2][6] = str(novo_status)
                    todas_linhas[row - 2][7] = data_resolucao

                # 🔹 Envia todas as atualizações em batch
                if updates:
                    ws.batch_update(updates, value_input_option="USER_ENTERED")
                    logger.info(f"✅ {len(updates)} incidentes atualizados como resolvidos em {dre}")

            logger.info("✅ Atualização de resolvidos concluída.")

        except Exception:
            logger.exception("❌ Falha ao atualizar status de resolvidos")
            raise