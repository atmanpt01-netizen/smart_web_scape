import { format } from "date-fns";
import { useVisitLog } from "../hooks/useApi";

const PIPELINE_LABELS: Record<string, string> = {
  api: "API", http: "HTTP", stealth: "스텔스", ai: "AI", proxy: "프록시",
};

export default function VisitDetail({ id, onBack }: { id: string; onBack: () => void }) {
  const { data: log, isLoading } = useVisitLog(id);

  if (isLoading) return <div className="p-6 text-gray-400">로딩 중...</div>;
  if (!log) return <div className="p-6 text-gray-400">방문 이력을 찾을 수 없습니다.</div>;

  return (
    <div className="p-6 space-y-6">
      {/* 헤더 */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
        >
          ← 목록으로
        </button>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white flex-1 truncate">
          방문 상세
        </h2>
        <span className={`text-xs px-3 py-1 rounded-full font-medium ${log.success ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>
          {log.success ? "성공" : "실패"}
        </span>
      </div>

      {/* 요약 카드 */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {[
          { label: "방문 시각", value: log.visited_at ? format(new Date(log.visited_at), "yyyy/MM/dd HH:mm:ss") : "-" },
          { label: "파이프라인", value: PIPELINE_LABELS[log.pipeline_name] ?? log.pipeline_name ?? "-" },
          { label: "소요 시간", value: log.duration_ms ? `${log.duration_ms}ms` : "-" },
          { label: "상태 코드", value: log.status_code ?? "-" },
        ].map((item) => (
          <div key={item.label} className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700">
            <p className="text-xs text-gray-500 dark:text-gray-400">{item.label}</p>
            <p className="text-base font-semibold text-gray-900 dark:text-white mt-1">{String(item.value)}</p>
          </div>
        ))}
      </div>

      {/* URL 정보 */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">URL</h3>
        <a href={log.url} target="_blank" rel="noreferrer" className="text-sm text-blue-600 hover:underline break-all">
          {log.url}
        </a>
        {log.error_message && (
          <p className="mt-2 text-sm text-red-500 bg-red-50 dark:bg-red-900/20 rounded p-2">{log.error_message}</p>
        )}
      </div>

      {/* 파이프라인 시도 이력 */}
      {log.pipelines_attempted?.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">시도한 파이프라인 순서</h3>
          <div className="flex gap-2 flex-wrap">
            {log.pipelines_attempted.map((p: string, i: number) => (
              <div key={i} className="flex items-center gap-1">
                {i > 0 && <span className="text-gray-300">→</span>}
                <span className={`text-xs px-2 py-1 rounded ${p === log.pipeline_name ? "bg-blue-600 text-white" : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300"}`}>
                  {PIPELINE_LABELS[p] ?? p}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Self-Healing 정보 */}
      {log.healing_applied && (
        <div className="bg-purple-50 dark:bg-purple-900/20 rounded-xl p-5 border border-purple-200 dark:border-purple-700">
          <h3 className="text-sm font-semibold text-purple-700 dark:text-purple-300 mb-2">🔧 Self-Healing 적용됨</h3>
          <p className="text-sm text-purple-600 dark:text-purple-400">
            유형: <span className="font-medium">{log.healing_type ?? "-"}</span>
          </p>
        </div>
      )}

      {/* 안티봇 감지 */}
      {log.antibot_detected && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-xl p-5 border border-yellow-200 dark:border-yellow-700">
          <h3 className="text-sm font-semibold text-yellow-700 dark:text-yellow-300 mb-2">⚠️ 안티봇 감지됨</h3>
          <p className="text-sm text-yellow-600 dark:text-yellow-400">
            유형: <span className="font-medium">{log.antibot_detected}</span>
            {log.captcha_encountered && " · CAPTCHA 발생"}
          </p>
        </div>
      )}

      {/* 수집 데이터 메타 */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">수집 정보</h3>
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-gray-500 dark:text-gray-400">콘텐츠 크기</dt>
            <dd className="text-gray-900 dark:text-white mt-0.5">
              {log.content_size_bytes ? `${(log.content_size_bytes / 1024).toFixed(1)} KB` : "-"}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500 dark:text-gray-400">추출 항목 수</dt>
            <dd className="text-gray-900 dark:text-white mt-0.5">{log.items_extracted ?? "-"}</dd>
          </div>
          <div>
            <dt className="text-gray-500 dark:text-gray-400">콘텐츠 해시</dt>
            <dd className="text-gray-900 dark:text-white mt-0.5 font-mono text-xs truncate">{log.content_hash ?? "-"}</dd>
          </div>
          <div>
            <dt className="text-gray-500 dark:text-gray-400">프록시 사용</dt>
            <dd className="text-gray-900 dark:text-white mt-0.5">{log.proxy_used ?? "없음"}</dd>
          </div>
        </dl>
      </div>

      {/* 메서드 상세 (JSON) */}
      {log.method_details && Object.keys(log.method_details).length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">메서드 상세</h3>
          <pre className="text-xs bg-gray-50 dark:bg-gray-900 rounded-lg p-3 overflow-x-auto text-gray-700 dark:text-gray-300">
            {JSON.stringify(log.method_details, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
