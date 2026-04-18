"""URL Profile 학습 엔진

방문 이력을 분석하여 각 URL에 대한 최적 수집 전략을 도출하고 프로파일을 갱신합니다.
"""
import uuid
from dataclasses import dataclass

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import ScrapeResult
from backend.db.models import UrlProfile, VisitLog

logger = structlog.get_logger(__name__)


@dataclass
class ScrapeStrategy:
    """최적화된 수집 전략."""
    best_pipeline: str | None
    optimal_delay_ms: int
    recommended_user_agent: str | None
    avoid_times: list[int]  # 실패율 높은 시간대 (0-23)


@dataclass
class FailureAnalysis:
    """실패 패턴 분석 결과."""
    dominant_error: str | None
    failure_rate: float
    antibot_frequency: float
    captcha_frequency: float
    common_pipelines_failed: list[str]


class VisitOptimizer:
    """방문 이력 기반 수집 전략 최적화 엔진."""

    async def update_profile(self, session: AsyncSession, result: ScrapeResult) -> None:
        """수집 결과를 바탕으로 URL 프로파일을 갱신합니다."""
        profile_result = await session.execute(
            select(UrlProfile).where(UrlProfile.url_id == result.url_id)
        )
        profile = profile_result.scalar_one_or_none()
        if not profile:
            return

        # 통계 갱신
        profile.total_visits += 1
        if result.success:
            profile.success_count += 1

        profile.success_rate = profile.success_count / profile.total_visits

        # 평균 응답시간 (이동평균)
        if result.duration_ms:
            if profile.total_visits == 1:
                profile.avg_response_time_ms = float(result.duration_ms)
            else:
                # EMA (Exponential Moving Average)
                alpha = 0.2
                profile.avg_response_time_ms = (
                    alpha * result.duration_ms + (1 - alpha) * profile.avg_response_time_ms
                )

        # 최적 파이프라인 갱신 (성공 시)
        if result.success:
            profile.best_pipeline = result.pipeline_name

        # 사이트 특성 갱신
        if result.antibot_detected:
            profile.has_antibot = True
            profile.antibot_type = result.antibot_detected

        if result.method_details and result.method_details.get("browser"):
            profile.requires_js = True

        # 구조 해시 갱신
        if result.content_hash:
            profile.page_structure_hash = result.content_hash

        from datetime import datetime
        profile.last_visited_at = datetime.utcnow()

        await session.commit()
        logger.debug(
            "profile_updated",
            url_id=str(result.url_id),
            success_rate=round(profile.success_rate, 3),
            total_visits=profile.total_visits,
        )

    async def optimize_next_visit(self, session: AsyncSession, url_id: uuid.UUID) -> ScrapeStrategy:
        """다음 방문을 위한 최적화된 전략을 반환합니다."""
        profile_result = await session.execute(
            select(UrlProfile).where(UrlProfile.url_id == url_id)
        )
        profile = profile_result.scalar_one_or_none()

        if not profile:
            return ScrapeStrategy(
                best_pipeline=None,
                optimal_delay_ms=1000,
                recommended_user_agent=None,
                avoid_times=[],
            )

        # 실패 패턴 분석
        failure_analysis = await self.analyze_failure_patterns(session, url_id)

        # 최적 딜레이 결정 (안티봇 감지 시 딜레이 증가)
        optimal_delay = profile.optimal_delay_ms
        if profile.has_antibot:
            optimal_delay = max(optimal_delay, 3000)
        if failure_analysis.antibot_frequency > 0.3:
            optimal_delay = max(optimal_delay, 5000)

        return ScrapeStrategy(
            best_pipeline=profile.best_pipeline,
            optimal_delay_ms=optimal_delay,
            recommended_user_agent=profile.best_user_agent,
            avoid_times=[],
        )

    async def analyze_failure_patterns(
        self, session: AsyncSession, url_id: uuid.UUID
    ) -> FailureAnalysis:
        """URL의 실패 패턴을 분석합니다."""
        # 최근 50건 방문 이력 조회
        result = await session.execute(
            select(VisitLog)
            .where(VisitLog.url_id == url_id)
            .order_by(VisitLog.visited_at.desc())
            .limit(50)
        )
        logs = result.scalars().all()

        if not logs:
            return FailureAnalysis(
                dominant_error=None,
                failure_rate=0.0,
                antibot_frequency=0.0,
                captcha_frequency=0.0,
                common_pipelines_failed=[],
            )

        total = len(logs)
        failed = [log for log in logs if not log.success]
        antibot_detected = [log for log in logs if log.antibot_detected]
        captcha_encountered = [log for log in logs if log.captcha_encountered]

        # 가장 빈번한 에러 타입
        error_counts: dict[str, int] = {}
        for log in failed:
            if log.error_type:
                error_counts[log.error_type] = error_counts.get(log.error_type, 0) + 1
        dominant_error = max(error_counts, key=lambda k: error_counts[k]) if error_counts else None

        # 실패가 많은 파이프라인
        pipeline_failures: dict[str, int] = {}
        for log in failed:
            pipeline_failures[log.pipeline_name] = pipeline_failures.get(log.pipeline_name, 0) + 1
        failed_pipelines = sorted(pipeline_failures, key=lambda k: pipeline_failures[k], reverse=True)[:3]

        return FailureAnalysis(
            dominant_error=dominant_error,
            failure_rate=len(failed) / total,
            antibot_frequency=len(antibot_detected) / total,
            captcha_frequency=len(captcha_encountered) / total,
            common_pipelines_failed=failed_pipelines,
        )
