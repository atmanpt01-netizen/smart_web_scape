import structlog

from backend.api.schemas import ScrapeResult, ScrapeTask
from backend.pipelines.registry import get_registry

logger = structlog.get_logger(__name__)


class PipelineOrchestrator:
    """파이프라인 순차 실행 및 자동 fallback을 담당하는 오케스트레이터."""

    async def execute(self, task: ScrapeTask) -> ScrapeResult:
        """
        ScrapeTask를 받아 적절한 파이프라인 체인으로 수집을 수행합니다.

        1. URL 프로파일에서 최적 파이프라인 조회 (Phase 2에서 활성화)
        2. 카테고리별 파이프라인 순서 결정
        3. 순차 실행, 실패 시 다음 파이프라인으로 자동 전환
        4. 전체 실패 시 Self-Healing 트리거 (Phase 3에서 활성화)
        """
        registry = get_registry()

        # 파이프라인 순서 결정: pipeline_override > URL profile > 카테고리 기본값
        if task.pipeline_override:
            pipeline = next(
                (p for p in registry.all() if p.name == task.pipeline_override),
                None,
            )
            pipelines = [pipeline] if pipeline else registry.get_for_category(task.category)
        else:
            pipelines = registry.get_for_category(task.category)

        if not pipelines:
            pipelines = registry.all()

        last_result: ScrapeResult | None = None
        for sequence, pipeline in enumerate(pipelines, start=1):
            log = logger.bind(url=task.url, pipeline=pipeline.name, sequence=sequence)

            # health check
            is_healthy = await pipeline.health_check(task.url)
            if not is_healthy:
                log.warning("pipeline_health_check_failed")
                continue

            log.info("pipeline_executing")
            await pipeline.pre_execute(task)

            result = await pipeline.execute(task)
            result.pipeline_sequence = sequence

            await pipeline.post_execute(result)

            if result.success:
                log.info("pipeline_success", duration_ms=result.duration_ms)
                return result

            log.warning(
                "pipeline_failed",
                error_type=result.error_type,
                error_message=result.error_message,
            )
            last_result = result

        # 모든 파이프라인 실패
        logger.error("all_pipelines_failed", url=task.url, tried=len(pipelines))

        if last_result is None:
            last_result = ScrapeResult(
                url_id=task.url_id,
                url=task.url,
                success=False,
                pipeline_name="none",
                pipeline_sequence=0,
                pipelines_attempted=[p.name for p in pipelines],
                duration_ms=0,
                error_type="all_pipelines_failed",
                error_message="모든 파이프라인이 실패했습니다.",
            )

        return last_result
