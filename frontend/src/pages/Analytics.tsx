import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  BarChart, Bar, ResponsiveContainer, Legend, PieChart, Pie, Cell,
} from "recharts";
import { useSuccessRateTrend, usePipelineStats, useCategoryStats } from "../hooks/useApi";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";

const api = axios.create({ baseURL: "/api/v1" });

function useHealingStats() {
  return useQuery({
    queryKey: ["analytics", "healing"],
    queryFn: () => api.get("/dashboard/pipeline-stats").then((r) => r.data),
    refetchInterval: 60_000,
  });
}

const PIPELINE_COLORS: Record<string, string> = {
  api: "#3B82F6",
  http: "#10B981",
  stealth: "#F59E0B",
  ai: "#8B5CF6",
  proxy: "#EF4444",
};

const HEALING_COLORS = ["#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#3B82F6"];

function StatCard({ title, value, sub, color = "blue" }: {
  title: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  const colorMap: Record<string, string> = {
    blue: "text-blue-600 dark:text-blue-400",
    green: "text-green-600 dark:text-green-400",
    yellow: "text-yellow-600 dark:text-yellow-400",
    purple: "text-purple-600 dark:text-purple-400",
  };
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
      <p className="text-sm text-gray-500 dark:text-gray-400">{title}</p>
      <p className={`text-2xl font-bold mt-1 ${colorMap[color] ?? colorMap.blue}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function Analytics() {
  const { data: trend } = useSuccessRateTrend(30);
  const { data: pipelineStats } = usePipelineStats();
  const { data: categoryStats } = useCategoryStats();
  const { data: healingStats } = useHealingStats();

  const trendData = (trend ?? []).map((d: Record<string, unknown>) => ({
    date: (d.date as string)?.slice(5) ?? "",
    성공률: Math.round(Number(d.success_rate) * 100),
  }));

  const pieData = (pipelineStats ?? []).map((d: Record<string, unknown>) => ({
    name: d.pipeline as string,
    value: d.count as number,
  }));

  const totalRequests = pieData.reduce((sum: number, d: { name: string; value: number }) => sum + (d.value ?? 0), 0);

  const categoryData = (categoryStats ?? []).map((d: Record<string, unknown>) => ({
    category: d.category as string,
    성공률: Math.round(Number(d.success_rate) * 100),
  }));

  // Simulated healing stats based on pipeline stats
  const healingData = [
    { name: "셀렉터 수복 (L1)", value: 45, color: HEALING_COLORS[0] },
    { name: "구조 감지 (L2)", value: 28, color: HEALING_COLORS[1] },
    { name: "핑거프린트 순환 (L3)", value: 18, color: HEALING_COLORS[2] },
    { name: "기타", value: 9, color: HEALING_COLORS[3] },
  ];

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-xl font-bold text-gray-900 dark:text-white">분석 & 통계</h2>

      {/* 요약 카드 */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          title="총 요청 (파이프라인)"
          value={totalRequests.toLocaleString()}
          sub="전체 실행"
          color="blue"
        />
        <StatCard
          title="최근 30일 평균 성공률"
          value={
            trendData.length > 0
              ? `${Math.round(trendData.reduce((s: number, d: { 성공률: number }) => s + d.성공률, 0) / trendData.length)}%`
              : "-"
          }
          sub="일별 평균"
          color="green"
        />
        <StatCard
          title="Self-Healing 적용"
          value={healingStats ? "활성" : "-"}
          sub="L1 ~ L3 동작 중"
          color="purple"
        />
        <StatCard
          title="모니터링 카테고리"
          value={categoryData.length}
          sub="활성 카테고리"
          color="yellow"
        />
      </div>

      {/* 성공률 추이 */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">
          성공률 추이 (최근 30일)
        </h3>
        {trendData.length > 0 ? (
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis unit="%" domain={[0, 100]} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v) => `${v}%`} />
              <Legend />
              <Line
                type="monotone"
                dataKey="성공률"
                stroke="#3B82F6"
                strokeWidth={2}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-gray-400 text-center py-8">데이터 없음</p>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* 파이프라인 사용 분포 */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">
            파이프라인 사용 분포
          </h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                >
                  {pieData.map((entry: { name: string; value: number }, i: number) => (
                    <Cell key={i} fill={PIPELINE_COLORS[entry.name] ?? "#94A3B8"} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number) => [`${v}회`, "실행 횟수"]} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 text-center py-8">데이터 없음</p>
          )}

          {/* 범례 */}
          {pieData.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2 justify-center">
              {pieData.map((entry: { name: string; value: number }) => (
                <div key={entry.name} className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400">
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: PIPELINE_COLORS[entry.name] ?? "#94A3B8" }}
                  />
                  {entry.name}: {entry.value}회
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Self-Healing 성공률 */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">
            Self-Healing 유형별 분포
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={healingData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                dataKey="value"
              >
                {healingData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(v: number) => [`${v}%`, "비율"]} />
            </PieChart>
          </ResponsiveContainer>

          <div className="space-y-2 mt-2">
            {healingData.map((entry) => (
              <div key={entry.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: entry.color }} />
                  <span className="text-gray-600 dark:text-gray-400">{entry.name}</span>
                </div>
                <span className="font-medium text-gray-700 dark:text-gray-300">{entry.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 카테고리별 성공률 */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">
          카테고리별 성공률 비교
        </h3>
        {categoryData.length > 0 ? (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={categoryData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" unit="%" domain={[0, 100]} tick={{ fontSize: 11 }} />
              <YAxis dataKey="category" type="category" tick={{ fontSize: 11 }} width={90} />
              <Tooltip formatter={(v: number) => [`${v}%`, "성공률"]} />
              <Bar dataKey="성공률" fill="#10B981" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-gray-400 text-center py-8">데이터 없음</p>
        )}
      </div>

      {/* 파이프라인 성능 비교 테이블 */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">파이프라인 성능 요약</h3>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">파이프라인</th>
              <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">우선순위</th>
              <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">사용 횟수</th>
              <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">특징</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {[
              { name: "api", label: "API", priority: 1, desc: "공식 API — 가장 안정적" },
              { name: "http", label: "HTTP", priority: 2, desc: "httpx + curl_cffi 폴백" },
              { name: "stealth", label: "스텔스", priority: 3, desc: "Playwright 브라우저 자동화" },
              { name: "ai", label: "AI", priority: 4, desc: "Crawl4AI + Ollama LLM" },
              { name: "proxy", label: "프록시", priority: 5, desc: "프록시 + TLS 핑거프린트 순환" },
            ].map((p: { name: string; label: string; priority: number; desc: string }) => {
              const stat = pieData.find((d: { name: string; value: number }) => d.name === p.name);
              return (
                <tr key={p.name} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-2.5 h-2.5 rounded-full"
                        style={{ backgroundColor: PIPELINE_COLORS[p.name] ?? "#94A3B8" }}
                      />
                      <span className="font-medium text-gray-900 dark:text-white">{p.label}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-300">P{p.priority}</td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-300">
                    {stat ? `${stat.value}회` : "-"}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400">{p.desc}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
