import unicodedata


def normalizar(texto: str) -> str:
    """
    Normaliza um texto para comparação:
    - Maiúsculas
    - Remove acentos
    - Remove espaços extras
    """
    if not texto:
        return ""
    texto = texto.upper().strip()
    texto = "".join(c for c in unicodedata.normalize("NFD", texto)
                    if unicodedata.category(c) != "Mn")
    return texto

