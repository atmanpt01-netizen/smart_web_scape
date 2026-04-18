import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell, BarChart, Bar, ResponsiveContainer,
} from "recharts";
import {
  useDashboardSummary,
  useSuccessRateTrend,
  usePipelineStats,
  useCategoryStats,
  useAlerts,
  useUpcomingSchedules,
} from "../hooks/useApi";
import { useWebSocket } from "../hooks/useWebSocket";
import { format } from "date-fns";

const PIPELINE_COLORS: Record<string, string> = {
  api: "#3B82F6",
  http: "#10B981",
  stealth: "#F59E0B",
  ai: "#8B5CF6",
  proxy: "#EF4444",
};

function KpiCard({ title, value, subtitle }: { title: string; value: string | number; subtitle?: string }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
      <p className="text-sm text-gray-500 dark:text-gray-400">{title}</p>
      <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{value}</p>
      {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
    </div>
  );
}

export default function Dashboard() {
  const { data: summary } = useDashboardSummary();
  const { data: trend } = useSuccessRateTrend(30);
  const { data: pipelineStats } = usePipelineStats();
  const { data: categoryStats } = useCategoryStats();
  const { data: alerts } = useAlerts({ is_read: false, limit: 5 });
  const { data: upcoming } = useUpcomingSchedules();
  const { messages: liveEvents, status: wsStatus } = useWebSocket("/ws/live-feed");

  const trendData = (trend ?? []).map((d: Record<string, unknown>) => ({
    date: d.date,
    성공률: Math.round(Number(d.success_rate) * 100),
  }));

  const pieData = (pipelineStats ?? []).map((d: Record<string, unknown>) => ({
    name: d.pipeline as string,
    value: d.count as number,
  }));

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">대시보드</h2>
        <span className={`text-xs px-2 py-1 rounded-full ${wsStatus === "connected" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>
          {wsStatus === "connected" ? "● 실시간 연결" : "● 연결 끊김"}
        </span>
      </div>

      {/* KPI 카드 */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <KpiCard title="총 URL" value={summary?.total_urls ?? "-"} />
        <KpiCard title="활성 URL" value={summary?.active_urls ?? "-"} />
        <KpiCard
          title="성공률 (7일)"
          value={summary ? `${(summary.success_rate * 100).toFixed(1)}%` : "-"}
        />
        <KpiCard title="오늘 수집" value={summary?.today_items ?? "-"} subtitle="건" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* 성공률 추이 */}
        <div className="xl:col-span-2 bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">성공률 추이 (30일)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v) => v?.slice(5) ?? ""} />
              <YAxis unit="%" domain={[0, 100]} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v) => `${v}%`} />
              <Line type="monotone" dataKey="성공률" stroke="#3B82F6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* 파이프라인 분포 */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">파이프라인 분포</h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value" label={({ name }) => name}>
                  {pieData.map((entry: { name: string; value: number }, i: number) => (
                    <Cell key={i} fill={PIPELINE_COLORS[entry.name] ?? "#94A3B8"} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 text-center mt-8">데이터 없음</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* 카테고리별 성공률 */}
        <div className="xl:col-span-2 bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">카테고리별 성공률</h3>
          {categoryStats && categoryStats.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={categoryStats} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" unit="%" domain={[0, 100]} tick={{ fontSize: 11 }} />
                <YAxis dataKey="category" type="category" tick={{ fontSize: 11 }} width={80} />
                <Tooltip formatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
                <Bar dataKey="success_rate" fill="#10B981" name="성공률" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 text-center mt-8">데이터 없음</p>
          )}
        </div>

        {/* 사이드 패널: 알림 + 다음 스케줄 */}
        <div className="space-y-4">
          {/* 알림 */}
          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">미확인 알림</h3>
            {alerts && alerts.length > 0 ? (
              <ul className="space-y-2">
                {alerts.slice(0, 3).map((alert: Record<string, string>) => (
                  <li key={alert.id} className="text-xs text-gray-600 dark:text-gray-400 border-l-2 border-yellow-400 pl-2">
                    {alert.message}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-gray-400">알림 없음</p>
            )}
          </div>

          {/* 다음 스케줄 */}
          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">다음 실행 예정</h3>
            {upcoming && upcoming.length > 0 ? (
              <ul className="space-y-2">
                {upcoming.slice(0, 3).map((s: Record<string, string>) => (
                  <li key={s.id} className="text-xs text-gray-600 dark:text-gray-400">
                    <span className="font-mono">{s.cron_expression}</span>
                    <br />
                    <span className="text-gray-400">
                      {s.next_run_at ? format(new Date(s.next_run_at), "MM/dd HH:mm") : "-"}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-gray-400">예정된 스케줄 없음</p>
            )}
          </div>
        </div>
      </div>

      {/* 실시간 방문 피드 */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">실시간 방문 피드</h3>
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {liveEvents.length === 0 ? (
            <p className="text-xs text-gray-400">수집 이벤트를 기다리는 중...</p>
          ) : (
            liveEvents.map((event: any, i) => (
              <div key={i} className="flex items-center gap-2 text-xs py-1 border-b border-gray-100 dark:border-gray-700">
                <span className={event.data?.success ? "text-green-500" : "text-red-500"}>
                  {event.data?.success ? "✓" : "✗"}
                </span>
                <span className="text-gray-500 font-mono">[{event.data?.pipeline_name}]</span>
                <span className="text-gray-700 dark:text-gray-300 truncate">{event.data?.url}</span>
                <span className="text-gray-400 ml-auto">{event.data?.duration_ms}ms</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
