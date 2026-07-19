from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Mapping

from deviation_protocol.application.action_gateway import ActionGateway, ActionRoute
from deviation_protocol.application.ports import UnitOfWorkFactory
from deviation_protocol.domain.actions import ActionContext, ActionSubmission


ContextLoader = Callable[[ActionSubmission], Awaitable[ActionContext]]


@dataclass(slots=True)
class FirstPhaseTurnOrchestrator:
    """Idempotent first-stage shell; narrative generation is intentionally absent."""

    gateway: ActionGateway
    uow_factory: UnitOfWorkFactory
    context_loader: ContextLoader

    async def handle(self, submission: ActionSubmission) -> Mapping[str, Any]:
        async with self.uow_factory() as uow:
            # The unique key remains the final database guard, while the session
            # row lock closes the concurrent check-then-process window. Turns for
            # one session are authoritative and sequential by design.
            if not await uow.sessions.lock_for_turn(submission.session_id):
                raise LookupError(f"unknown game session: {submission.session_id}")
            existing = await uow.turn_requests.get_by_client_request_id(
                submission.session_id, submission.client_request_id
            )
            if existing is not None:
                # Returning the stored result ensures a retry can never trigger a
                # second narrative call when that provider is added later.
                return existing

            context = await self.context_loader(submission)
            result = self.gateway.evaluate(context)
            response: dict[str, Any] = {
                "route": result.route.value,
                "action_signature": result.action_signature,
                "policy_trace": [
                    {
                        "policy": item.policy,
                        "outcome": item.outcome.value,
                        "reason_code": item.reason_code,
                        "detail": item.detail,
                    }
                    for item in result.policy_trace
                ],
            }
            await uow.turn_requests.add(
                submission, result.action_signature, result.route, response=response
            )
            await uow.commit()
            return response
