"""
license_manager.py

Responsável por obter textos oficiais de licenças a partir da fonte
canônica da SPDX (https://spdx.org/licenses/{licenseId}.json) e gerar
o arquivo LICENSE dentro do projeto criado pelo FolderGEN.

Este módulo NUNCA embute textos de licença no código-fonte. Em vez
disso, busca o texto oficial em tempo de execução (com cache local
opcional) usando apenas a biblioteca padrão do Python.

Fonte de dados:
    https://spdx.org/licenses/{licenseId}.json

    Esse é o endpoint oficial do projeto SPDX (Software Package Data
    Exchange, mantido pela Linux Foundation) para acessar os detalhes
    de uma licença da SPDX License List. O campo relevante da resposta
    é "licenseText", que contém o texto completo e oficial da licença.

Segurança:
    * O SPDX ID é sempre validado contra uma lista fixa e permitida
      (ALLOWED_LICENSES) antes de qualquer requisição.
    * A URL é sempre construída a partir de SPDX_API_BASE_URL + um ID
      validado; nenhuma URL arbitrária fornecida pelo usuário é aceita.
    * Nenhum conteúdo baixado é executado; é tratado exclusivamente
      como texto.
    * Requisições têm timeout definido.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# URL base oficial da SPDX para detalhes de licença em JSON.
# A URL final é sempre SPDX_API_BASE_URL + "<SPDX_ID>.json", nunca uma
# URL fornecida externamente.
SPDX_API_BASE_URL = "https://spdx.org/licenses/"

# Timeout razoável para uma requisição HTTP simples de um arquivo JSON
# pequeno.
REQUEST_TIMEOUT_SECONDS = 10

# Lista de licenças suportadas pelo FolderGEN. A chave é o rótulo usado
# na CLI; o valor é o SPDX ID oficial. Esta é a ÚNICA fonte de IDs
# aceitos — qualquer ID fora deste dicionário é rejeitado antes de
# qualquer requisição de rede.
SUPPORTED_LICENSES: dict[str, str] = {
    "MIT": "MIT",
    "Apache License 2.0": "Apache-2.0",
    "GNU GPLv2": "GPL-2.0-only",
    "GNU GPLv3": "GPL-3.0-only",
    "BSD 3-Clause": "BSD-3-Clause",
    "The Unlicense": "Unlicense",
}

# Conjunto de SPDX IDs permitidos, derivado de SUPPORTED_LICENSES.
# Usado para validar qualquer ID antes de montar a URL de requisição.
ALLOWED_SPDX_IDS: frozenset[str] = frozenset(SUPPORTED_LICENSES.values())

# Placeholders que o FolderGEN sabe substituir, e a que padrões da SPDX
# eles correspondem no texto original da licença.
#
# A SPDX usa convenções como "<year>" e "<copyright holders>" dentro do
# licenseText (ex.: MIT, BSD-3-Clause). O FolderGEN normaliza isso para
# os placeholders internos "{year}" e "{author}" ANTES de fazer a
# substituição final, e só substitui o que de fato existir no texto.
_SPDX_YEAR_MARKERS = ("<year>",)
_SPDX_AUTHOR_MARKERS = (
    "<copyright holders>",
    "<name of author>",
    "<owner>",
)


class LicenseError(Exception):
    """
    Erro levantado quando uma licença não pôde ser obtida ou gerada.

    Sempre inclui, na mensagem, qual licença falhou, para que a CLI
    possa informar isso claramente ao usuário.
    """


@dataclass
class LicenseResult:
    """Resultado de uma operação de obtenção/geração de licença."""

    spdx_id: str
    text: str
    from_cache: bool


def list_available_licenses() -> dict[str, str]:
    """
    Retorna o mapeamento {rótulo amigável: SPDX ID} das licenças
    suportadas pelo FolderGEN, na ordem em que devem ser exibidas.
    """
    return dict(SUPPORTED_LICENSES)


def get_license_text(
    spdx_id: str,
    cache_dir: Optional[Path] = None,
) -> LicenseResult:
    """
    Obtém o texto oficial de uma licença, identificada pelo seu SPDX
    ID, usando o cache local quando disponível e, caso contrário,
    buscando na SPDX.

    Levanta LicenseError se o SPDX ID não for permitido, se a licença
    não puder ser obtida (rede indisponível, timeout, erro HTTP, JSON
    inválido) e o cache também não tiver uma cópia válida.

    `cache_dir`, se fornecido, é o diretório onde os textos em cache
    são lidos/gravados (um arquivo "<spdx_id>.txt" por licença). O
    cache é totalmente opcional: se `cache_dir` for None, a busca
    sempre vai direto à SPDX.
    """
    _validate_spdx_id(spdx_id)

    if cache_dir is not None:
        cached_text = _read_from_cache(spdx_id, cache_dir)
        if cached_text is not None:
            return LicenseResult(
                spdx_id=spdx_id, text=cached_text, from_cache=True
            )

    text = _fetch_from_spdx(spdx_id)

    if cache_dir is not None:
        _write_to_cache(spdx_id, text, cache_dir)

    return LicenseResult(spdx_id=spdx_id, text=text, from_cache=False)


def render_license_text(
    raw_text: str,
    author: Optional[str] = None,
    year: Optional[str] = None,
) -> str:
    """
    Substitui os placeholders de autor/ano no texto bruto da licença
    (conforme retornado pela SPDX), apenas quando eles de fato
    existirem no texto. Se um marcador não existir, o texto não é
    alterado nesse ponto.
    """
    rendered = raw_text

    if _contains_any(rendered, _SPDX_YEAR_MARKERS):
        effective_year = year or str(datetime.now(timezone.utc).year)
        for marker in _SPDX_YEAR_MARKERS:
            rendered = rendered.replace(marker, effective_year)

    if _contains_any(rendered, _SPDX_AUTHOR_MARKERS) and author:
        for marker in _SPDX_AUTHOR_MARKERS:
            rendered = rendered.replace(marker, author)

    return rendered


def generate_license_file(
    spdx_id: str,
    destination_dir: Path,
    author: Optional[str] = None,
    year: Optional[str] = None,
    cache_dir: Optional[Path] = None,
    confirm_overwrite: Optional[callable] = None,
) -> Optional[Path]:
    """
    Busca o texto da licença e escreve o arquivo LICENSE dentro de
    `destination_dir` (a pasta raiz do projeto já criado).

    Se já existir um LICENSE em `destination_dir` e `confirm_overwrite`
    não for fornecido ou retornar False, o arquivo existente NÃO é
    sobrescrito e a função retorna None.

    Levanta LicenseError se a licença não puder ser obtida — nesse
    caso, nenhum arquivo é criado ou alterado (nunca gera um LICENSE
    parcial/incompleto).
    """
    _validate_spdx_id(spdx_id)

    result = get_license_text(spdx_id, cache_dir=cache_dir)
    rendered_text = render_license_text(
        result.text, author=author, year=year
    )

    license_path = destination_dir / "LICENSE"

    if license_path.exists():
        should_overwrite = bool(confirm_overwrite) and confirm_overwrite(
            license_path
        )
        if not should_overwrite:
            return None

    license_path.write_text(rendered_text, encoding="utf-8")
    return license_path


def _validate_spdx_id(spdx_id: str) -> None:
    """
    Garante que `spdx_id` está na lista de licenças explicitamente
    permitidas pelo FolderGEN. Isso impede que qualquer entrada externa
    force uma requisição para um ID (e, portanto, uma URL) arbitrário.
    """
    if spdx_id not in ALLOWED_SPDX_IDS:
        raise LicenseError(
            f"SPDX ID '{spdx_id}' não está na lista de licenças "
            "permitidas pelo FolderGEN."
        )


def _fetch_from_spdx(spdx_id: str) -> str:
    """
    Faz a requisição HTTP para a SPDX e retorna o texto bruto da
    licença (campo "licenseText" do JSON).

    A URL é sempre construída internamente a partir de
    SPDX_API_BASE_URL + spdx_id (já validado) — nunca a partir de uma
    URL externa.
    """
    url = f"{SPDX_API_BASE_URL}{spdx_id}.json"

    try:
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(
            request, timeout=REQUEST_TIMEOUT_SECONDS
        ) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise LicenseError(
                    f"Não foi possível obter a licença '{spdx_id}': "
                    f"a SPDX respondeu com status HTTP {status}."
                )
            raw_body = response.read()
    except urllib.error.HTTPError as exc:
        raise LicenseError(
            f"Não foi possível obter a licença '{spdx_id}': erro HTTP "
            f"{exc.code} ao consultar a SPDX."
        ) from exc
    except urllib.error.URLError as exc:
        raise LicenseError(
            f"Não foi possível obter a licença '{spdx_id}': falha de "
            f"rede ao consultar a SPDX ({exc.reason})."
        ) from exc
    except TimeoutError as exc:
        raise LicenseError(
            f"Não foi possível obter a licença '{spdx_id}': tempo "
            "limite excedido ao consultar a SPDX."
        ) from exc

    try:
        data = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LicenseError(
            f"Não foi possível obter a licença '{spdx_id}': resposta "
            "da SPDX não é um JSON válido."
        ) from exc

    license_text = data.get("licenseText")
    if not license_text or not isinstance(license_text, str):
        raise LicenseError(
            f"Não foi possível obter a licença '{spdx_id}': a resposta "
            "da SPDX não contém o campo 'licenseText'."
        )

    return license_text


def _cache_file_path(spdx_id: str, cache_dir: Path) -> Path:
    return cache_dir / f"{spdx_id}.txt"


def _read_from_cache(spdx_id: str, cache_dir: Path) -> Optional[str]:
    """
    Tenta ler o texto da licença a partir do cache local. Retorna
    None se o cache não existir ou não puder ser lido (o cache nunca
    é obrigatório: qualquer falha aqui simplesmente leva à busca na
    SPDX).
    """
    cache_path = _cache_file_path(spdx_id, cache_dir)
    if not cache_path.is_file():
        return None

    try:
        return cache_path.read_text(encoding="utf-8")
    except OSError:
        return None


def _write_to_cache(spdx_id: str, text: str, cache_dir: Path) -> None:
    """
    Grava o texto da licença no cache local. Falhas ao gravar o cache
    (permissão, disco cheio, etc.) são silenciosamente ignoradas: o
    cache é apenas uma otimização e nunca deve impedir a geração do
    LICENSE.
    """
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = _cache_file_path(spdx_id, cache_dir)
        cache_path.write_text(text, encoding="utf-8")
    except OSError:
        pass


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)
