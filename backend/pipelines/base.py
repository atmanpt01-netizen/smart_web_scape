from abc import ABC, abstractmethod

from backend.api.schemas import ScrapeResult, ScrapeTask


class BasePipeline(ABC):
    """모든 스크래핑 파이프라인의 추상 기본 클래스."""

    name: str
    priority: int  # 1(최우선) ~ 5(최후수단)
    estimated_cost: float = 0.0  # 상대적 비용 (0.0~1.0)
    avg_response_time: float = 5.0  # 평균 응답 시간 (초)

    @abstractmethod
    async def execute(self, task: ScrapeTask) -> ScrapeResult:
        """수집 작업을 실행합니다."""
        ...

    @abstractmethod
    async def health_check(self, url: str) -> bool:
        """파이프라인 사용 가능 여부를 확인합니다."""
        ...

    async def pre_execute(self, task: ScrapeTask) -> None:
        """실행 전 처리 (Rate limiting, 로깅 등)."""
        pass

    async def post_execute(self, result: ScrapeResult) -> None:
        """실행 후 처리 (통계 업데이트 등)."""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(priority={self.priority})"
