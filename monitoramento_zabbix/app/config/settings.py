import os
import json
from pathlib import Path
from dotenv import load_dotenv
from typing import Any

# app/config/
CURRENT_DIR = Path(__file__).resolve().parent

#A raiz do projeto (sobe dois níveis: de 'config' para 'app', de 'app' para a raiz)
BASE_DIR = CURRENT_DIR.parent.parent

#caminho arquivos JSON 
CONFIG_DIR = CURRENT_DIR

#Localização do .env 

env_path = BASE_DIR / ".env"
if not env_path.exists():
    raise FileNotFoundError(".env não encontrado na raiz do projeto")
load_dotenv(env_path)


class Settings:
    
    def __init__(self) -> None:


        # ---------- ENV ----------
        self.zabbix_url: str = self._get_env("ZABBIX_URL")
        self.zabbix_token: str = self._get_env("ZABBIX_TOKEN")
        self.spreadsheet_name: str = self._get_env("SPREADSHEET_NAME")
        self.google_creds: Path = BASE_DIR / self._get_env("GOOGLE_CREDS")

        # ---------- JSON ----------
        self.allowed_groups: list[str] = self._load_json(
            self._config_path("config_groups.json"),
            "allowed_groups"
        )

        self.allowed_prefixes: list[str] = self._load_json(
            self._config_path("config_groups.json"),
            "allowed_prefixes"
        )

        self.dre_map: dict[str, str] = self._load_json_full(
            self._config_path("dre_map.json")
        )

        # Derivação automática (fonte única de verdade)
        self.expected_dres: list[str] = sorted(set(self.dre_map.values()))

        self.min_severity: int = self._load_json(
            self._config_path("config_severity.json"),
            "min_severity",
            default=0
        )


    # ==================================================
    # HELPERS
    # ==================================================

    def _get_env(self, key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise RuntimeError(f"Variável de ambiente não definida: {key}")
        return value

    # -----------------------------

    def _config_path(self, file: str) -> Path:
        return CONFIG_DIR / file

    # -----------------------------

    def _load_json(self, file: Path, key: str, default=None):
        try:
            with open(file, encoding="utf-8") as f:
                data = json.load(f)
            return data.get(key, default)
        except FileNotFoundError:
            raise RuntimeError(f"Arquivo de config não encontrado: {file}")
        except json.JSONDecodeError:
            raise RuntimeError(f"JSON inválido em {file}")

    # -----------------------------

    def _load_json_full(self, file: Path):
        try:
            with open(file, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise RuntimeError(f"Arquivo de config não encontrado: {file}")
        except json.JSONDecodeError:
            raise RuntimeError(f"JSON inválido em {file}")