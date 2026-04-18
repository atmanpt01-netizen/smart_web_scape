import { useState } from "react";
import { Toaster } from "react-hot-toast";
import Dashboard from "./pages/Dashboard";
import UrlManager from "./pages/UrlManager";
import UrlDetail from "./pages/UrlDetail";
import ScheduleManager from "./pages/ScheduleManager";
import VisitHistory from "./pages/VisitHistory";
import VisitDetail from "./pages/VisitDetail";
import Analytics from "./pages/Analytics";
import SystemSettings from "./pages/SystemSettings";
import NotificationSettings from "./pages/NotificationSettings";

type Page = "dashboard" | "urls" | "schedules" | "history" | "analytics" | "settings" | "notifications";
type DetailView = { type: "url"; id: string } | { type: "visit"; id: string } | null;

const NAV_ITEMS: { id: Page; label: string; icon: string }[] = [
  { id: "dashboard", label: "대시보드", icon: "📊" },
  { id: "urls", label: "URL 관리", icon: "🔗" },
  { id: "schedules", label: "스케줄", icon: "🗓️" },
  { id: "history", label: "방문 이력", icon: "📋" },
  { id: "analytics", label: "분석", icon: "📈" },
  { id: "settings", label: "시스템 설정", icon: "⚙️" },
  { id: "notifications", label: "알림 설정", icon: "🔔" },
];

export default function App() {
  const [currentPage, setCurrentPage] = useState<Page>("dashboard");
  const [isDark, setIsDark] = useState(false);
  const [detail, setDetail] = useState<DetailView>(null);

  const navigate = (page: Page) => {
    setDetail(null);
    setCurrentPage(page);
  };

  const renderPage = () => {
    if (detail?.type === "url") return <UrlDetail id={detail.id} onBack={() => setDetail(null)} />;
    if (detail?.type === "visit") return <VisitDetail id={detail.id} onBack={() => setDetail(null)} />;
    switch (currentPage) {
      case "dashboard": return <Dashboard />;
      case "urls": return <UrlManager onSelectUrl={(id) => setDetail({ type: "url", id })} />;
      case "schedules": return <ScheduleManager />;
      case "history": return <VisitHistory onSelectVisit={(id) => setDetail({ type: "visit", id })} />;
      case "analytics": return <Analytics />;
      case "settings": return <SystemSettings />;
      case "notifications": return <NotificationSettings />;
    }
  };

  return (
    <div className={isDark ? "dark" : ""}>
      <div className="min-h-screen flex bg-gray-50 dark:bg-gray-900">
        {/* 사이드바 */}
        <aside className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <h1 className="text-lg font-bold text-gray-900 dark:text-white">
              🕷️ Smart Web Scraper
            </h1>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              지능형 웹 수집 플랫폼
            </p>
          </div>

          <nav className="flex-1 p-3 space-y-1">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                onClick={() => navigate(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  currentPage === item.id
                    ? "bg-blue-50 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300"
                    : "text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                }`}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </button>
            ))}
          </nav>

          <div className="p-3 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={() => setIsDark(!isDark)}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            >
              <span>{isDark ? "☀️" : "🌙"}</span>
              <span>{isDark ? "라이트 모드" : "다크 모드"}</span>
            </button>
          </div>
        </aside>

        {/* 메인 콘텐츠 */}
        <main className="flex-1 overflow-auto">
          {renderPage()}
        </main>
      </div>
      <Toaster position="top-right" />
    </div>
  );
}
