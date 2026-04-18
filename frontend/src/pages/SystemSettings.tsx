import { useState } from "react";
import toast from "react-hot-toast";

const PIPELINES = [
  { id: "api", label: "API Client (P1)", desc: "공식 API 우선 사용" },
  { id: "http", label: "HTTP + Parser (P2)", desc: "httpx + BeautifulSoup4" },
  { id: "stealth", label: "Stealth Browser (P3)", desc: "Playwright 스텔스 모드" },
  { id: "ai", label: "AI Extraction (P4)", desc: "Crawl4AI + Ollama LLM" },
  { id: "proxy", label: "Proxy + Browser (P5)", desc: "프록시 + 풀 브라우저" },
];

const DOMAIN_RATE_DEFAULTS: Record<string, { concurrent: number; delay: number }> = {
  news: { concurrent: 3, delay: 1000 },
  portal: { concurrent: 2, delay: 3000 },
  ecommerce: { concurrent: 2, delay: 2000 },
  enterprise: { concurrent: 5, delay: 1000 },
  government: { concurrent: 3, delay: 1500 },
  finance: { concurrent: 2, delay: 2000 },
};

const LLM_MODELS = ["llama3.2:8b", "llama3.2:3b", "mistral:7b", "gemma2:9b"];
const RETENTION_OPTIONS = [7, 30, 60, 90, 180, 365];

export default function SystemSettings() {
  const [pipelines, setPipelines] = useState<Record<string, boolean>>(
    Object.fromEntries(PIPELINES.map((p) => [p.id, true]))
  );
  const [rateLimits, setRateLimits] = useState(DOMAIN_RATE_DEFAULTS);
  const [proxyPoolUrl, setProxyPoolUrl] = useState("");
  const [llmModel, setLlmModel] = useState("llama3.2:8b");
  const [retentionDays, setRetentionDays] = useState(90);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    await new Promise((r) => setTimeout(r, 600));
    setSaving(false);
    toast.success("설정이 저장되었습니다.");
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">시스템 설정</h2>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-60"
        >
          {saving ? "저장 중..." : "저장"}
        </button>
      </div>

      {/* 파이프라인 활성화 */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">파이프라인 활성화</h3>
        <div className="space-y-3">
          {PIPELINES.map((p) => (
            <div key={p.id} className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-white">{p.label}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{p.desc}</p>
              </div>
              <button
                onClick={() => setPipelines((prev) => ({ ...prev, [p.id]: !prev[p.id] }))}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  pipelines[p.id] ? "bg-blue-600" : "bg-gray-300 dark:bg-gray-600"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    pipelines[p.id] ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* 도메인별 Rate Limit */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">도메인별 Rate Limit</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-700">
                <th className="pb-2 font-medium">카테고리</th>
                <th className="pb-2 font-medium">동시 요청 수</th>
                <th className="pb-2 font-medium">딜레이 (ms)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {Object.entries(rateLimits).map(([cat, cfg]) => (
                <tr key={cat}>
                  <td className="py-2 pr-4 text-gray-900 dark:text-white capitalize">{cat}</td>
                  <td className="py-2 pr-4">
                    <input
                      type="number"
                      min={1}
                      max={20}
                      value={cfg.concurrent}
                      onChange={(e) =>
                        setRateLimits((prev) => ({
                          ...prev,
                          [cat]: { ...prev[cat], concurrent: Number(e.target.value) },
                        }))
                      }
                      className="w-16 border border-gray-300 dark:border-gray-600 rounded px-2 py-1 text-sm bg-white dark:bg-gray-700 dark:text-white"
                    />
                  </td>
                  <td className="py-2">
                    <input
                      type="number"
                      min={500}
                      step={500}
                      value={cfg.delay}
                      onChange={(e) =>
                        setRateLimits((prev) => ({
                          ...prev,
                          [cat]: { ...prev[cat], delay: Number(e.target.value) },
                        }))
                      }
                      className="w-24 border border-gray-300 dark:border-gray-600 rounded px-2 py-1 text-sm bg-white dark:bg-gray-700 dark:text-white"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 프록시 풀 */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">프록시 풀 설정</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">프록시 풀 URL</label>
            <input
              type="text"
              placeholder="http://proxy-pool.example.com:8080"
              value={proxyPoolUrl}
              onChange={(e) => setProxyPoolUrl(e.target.value)}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white"
            />
            <p className="text-xs text-gray-400 mt-1">HTTP / SOCKS5 프록시 풀 엔드포인트</p>
          </div>
        </div>
      </div>

      {/* LLM 모델 */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">AI 파이프라인 설정</h3>
        <div>
          <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Ollama LLM 모델</label>
          <select
            value={llmModel}
            onChange={(e) => setLlmModel(e.target.value)}
            className="border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white"
          >
            {LLM_MODELS.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
          <p className="text-xs text-gray-400 mt-1">
            Ollama에서 미리 pull 된 모델이어야 합니다: <code className="font-mono">ollama pull {llmModel}</code>
          </p>
        </div>
      </div>

      {/* 데이터 보존 기간 */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">데이터 보존 기간</h3>
        <div className="flex gap-2 flex-wrap">
          {RETENTION_OPTIONS.map((d) => (
            <button
              key={d}
              onClick={() => setRetentionDays(d)}
              className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                retentionDays === d
                  ? "bg-blue-600 text-white border-blue-600"
                  : "border-gray-300 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
              }`}
            >
              {d}일
            </button>
          ))}
        </div>
        <p className="text-xs text-gray-400 mt-2">방문 이력 및 수집 데이터의 자동 삭제 기간</p>
      </div>
    </div>
  );
}
