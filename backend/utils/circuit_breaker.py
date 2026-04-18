"""Circuit Breaker 패턴 — 외부 API/프록시 장애 전파를 차단합니다."""
import time
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"       # 정상: 요청 통과
    OPEN = "open"           # 차단: 모든 요청 즉시 실패 반환
    HALF_OPEN = "half_open" # 복구 시도: 테스트 요청 1개만 허용


class CircuitBreaker:
    """
    도메인/서비스별 Circuit Breaker.

    - CLOSED: 정상 상태, 요청 허용
    - OPEN: failure_threshold 이상 연속 실패 → 요청 차단
    - HALF_OPEN: recovery_timeout 경과 후 테스트 요청 허용
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 300.0,  # 5분
        name: str = "default",
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time > self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info("circuit_half_open", name=self.name)
        return self._state

    def is_allowed(self) -> bool:
        """요청 실행이 허용되는지 확인합니다."""
        return self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self) -> None:
        """요청 성공을 기록합니다."""
        if self._state == CircuitState.HALF_OPEN:
            logger.info("circuit_closed", name=self.name)
        self._state = CircuitState.CLOSED
        self._failure_count = 0

    def record_failure(self) -> None:
        """요청 실패를 기록하고 임계값 초과 시 회로를 엽니다."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            logger.warning("circuit_reopened", name=self.name)
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "circuit_opened",
                name=self.name,
                failures=self._failure_count,
                recovery_in=self.recovery_timeout,
            )


class CircuitBreakerRegistry:
    """도메인별 CircuitBreaker 인스턴스 관리."""

    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}

    def get(self, name: str, **kwargs: int | float) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name=name, **kwargs)
        return self._breakers[name]


_registry = CircuitBreakerRegistry()


def get_circuit_breaker(name: str) -> CircuitBreaker:
    return _registry.get(name)
