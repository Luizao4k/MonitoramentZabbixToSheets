from app.application.incident_orchestrator import IncidentOrchestrator
from app.config.settings import Settings


def main() -> None:
    settings = Settings()
    orchestrator = IncidentOrchestrator(settings)
    orchestrator.run()
    


if __name__ == "__main__":
    main()