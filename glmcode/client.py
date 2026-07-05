"""Client HTTP pour l'API Z.ai (endpoint compatible OpenAI).

Gere le streaming en Server-Sent Events et le tool-calling (function calling).
Aucune dependance lourde : uniquement `requests`.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Callable

import requests

from .config import Config

# Codes d'erreur Z.ai transitoires : rate limit / service surcharge.
_RETRYABLE_CODES = {"1302", "1305"}


class LLMError(RuntimeError):
    pass


class LLMCancelled(Exception):
    """L'utilisateur a interrompu la requete en cours (Ctrl+C)."""


class _ApiError(Exception):
    """Erreur HTTP d'un appel modele, avec info sur sa nature (retryable ou non)."""

    def __init__(self, status: int, code, detail: str, retryable: bool):
        super().__init__(detail)
        self.status = status
        self.code = code
        self.detail = detail
        self.retryable = retryable


class LLMClient:
    # Compteur global de requetes HTTP envoyees (tous modeles confondus).
    request_count = 0

    def __init__(self, config: Config):
        self.config = config
        self._session = requests.Session()
        self._free_models = self._load_free_models()

    def _load_free_models(self) -> list[str]:
        """Charge la liste des modèles gratuits depuis model_coder_free.txt."""
        try:
            models_file = Path(__file__).parent.parent / "model" / "model_coder_free.txt"
            if models_file.exists():
                with models_file.open("r", encoding="utf-8") as f:
                    return [line.strip() for line in f if line.strip()]
        except Exception:
            pass
        return []

    @property
    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _url(self) -> str:
        return self.config.base_url.rstrip("/") + "/chat/completions"

    def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        on_text: Callable[[str], None] | None = None,
        on_notice: Callable[[str], None] | None = None,
        cancel_event: threading.Event | None = None,
        preferred_model: str | None = None,
    ) -> dict[str, Any]:
        """Envoie une requete en streaming, avec re-tentative et bascule modele.

        - Si le modele est surcharge (429 code 1305) ou rate-limite (1302), on
          reessaie quelques fois.
        - Si le modele primaire reste indisponible, on bascule automatiquement
          sur `fallback_model` (ex. glm-4.5-flash).
        - Si aucun des modèles principaux n'est disponible, on essaie les modèles
          gratuits de model_coder_free.txt dans l'ordre.
        `on_notice` sert a informer l'utilisateur (tentatives, bascule).
        `cancel_event` : si fourni et arme, interrompt le stream (leve LLMCancelled).
        `preferred_model` : si fourni, est utilisé en premier.
        """
        # Liste des modèles à essayer :
        # 1. Le modèle préféré s'il est fourni
        # 2. Le modèle principal
        # 3. Si échec, essayer les modèles de model_coder_free.txt dans l'ordre
        models = []
        
        # Ajouter le modèle préféré s'il est fourni
        if preferred_model:
            models.append(preferred_model)
        
        # Ajouter le modèle principal s'il n'est pas déjà dans la liste
        if self.config.model not in models:
            models.append(self.config.model)
        
        # Ajouter les modèles gratuits de model_coder_free.txt (s'ils ne sont pas déjà dans la liste)
        if self._free_models:
            for free_model in self._free_models:
                if free_model not in models:
                    models.append(free_model)
        
        retries = max(1, int(getattr(self.config, "max_retries", 3)))

        last: _ApiError | None = None
        used_model = models[0]  # Modèle par défaut
        for idx, model in enumerate(models):
            used_model = model  # Mettre à jour le modèle utilisé
            if idx > 0 and on_notice:
                # C'est un modèle de fallback ou gratuit
                if preferred_model and model == preferred_model:
                    on_notice(f"Utilisation du modèle préféré {model}")
                elif model == self.config.model:
                    on_notice(f"Modèle principal indisponible — bascule sur {model}")
                else:
                    on_notice(f"{models[idx-1]} indisponible — bascule sur modèle gratuit {model}")
            for attempt in range(retries):
                try:
                    result = self._stream_once(
                        model, messages, tools, on_text, cancel_event
                    )
                    # Ajouter le modèle utilisé au résultat
                    result["_used_model"] = used_model
                    return result
                except _ApiError as err:
                    last = err
                    if err.retryable and attempt < retries - 1:
                        if on_notice:
                            on_notice(
                                f"{model} surcharge — nouvelle tentative "
                                f"({attempt + 2}/{retries})…"
                            )
                        time.sleep(min(1.5 * (attempt + 1), 6))
                        continue
                    break  # non-retryable ou tentatives epuisees -> modele suivant

        detail = last.detail if last else "erreur inconnue"
        raise LLMError(f"Aucun modele disponible ({', '.join(models)}) : {detail}")

    def _stream_once(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        on_text: Callable[[str], None] | None,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        """Un seul appel streaming. Leve _ApiError sur echec HTTP."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        LLMClient.request_count += 1
        try:
            resp = self._session.post(
                self._url(),
                headers=self._headers,
                json=payload,
                stream=True,
                timeout=300,
            )
        except requests.RequestException as exc:
            # Erreur reseau : consideree comme transitoire (retryable).
            raise _ApiError(0, None, f"Connexion impossible : {exc}", retryable=True)

        if resp.status_code != 200:
            detail = resp.text[:300]
            code = None
            try:
                code = str(resp.json().get("error", {}).get("code"))
            except Exception:
                pass
            # 429 (rate limit, y compris OpenRouter) et 5xx sont retryables.
            retryable = (
                code in _RETRYABLE_CODES
                or resp.status_code == 429
                or resp.status_code >= 500
            )
            raise _ApiError(resp.status_code, code, f"{resp.status_code} {detail}", retryable)

        # Force l'UTF-8 : certains serveurs (Ollama) n'annoncent pas de charset,
        # et requests retombe alors sur latin-1 -> accents casses (mojibake).
        resp.encoding = "utf-8"

        content_parts: list[str] = []
        # Accumulation des tool_calls par index.
        tool_calls: dict[int, dict[str, Any]] = {}

        for raw_line in resp.iter_lines(decode_unicode=True):
            # Interruption demandee (Ctrl+C) : on ferme la connexion et on sort.
            if cancel_event is not None and cancel_event.is_set():
                resp.close()
                raise LLMCancelled()
            if not raw_line:
                continue
            if not raw_line.startswith("data:"):
                continue
            data = raw_line[len("data:"):].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue

            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}

            text = delta.get("content")
            if text:
                content_parts.append(text)
                if on_text:
                    on_text(text)

            for tc in delta.get("tool_calls") or []:
                idx = tc.get("index", 0)
                slot = tool_calls.setdefault(
                    idx,
                    {"id": "", "type": "function", "function": {"name": "", "arguments": ""}},
                )
                if tc.get("id"):
                    slot["id"] = tc["id"]
                fn = tc.get("function") or {}
                if fn.get("name"):
                    slot["function"]["name"] = fn["name"]
                if fn.get("arguments"):
                    slot["function"]["arguments"] += fn["arguments"]

        message: dict[str, Any] = {
            "role": "assistant",
            "content": "".join(content_parts),
        }
        if tool_calls:
            message["tool_calls"] = [tool_calls[i] for i in sorted(tool_calls)]
        return message

    def ping(self) -> tuple[bool, str]:
        """Verifie que l'endpoint repond. Renvoie (ok, message)."""
        try:
            msg = self.stream_chat(
                [{"role": "user", "content": "Reponds juste 'ok'."}],
            )
            return True, msg.get("content", "").strip() or "ok"
        except LLMError as exc:
            return False, str(exc)
