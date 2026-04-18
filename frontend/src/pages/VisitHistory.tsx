import { useState } from "react";
import { format } from "date-fns";
import { useHistory } from "../hooks/useApi";

const PIPELINE_LABELS: Record<string, string> = {
  api: "API", http: "HTTP", stealth: "스텔스", ai: "AI", proxy: "프록시",
};

export default function VisitHistory({ onSelectVisit }: { onSelectVisit?: (id: string) => void }) {
  const [page, setPage] = useState(1);
  const [success, setSuccess] = useState<string>("");
  const [pipeline, setPipeline] = useState("");

  const params: Record<string, unknown> = { page, size: 20 };
  if (success !== "") params.success = success === "true";
  if (pipeline) params.pipeline_name = pipeline;

  const { data, isLoading } = useHistory(params);

  return (
    <div className="p-6 space-y-4">
      <h2 className="text-xl font-bold text-gray-900 dark:text-white">방문 이력</h2>

      {/* 필터 */}
      <div className="flex gap-3">
        <select
          value={success}
          onChange={(e) => { setSuccess(e.target.value); setPage(1); }}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-800 dark:text-white"
        >
          <option value="">전체</option>
          <option value="true">성공만</option>
          <option value="false">실패만</option>
        </select>

        <select
          value={pipeline}
          onChange={(e) => { setPipeline(e.target.value); setPage(1); }}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-800 dark:text-white"
        >
          <option value="">전체 파이프라인</option>
          {Object.entries(PIPELINE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>

        <a
          href="/api/v1/history/export?format=csv"
          className="ml-auto px-4 py-2 text-sm border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 transition-colors"
          download
        >
          CSV 내보내기
        </a>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">로딩 중...</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">URL</th>
                <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">방문 시각</th>
                <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">파이프라인</th>
                <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">소요 시간</th>
                <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">결과</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {data?.items?.map((log: any) => (
                <tr key={log.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer" onClick={() => onSelectVisit?.(log.id)}>
                  <td className="px-4 py-3">
                    <div className="text-xs text-blue-600 dark:text-blue-400 truncate max-w-xs hover:underline">{log.url}</div>
                    {log.error_message && (
                      <div className="text-xs text-red-400 truncate max-w-xs mt-0.5">{log.error_message}</div>
                    )}
                  </td>
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
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      log.success ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"
                    }`}>
                      {log.success ? "성공" : "실패"}
                    </span>
                    {log.healing_applied && (
                      <span className="ml-1 text-xs text-purple-500">🔧 복구</span>
                    )}
                  </td>
                </tr>
              ))}
              {(!data?.items || data.items.length === 0) && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                    방문 이력이 없습니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {data && data.pages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            className="px-3 py-1 text-sm border rounded disabled:opacity-40">이전</button>
          <span className="text-sm text-gray-600">{page} / {data.pages}</span>
          <button onClick={() => setPage(p => Math.min(data.pages, p + 1))} disabled={page === data.pages}
            className="px-3 py-1 text-sm border rounded disabled:opacity-40">다음</button>
        </div>
      )}
    </div>
  );
}
