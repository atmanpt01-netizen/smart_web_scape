import { useState } from "react";
import { format } from "date-fns";
import toast from "react-hot-toast";
import { useUrl, useHistory, useScrapeNow } from "../hooks/useApi";

const PIPELINE_LABELS: Record<string, string> = {
  api: "API", http: "HTTP", stealth: "스텔스", ai: "AI", proxy: "프록시",
};

export default function UrlDetail({ id, onBack }: { id: string; onBack: () => void }) {
  const [historyPage, setHistoryPage] = useState(1);
  const { data: url, isLoading } = useUrl(id);
  const { data: history } = useHistory({ url_id: id, page: historyPage, size: 10 });
  const scrapeNow = useScrapeNow();

  const handleScrape = async () => {
    try {
      await scrapeNow.mutateAsync({ url_id: id });
      toast.success("수집이 시작되었습니다.");
    } catch {
      toast.error("수집 시작에 실패했습니다.");
    }
  };

  if (isLoading) {
    return <div className="p-6 text-gray-400">로딩 중...</div>;
  }
  if (!url) {
    return <div className="p-6 text-gray-400">URL을 찾을 수 없습니다.</div>;
  }

  const profile = url.profile;

  return (
    <div className="p-6 space-y-6">
      {/* 헤더 */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 flex items-center gap-1"
        >
          ← 목록으로
        </button>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white flex-1 truncate">
          {url.name || url.domain}
        </h2>
        <button
          onClick={handleScrape}
          disabled={scrapeNow.isPending}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-60"
        >
          {scrapeNow.isPending ? "수집 중..." : "즉시 수집"}
        </button>
      </div>

      {/* 기본 정보 */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">기본 정보</h3>
        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-gray-500 dark:text-gray-400">URL</dt>
            <dd className="text-gray-900 dark:text-white break-all mt-0.5">
              <a href={url.url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
                {url.url}
              </a>
            </dd>
          </div>
          <div>
            <dt className="text-gray-500 dark:text-gray-400">카테고리</dt>
            <dd className="mt-0.5">
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
                {url.category}
              </span>
            </dd>
          </div>
          <div>
            <dt className="text-gray-500 dark:text-gray-400">도메인</dt>
            <dd className="text-gray-900 dark:text-white mt-0.5">{url.domain}</dd>
          </div>
          <div>
            <dt className="text-gray-500 dark:text-gray-400">상태</dt>
            <dd className="mt-0.5">
              <span className={`text-xs px-2 py-0.5 rounded-full ${url.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                {url.is_active ? "활성" : "비활성"}
              </span>
            </dd>
          </div>
          <div>
            <dt className="text-gray-500 dark:text-gray-400">등록일</dt>
            <dd className="text-gray-900 dark:text-white mt-0.5">
              {url.created_at ? format(new Date(url.created_at), "yyyy/MM/dd HH:mm") : "-"}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500 dark:text-gray-400">태그</dt>
            <dd className="mt-0.5 flex gap-1 flex-wrap">
              {url.tags?.length > 0
                ? url.tags.map((t: string) => (
                    <span key={t} className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-0.5 rounded">
                      {t}
                    </span>
                  ))
                : <span className="text-gray-400 text-xs">없음</span>
              }
            </dd>
          </div>
        </dl>
      </div>

      {/* URL Profile (학습 데이터) */}
      {profile && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">학습 프로파일</h3>
          <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
            {[
              { label: "최적 파이프라인", value: PIPELINE_LABELS[profile.best_pipeline] ?? profile.best_pipeline ?? "-" },
              { label: "성공률", value: profile.success_rate != null ? `${(profile.success_rate * 100).toFixed(1)}%` : "-" },
              { label: "총 방문", value: profile.total_visits != null ? `${profile.total_visits}회` : "-" },
              { label: "평균 응답", value: profile.avg_response_time_ms != null ? `${Math.round(profile.avg_response_time_ms)}ms` : "-" },
            ].map((item) => (
              <div key={item.label} className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                <p className="text-xs text-gray-500 dark:text-gray-400">{item.label}</p>
                <p className="text-lg font-bold text-gray-900 dark:text-white mt-1">{item.value}</p>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-3 gap-3 mt-3 text-sm">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${profile.requires_js ? "bg-yellow-400" : "bg-gray-300"}`} />
              <span className="text-gray-600 dark:text-gray-400">JavaScript 필요</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${profile.has_antibot ? "bg-red-400" : "bg-gray-300"}`} />
              <span className="text-gray-600 dark:text-gray-400">안티봇 감지됨</span>
            </div>
            {profile.antibot_type && (
              <div className="text-xs text-gray-500">유형: {profile.antibot_type}</div>
            )}
          </div>
        </div>
      )}

      {/* 방문 이력 */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">최근 방문 이력</h3>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">방문 시각</th>
              <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">파이프라인</th>
              <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">소요 시간</th>
              <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">결과</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {history?.items?.map((log: any) => (
              <tr key={log.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                  {format(new Date(log.visited_at), "MM/dd HH:mm:ss")}
                </td>
                <td className="px-4 py-3">
                  <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-0.5 rounded">
                    {PIPELINE_LABELS[log.pipeline_name] ?? log.pipeline_name}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs text-gray-500">
                  {log.duration_ms ? `${log.duration_ms}ms` : "-"}
                </td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${log.success ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>
                    {log.success ? "성공" : "실패"}
                  </span>
                  {log.healing_applied && (
                    <span className="ml-1 text-xs text-purple-500">🔧 복구</span>
                  )}
                </td>
              </tr>
            ))}
            {(!history?.items || history.items.length === 0) && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-gray-400">방문 이력이 없습니다.</td>
              </tr>
            )}
          </tbody>
        </table>
        {history && history.pages > 1 && (
          <div className="flex items-center justify-center gap-2 p-4 border-t border-gray-100 dark:border-gray-700">
            <button onClick={() => setHistoryPage((p) => Math.max(1, p - 1))} disabled={historyPage === 1}
              className="px-3 py-1 text-sm border rounded disabled:opacity-40">이전</button>
            <span className="text-sm text-gray-600">{historyPage} / {history.pages}</span>
            <button onClick={() => setHistoryPage((p) => Math.min(history.pages, p + 1))} disabled={historyPage === history.pages}
              className="px-3 py-1 text-sm border rounded disabled:opacity-40">다음</button>
          </div>
        )}
      </div>
    </div>
  );
}
