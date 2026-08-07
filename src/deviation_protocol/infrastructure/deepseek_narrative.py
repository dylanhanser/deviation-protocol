from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Annotated, Any, Literal, Protocol
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from deviation_protocol.application.dynamic_narrative_models import (
    DynamicNarrativeRequest,
    DynamicNarrativeResponseCategory,
    DynamicNarrativeResponseError,
    DynamicProviderCandidateContract,
    DynamicProviderCandidateContractError,
    DynamicPromptBuilder,
    UntrustedDynamicNarrativeCandidate,
)
from deviation_protocol.application.narrative_models import (
    MAX_NARRATIVE_USAGE_TOKENS,
    NarrativeProposalPayload,
    NarrativeProviderAuthenticationError,
    NarrativeProviderBalanceError,
    NarrativeProviderMetadata,
    NarrativeProviderRateLimitError,
    NarrativeProviderRequestError,
    NarrativeProviderResponseError,
    NarrativeProviderTruncatedError,
    NarrativeProviderUnavailableError,
    NarrativeRequest,
    NarrativeUsage,
    UntrustedNarrativeProposal,
)
from deviation_protocol.application.narrative_prompt import PromptBuilder


OFFICIAL_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
OFFICIAL_DEEPSEEK_CHAT_COMPLETIONS_URL = (
    f"{OFFICIAL_DEEPSEEK_BASE_URL}/chat/completions"
)
ALLOWED_DEEPSEEK_MODELS = frozenset(
    {"deepseek-v4-flash", "deepseek-v4-pro"}
)
MAX_RESPONSE_BYTES = 1_000_000


class DeepSeekSettings(BaseModel):
    """Strict trusted configuration; secrets are masked in repr and errors."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    api_key: SecretStr
    base_url: str = OFFICIAL_DEEPSEEK_BASE_URL
    model: Literal["deepseek-v4-flash", "deepseek-v4-pro"] = "deepseek-v4-flash"
    timeout_seconds: Annotated[
        float, Field(strict=True, gt=0.0, le=120.0)
    ] = 30.0
    max_tokens: Annotated[int, Field(strict=True, ge=64, le=4_096)] = 1_200
    # The conservative production default is one transport attempt.  An
    # interrupted/read-timed-out request may already have reached the provider,
    # so an automatic retry can duplicate provider work or billing.
    max_retries: Annotated[int, Field(strict=True, ge=0, le=2)] = 0
    backoff_base_seconds: Annotated[
        float, Field(strict=True, ge=0.0, le=10.0)
    ] = 0.25

    @field_validator("api_key")
    @classmethod
    def require_key(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("DeepSeek API key is required")
        return value

    @field_validator("base_url")
    @classmethod
    def require_official_https_host(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "api.deepseek.com"
            or parsed.port not in (None, 443)
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("DeepSeek base URL must use the official HTTPS host")
        return OFFICIAL_DEEPSEEK_BASE_URL

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> DeepSeekSettings:
        """Read process environment only when explicitly called; never load .env."""

        source = os.environ if environ is None else environ
        key = source.get("DEEPSEEK_API_KEY")
        if not key:
            raise ValueError("DEEPSEEK_API_KEY is not configured")
        try:
            timeout = float(source.get("DEEPSEEK_TIMEOUT_SECONDS", "30"))
            max_tokens = int(source.get("DEEPSEEK_MAX_TOKENS", "1200"))
            max_retries = int(source.get("DEEPSEEK_MAX_RETRIES", "0"))
        except (TypeError, ValueError) as exc:
            raise ValueError("DeepSeek numeric configuration is invalid") from None
        return cls(
            api_key=key,
            base_url=source.get("DEEPSEEK_BASE_URL", OFFICIAL_DEEPSEEK_BASE_URL),
            model=source.get("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            timeout_seconds=timeout,
            max_tokens=max_tokens,
            max_retries=max_retries,
        )


class DeepSeekTransportTimeout(TimeoutError):
    pass


class DeepSeekTransportConnectionError(ConnectionError):
    pass


class DeepSeekTransportResponseError(ValueError):
    pass


class DeepSeekHttpResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    status_code: Annotated[int, Field(strict=True, ge=100, le=599)]
    body_text: str
    request_id: Annotated[str, Field(strict=True, min_length=1, max_length=256)] | None = None


class DeepSeekTransport(Protocol):
    async def post_json(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, Any],
        timeout_seconds: float,
    ) -> DeepSeekHttpResponse: ...

    async def aclose(self) -> None: ...


class HttpxDeepSeekTransport:
    """Small HTTP adapter with no default authorization header or logging."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            follow_redirects=False,
            trust_env=False,
        )

    async def post_json(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, Any],
        timeout_seconds: float,
    ) -> DeepSeekHttpResponse:
        if url != OFFICIAL_DEEPSEEK_CHAT_COMPLETIONS_URL:
            raise DeepSeekTransportConnectionError()
        try:
            response = await self._client.post(
                url,
                headers=dict(headers),
                json=dict(payload),
                timeout=httpx.Timeout(timeout_seconds),
            )
        except httpx.TimeoutException as exc:
            raise DeepSeekTransportTimeout() from None
        except httpx.RequestError as exc:
            raise DeepSeekTransportConnectionError() from None
        body = response.content
        if len(body) > MAX_RESPONSE_BYTES:
            raise DeepSeekTransportResponseError()
        request_id = response.headers.get("x-request-id")
        if request_id is not None and not 1 <= len(request_id) <= 256:
            request_id = None
        return DeepSeekHttpResponse(
            status_code=response.status_code,
            body_text=body.decode("utf-8", errors="strict"),
            request_id=request_id,
        )

    async def aclose(self) -> None:
        await self._client.aclose()


