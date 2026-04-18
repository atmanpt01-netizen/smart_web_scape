from backend.core.url_classifier import CATEGORY_PIPELINE_ORDER
from backend.pipelines.ai_pipeline import AiPipeline
from backend.pipelines.api_pipeline import ApiPipeline
from backend.pipelines.base import BasePipeline
from backend.pipelines.http_pipeline import HttpPipeline
from backend.pipelines.proxy_pipeline import ProxyPipeline
from backend.pipelines.stealth_pipeline import StealthPipeline


class PipelineRegistry:
    """파이프라인 등록 및 조회 레지스트리."""

    def __init__(self) -> None:
        self._pipelines: dict[int, BasePipeline] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        # Phase 1: HTTP
        self.register(HttpPipeline())
        # Phase 2: API, Stealth, AI
        self.register(ApiPipeline())
        self.register(StealthPipeline())
        self.register(AiPipeline())
        # Phase 3: Proxy
        self.register(ProxyPipeline())

    def register(self, pipeline: BasePipeline) -> None:
        self._pipelines[pipeline.priority] = pipeline

    def get(self, priority: int) -> BasePipeline | None:
        return self._pipelines.get(priority)

    def get_for_category(self, category: str) -> list[BasePipeline]:
        """카테고리에 맞는 파이프라인 목록을 우선순위 순서로 반환합니다."""
        order = CATEGORY_PIPELINE_ORDER.get(category, CATEGORY_PIPELINE_ORDER["enterprise"])
        pipelines = []
        for priority in order:
            pipeline = self._pipelines.get(priority)
            if pipeline is not None:
                pipelines.append(pipeline)
        return pipelines

    def all(self) -> list[BasePipeline]:
        return sorted(self._pipelines.values(), key=lambda p: p.priority)


# 싱글턴 레지스트리 인스턴스
_registry: PipelineRegistry | None = None


def get_registry() -> PipelineRegistry:
    global _registry
    if _registry is None:
        _registry = PipelineRegistry()
    return _registry
