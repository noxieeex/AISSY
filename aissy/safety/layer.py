import re
from datetime import datetime

from aissy.safety.actions import Action, Decision, Origin, Verdict
from aissy.safety.audit import summarize_args
from aissy.safety.policy import Policy

STOP_PHRASES = {
    "parar tudo", "para tudo", "pare tudo", "parada de emergência",
    "emergência", "stop everything", "emergency stop",
}


def is_stop_phrase(text):
    cleaned = re.sub(r"[^\w\sà-ÿ]", "", text.lower()).strip()
    return cleaned in STOP_PHRASES


class ActionBlocked(RuntimeError):
    """A Safety Layer não autorizou a ação."""

    def __init__(self, decision):
        super().__init__(
            f"Blocked by safety layer ({decision.rule}): {decision.reason}"
        )
        self.decision = decision


def _deny(rule, reason):
    return Decision(Verdict.DENY, rule, reason)


class SafetyLayer:
    """
    Único caminho até os executores. Política "fail closed": qualquer falha,
    ausência de registro ou situação não prevista bloqueia a ação.
    """

    def __init__(self, policy=None, audit=None, now_fn=None):
        self.policy = policy if policy is not None else Policy()
        self.audit = audit
        self.now_fn = now_fn or datetime.now
        self.healthy = True
        self.stopped = False

    # ---- parada de emergência (não depende do modelo) ----

    def halt(self):
        self.stopped = True

    def resume(self):
        self.stopped = False

    # ---- decisão ----

    def evaluate(self, action):
        if self.stopped:
            return _deny("emergency.stopped", "Emergency stop is active.")

        if not self.healthy:
            return _deny("layer.unhealthy", "Safety layer is not healthy.")

        if self.audit is None:
            return _deny("audit.missing", "No audit log configured.")

        try:
            decision = self.policy.decide(action)
        except Exception:
            return _deny("policy.error", "Policy failed; blocking (fail closed).")

        if not isinstance(decision, Decision):
            return _deny("policy.invalid", "Invalid policy result.")

        if decision.verdict == Verdict.CONFIRM:
            return _deny(
                "confirmation.unavailable",
                "Confirmation is required but not available yet.",
            )

        return decision

    # ---- execução ----

    def _entry(self, event, action, decision=None, result=None):
        entry = {
            "ts": self.now_fn().isoformat(timespec="seconds"),
            "event": event,
        }

        if isinstance(action, Action):
            entry.update({
                "origin": getattr(action.origin, "value", str(action.origin)),
                "kind": action.kind,
                "operation": action.operation,
                "target": action.target,
                "args": summarize_args(action.args),
            })

        if decision is not None:
            entry.update({
                "decision": decision.verdict.value,
                "rule": decision.rule,
                "reason": decision.reason,
            })

        if result is not None:
            entry["result"] = result

        return entry

    def run(self, action, executor):
        """Avalia, registra e só então executa. Bloqueia por padrão."""
        decision = self.evaluate(action)

        if self.audit is None:
            raise ActionBlocked(decision)

        try:
            self.audit.record(self._entry("decision", action, decision))
        except Exception:
            self.healthy = False
            raise ActionBlocked(
                _deny("audit.unavailable", "Could not write the audit log.")
            ) from None

        if not decision.allowed:
            raise ActionBlocked(decision)

        try:
            result = executor()
        except Exception as error:
            self._record_result(action, f"error: {type(error).__name__}")
            raise

        self._record_result(action, "ok")

        return result

    def _record_result(self, action, outcome):
        try:
            self.audit.record(self._entry("result", action, result=outcome))
        except Exception:
            # Sem conseguir registrar, as próximas ações ficam bloqueadas.
            self.healthy = False

    def self_check(self):
        """Verificação de inicialização. Se falhar, nada deve executar."""
        try:
            canary = Action("process_memory", "read", Origin.MODEL)

            if self.policy.decide(canary).verdict != Verdict.DENY:
                return False

            if self.audit is None:
                return False

            self.audit.record({
                "ts": self.now_fn().isoformat(timespec="seconds"),
                "event": "self_check",
            })

            return True
        except Exception:
            return False


def guard(safety, action, executor):
    """Executa via Safety Layer. Sem camada disponível, bloqueia."""
    if safety is None:
        raise ActionBlocked(
            _deny("layer.unavailable", "Safety layer is not available.")
        )

    return safety.run(action, executor)