Waiter = Callable[[float], Awaitable[None]]
Clock = Callable[[], float]
TransportFactory = Callable[[], DeepSeekTransport]


class DeepSeekNarrativeProvider:
    """DeepSeek V4 Chat Completions adapter returning only untrusted proposals."""

    def __init__(
        self,
        settings: DeepSeekSettings,
        prompt_builder: PromptBuilder,
        *,
        transport: DeepSeekTransport | None = None,
        transport_factory: TransportFactory = HttpxDeepSeekTransport,
        waiter: Waiter = asyncio.sleep,
        clock: Clock = time.perf_counter,
        dynamic_prompt_builder: DynamicPromptBuilder | None = None,
    ) -> None:
        self._settings = settings
        self._prompt_builder = prompt_builder
        self._transport = transport
        self._transport_factory = transport_factory
        self._owns_transport = transport is None
        self._waiter = waiter
        self._clock = clock
        self._dynamic_prompt_builder = dynamic_prompt_builder or DynamicPromptBuilder()
        self._closed = False

    def __repr__(self) -> str:
        return (
            "DeepSeekNarrativeProvider("
            f"model={self._settings.model!r}, "
            f"base_url={self._settings.base_url!r}, closed={self._closed!r})"
        )

    async def generate(
        self, request: NarrativeRequest
    ) -> UntrustedNarrativeProposal:
        if self._closed:
            raise NarrativeProviderUnavailableError()
        prompt = self._prompt_builder.build(request)
        payload: dict[str, Any] = {
            "model": self._settings.model,
            "messages": [
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": prompt.user},
            ],
            "thinking": {"type": "disabled"},
            "stream": False,
            "response_format": {"type": "json_object"},
            "max_tokens": self._settings.max_tokens,
        }
        headers = {
            "Authorization": (
                "Bearer " + self._settings.api_key.get_secret_value()
            ),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        started = self._clock()
        maximum_attempts = self._settings.max_retries + 1
        content_retry_used = False
        last_retry_kind = "unavailable"

        for attempt in range(1, maximum_attempts + 1):
            try:
                response = await self._get_transport().post_json(
                    url=OFFICIAL_DEEPSEEK_CHAT_COMPLETIONS_URL,
                    headers=headers,
                    payload=payload,
                    timeout_seconds=self._settings.timeout_seconds,
                )
            except (DeepSeekTransportTimeout, DeepSeekTransportConnectionError):
                last_retry_kind = "unavailable"
                if attempt < maximum_attempts:
                    await self._backoff(attempt)
                    continue
                raise NarrativeProviderUnavailableError() from None
            except DeepSeekTransportResponseError:
                raise NarrativeProviderResponseError() from None
            except asyncio.CancelledError:
                raise
            except Exception:
                raise NarrativeProviderUnavailableError() from None

            if response.status_code != 200:
                retry_kind = self._classify_status(response.status_code)
                if retry_kind in {"rate", "unavailable"} and attempt < maximum_attempts:
                    last_retry_kind = retry_kind
                    await self._backoff(attempt)
                    continue
                self._raise_status(response.status_code)

            if len(response.body_text.encode("utf-8")) > MAX_RESPONSE_BYTES:
                raise NarrativeProviderResponseError()

            envelope = _parse_envelope(response.body_text)
            finish_reason, content = _choice_content(envelope)
            if finish_reason == "length":
                raise NarrativeProviderTruncatedError()
            if finish_reason != "stop":
                raise NarrativeProviderResponseError()
            if not isinstance(content, str) or not content.strip():
                if not content_retry_used and attempt < maximum_attempts:
                    content_retry_used = True
                    await self._backoff(attempt)
                    continue
                raise NarrativeProviderResponseError()
            try:
                json.loads(
                    content,
                    parse_float=_reject_float,
                    parse_constant=_reject_constant,
                    object_pairs_hook=_reject_duplicate_object_keys,
                )
            except (json.JSONDecodeError, TypeError, ValueError):
                if not content_retry_used and attempt < maximum_attempts:
                    content_retry_used = True
                    await self._backoff(attempt)
                    continue
                raise NarrativeProviderResponseError() from None
            try:
                proposal = NarrativeProposalPayload.model_validate_json(content)
            except (TypeError, ValueError):
                raise NarrativeProviderResponseError() from None

            elapsed_ms = max(0, int((self._clock() - started) * 1_000))
            body_request_id = envelope.get("id")
            request_id = (
                body_request_id
                if isinstance(body_request_id, str)
                and 1 <= len(body_request_id) <= 256
                and _safe_request_id(body_request_id)
                else response.request_id
                if response.request_id is not None
                and _safe_request_id(response.request_id)
                else None
            )
            return UntrustedNarrativeProposal(
                proposal=proposal,
                provider_metadata=NarrativeProviderMetadata(
                    provider="deepseek",
                    model=self._settings.model,
                    request_id=request_id,
                    finish_reason=finish_reason,
                    attempts=attempt,
                    latency_ms=elapsed_ms,
                ),
                usage=_usage(envelope.get("usage")),
            )

        if last_retry_kind == "rate":  # pragma: no cover - loop always raises
            raise NarrativeProviderRateLimitError()
        raise NarrativeProviderUnavailableError()  # pragma: no cover

    async def generate_dynamic(
        self, request: DynamicNarrativeRequest
    ) -> UntrustedDynamicNarrativeCandidate:
        """Make the spike's one exact, non-retried dynamic Provider attempt."""

        if self._closed:
            raise NarrativeProviderUnavailableError()
        if self._settings.max_retries != 0:
            raise NarrativeProviderRequestError()
        prompt_failed = False
        try:
            prompt = self._dynamic_prompt_builder.build(request)
        except (TypeError, ValueError):
            prompt_failed = True
        if prompt_failed:
            raise NarrativeProviderRequestError()
        payload: dict[str, Any] = {
            "model": self._settings.model,
            "messages": [
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": prompt.user},
            ],
            "thinking": {"type": "disabled"},
            "stream": False,
            "response_format": {"type": "json_object"},
            "max_tokens": self._settings.max_tokens,
        }
        headers = {
            "Authorization": "Bearer " + self._settings.api_key.get_secret_value(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        started = self._clock()
        transport_failure: Literal["response", "unavailable"] | None = None
        try:
            response = await self._get_transport().post_json(
                url=OFFICIAL_DEEPSEEK_CHAT_COMPLETIONS_URL,
                headers=headers,
                payload=payload,
                timeout_seconds=self._settings.timeout_seconds,
            )
        except (DeepSeekTransportTimeout, DeepSeekTransportConnectionError):
            transport_failure = "unavailable"
        except DeepSeekTransportResponseError:
            transport_failure = "response"
        except asyncio.CancelledError:
            raise
        except Exception:
            transport_failure = "unavailable"
        if transport_failure == "response":
            raise NarrativeProviderResponseError()
        if transport_failure == "unavailable":
            raise NarrativeProviderUnavailableError()

        if response.status_code != 200:
            self._raise_status(response.status_code)
        if len(response.body_text.encode("utf-8")) > MAX_RESPONSE_BYTES:
            raise NarrativeProviderResponseError()
        envelope = _parse_envelope(response.body_text)
        finish_reason, content = _choice_content(envelope)
        if finish_reason == "length":
            raise NarrativeProviderTruncatedError()
        if finish_reason != "stop":
            raise NarrativeProviderResponseError()
        if not isinstance(content, str) or not content.strip():
            raise DynamicNarrativeResponseError(
                DynamicNarrativeResponseCategory.UNPARSEABLE_RESPONSE
            )
        decoding_failed = False
        try:
            _decoded = json.loads(
                content,
                parse_constant=_reject_constant,
                object_pairs_hook=_reject_duplicate_object_keys,
            )
        except (UnicodeError, json.JSONDecodeError, TypeError, ValueError):
            decoding_failed = True
        if decoding_failed:
            raise DynamicNarrativeResponseError(
                DynamicNarrativeResponseCategory.UNPARSEABLE_RESPONSE
            )
        contract_failure_family = None
        try:
            candidate = DynamicProviderCandidateContract.validate_response_json(
                _decoded, content
            )
        except DynamicProviderCandidateContractError as exc:
            contract_failure_family = exc.family
        if contract_failure_family is not None:
            raise DynamicNarrativeResponseError(
                DynamicNarrativeResponseCategory.SCHEMA_INVALID_RESPONSE,
                schema_failure_family=contract_failure_family,
            )
        elapsed_ms = max(0, int((self._clock() - started) * 1_000))
        body_request_id = envelope.get("id")
        request_id = (
            body_request_id
            if isinstance(body_request_id, str)
            and 1 <= len(body_request_id) <= 256
            and _safe_request_id(body_request_id)
            else response.request_id
            if response.request_id is not None and _safe_request_id(response.request_id)
            else None
        )
        return UntrustedDynamicNarrativeCandidate(
            candidate=candidate,
            provider_metadata=NarrativeProviderMetadata(
                provider="deepseek",
                model=self._settings.model,
                request_id=request_id,
                finish_reason=finish_reason,
                attempts=1,
                latency_ms=elapsed_ms,
            ),
            usage=_usage(envelope.get("usage")),
        )

    async def _backoff(self, failed_attempt: int) -> None:
        delay = min(
            self._settings.backoff_base_seconds * (2 ** (failed_attempt - 1)),
            10.0,
        )
        await self._waiter(delay)

    @staticmethod
    def _classify_status(status_code: int) -> str:
        if status_code == 429:
            return "rate"
        if status_code in {500, 503}:
            return "unavailable"
        return "terminal"

    @staticmethod
    def _raise_status(status_code: int) -> None:
        if status_code in {400, 422}:
            raise NarrativeProviderRequestError()
        if status_code == 401:
            raise NarrativeProviderAuthenticationError()
        if status_code == 402:
            raise NarrativeProviderBalanceError()
        if status_code == 429:
            raise NarrativeProviderRateLimitError()
        if status_code in {500, 503}:
            raise NarrativeProviderUnavailableError()
        raise NarrativeProviderUnavailableError()

    def _get_transport(self) -> DeepSeekTransport:
        if self._transport is None:
            self._transport = self._transport_factory()
        return self._transport

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._transport is not None and self._owns_transport:
            await self._transport.aclose()


def _parse_envelope(body_text: str) -> dict[str, Any]:
    parsing_failed = False
    try:
        parsed = json.loads(
            body_text,
            parse_constant=_reject_constant,
            object_pairs_hook=_reject_duplicate_object_keys,
        )
    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        parsing_failed = True
    if parsing_failed:
        raise NarrativeProviderResponseError()
    if not isinstance(parsed, dict):
        raise NarrativeProviderResponseError()
    return parsed


def _choice_content(envelope: Mapping[str, Any]) -> tuple[str, Any]:
    choices = envelope.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise NarrativeProviderResponseError()
    choice = choices[0]
    if not isinstance(choice, dict):
        raise NarrativeProviderResponseError()
    finish_reason = choice.get("finish_reason")
    message = choice.get("message")
    if not isinstance(finish_reason, str) or not isinstance(message, dict):
        raise NarrativeProviderResponseError()
    return finish_reason, message.get("content")


def _usage(value: Any) -> NarrativeUsage:
    if value is None:
        return NarrativeUsage()
    if not isinstance(value, Mapping):
        raise NarrativeProviderResponseError()
    return NarrativeUsage(
        input_tokens=_optional_usage_int(value, "prompt_tokens"),
        output_tokens=_optional_usage_int(value, "completion_tokens"),
        total_tokens=_optional_usage_int(value, "total_tokens"),
        cache_hit_input_tokens=_optional_usage_int(
            value, "prompt_cache_hit_tokens"
        ),
        cache_miss_input_tokens=_optional_usage_int(
            value, "prompt_cache_miss_tokens"
        ),
    )


def _optional_usage_int(value: Mapping[str, Any], key: str) -> int | None:
    if key not in value:
        return None
    token_count = value[key]
    if (
        type(token_count) is not int
        or token_count < 0
        or token_count > MAX_NARRATIVE_USAGE_TOKENS
    ):
        raise NarrativeProviderResponseError()
    return token_count


def _safe_request_id(value: str) -> bool:
    return all(character.isalnum() or character in "_.:-" for character in value)


def _reject_duplicate_object_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_float(_: str) -> Any:
    raise ValueError("floats are not accepted in narrative proposal JSON")


def _reject_constant(_: str) -> Any:
    raise ValueError("non-standard numbers are not accepted")
