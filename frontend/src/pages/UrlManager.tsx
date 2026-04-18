import { useState } from "react";
import toast from "react-hot-toast";
import { useUrls, useCreateUrl, useDeleteUrl, useScrapeNow } from "../hooks/useApi";

const CATEGORIES = ["government", "finance", "news", "portal", "sns", "ecommerce", "enterprise"];

function CategoryBadge({ category }: { category: string }) {
  const colors: Record<string, string> = {
    government: "bg-blue-100 text-blue-800",
    finance: "bg-green-100 text-green-800",
    news: "bg-yellow-100 text-yellow-800",
    portal: "bg-purple-100 text-purple-800",
    sns: "bg-pink-100 text-pink-800",
    ecommerce: "bg-orange-100 text-orange-800",
    enterprise: "bg-gray-100 text-gray-800",
  };
  const labels: Record<string, string> = {
    government: "정부", finance: "금융", news: "뉴스",
    portal: "포털", sns: "SNS", ecommerce: "쇼핑몰", enterprise: "기업",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${colors[category] ?? "bg-gray-100 text-gray-700"}`}>
      {labels[category] ?? category}
    </span>
  );
}

export default function UrlManager({ onSelectUrl }: { onSelectUrl?: (id: string) => void }) {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [newUrl, setNewUrl] = useState("");
  const [newName, setNewName] = useState("");
  const [bulkMode, setBulkMode] = useState(false);
  const [bulkText, setBulkText] = useState("");

  const { data, isLoading } = useUrls({ page, size: 20, search: search || undefined, category: categoryFilter || undefined });
  const createUrl = useCreateUrl();
  const deleteUrl = useDeleteUrl();
  const scrapeNow = useScrapeNow();

  const handleAddUrl = async () => {
    if (!newUrl.trim()) return;
    try {
      if (bulkMode) {
        const urls = bulkText.split("\n").map((u) => u.trim()).filter(Boolean).map((u) => ({ url: u }));
        await createUrl.mutateAsync({ urls });
        toast.success(`${urls.length}개 URL이 등록되었습니다.`);
      } else {
        await createUrl.mutateAsync({ url: newUrl.trim(), name: newName.trim() || undefined });
        toast.success("URL이 등록되었습니다.");
      }
      setShowAddDialog(false);
      setNewUrl("");
      setNewName("");
      setBulkText("");
    } catch (e: any) {
      toast.error(e.response?.data?.detail ?? "URL 등록에 실패했습니다.");
    }
  };

  const handleDelete = async (id: string, url: string) => {
    if (!confirm(`"${url}"을 삭제하시겠습니까?`)) return;
    await deleteUrl.mutateAsync(id);
    toast.success("URL이 삭제되었습니다.");
  };

  const handleScrapeNow = async (id: string) => {
    try {
      await scrapeNow.mutateAsync({ url_id: id });
      toast.success("수집이 시작되었습니다.");
    } catch {
      toast.error("수집 시작에 실패했습니다.");
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">URL 관리</h2>
        <button
          onClick={() => setShowAddDialog(true)}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
        >
          + URL 추가
        </button>
      </div>

      {/* 검색/필터 */}
      <div className="flex gap-3">
        <input
          type="text"
          placeholder="URL 또는 이름 검색..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="flex-1 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-800 dark:text-white"
        />
        <select
          value={categoryFilter}
          onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
          className="border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-800 dark:text-white"
        >
          <option value="">전체 카테고리</option>
          {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {/* URL 테이블 */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">로딩 중...</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">URL</th>
                <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">카테고리</th>
                <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">상태</th>
                <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">작업</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {data?.items?.map((url: any) => (
                <tr key={url.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-4 py-3">
                    <button
                      onClick={() => onSelectUrl?.(url.id)}
                      className="font-medium text-blue-600 dark:text-blue-400 hover:underline truncate max-w-xs text-left"
                    >
                      {url.name || url.domain}
                    </button>
                    <div className="text-xs text-gray-400 truncate max-w-xs">{url.url}</div>
                  </td>
                  <td className="px-4 py-3">
                    <CategoryBadge category={url.category} />
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${url.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {url.is_active ? "활성" : "비활성"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleScrapeNow(url.id)}
                        className="text-xs px-2 py-1 bg-blue-50 text-blue-600 hover:bg-blue-100 rounded transition-colors"
                      >
                        즉시 수집
                      </button>
                      <button
                        onClick={() => handleDelete(url.id, url.url)}
                        className="text-xs px-2 py-1 bg-red-50 text-red-600 hover:bg-red-100 rounded transition-colors"
                      >
                        삭제
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {(!data?.items || data.items.length === 0) && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-gray-400">
                    등록된 URL이 없습니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* 페이지네이션 */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            className="px-3 py-1 text-sm border rounded disabled:opacity-40">이전</button>
          <span className="text-sm text-gray-600">{page} / {data.pages}</span>
          <button onClick={() => setPage(p => Math.min(data.pages, p + 1))} disabled={page === data.pages}
            className="px-3 py-1 text-sm border rounded disabled:opacity-40">다음</button>
        </div>
      )}

      {/* URL 추가 다이얼로그 */}
      {showAddDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 w-full max-w-md shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">URL 추가</h3>

            <div className="flex gap-2 mb-4">
              <button onClick={() => setBulkMode(false)}
                className={`flex-1 py-1.5 text-sm rounded-lg border ${!bulkMode ? "bg-blue-600 text-white border-blue-600" : "border-gray-300 text-gray-600"}`}>
                단일 URL
              </button>
              <button onClick={() => setBulkMode(true)}
                className={`flex-1 py-1.5 text-sm rounded-lg border ${bulkMode ? "bg-blue-600 text-white border-blue-600" : "border-gray-300 text-gray-600"}`}>
                여러 URL
              </button>
            </div>

            {!bulkMode ? (
              <div className="space-y-3">
                <input
                  type="url"
                  placeholder="https://example.com"
                  value={newUrl}
                  onChange={(e) => setNewUrl(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                />
                <input
                  type="text"
                  placeholder="이름 (선택)"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                />
              </div>
            ) : (
              <textarea
                placeholder={"URL을 줄바꿈으로 구분하여 입력하세요\nhttps://example.com\nhttps://example.org"}
                value={bulkText}
                onChange={(e) => setBulkText(e.target.value)}
                rows={6}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono"
              />
            )}

            <div className="flex gap-2 mt-4">
              <button onClick={() => setShowAddDialog(false)}
                className="flex-1 py-2 text-sm border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50">
                취소
              </button>
              <button onClick={handleAddUrl} disabled={createUrl.isPending}
                className="flex-1 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60">
                {createUrl.isPending ? "등록 중..." : "등록"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
