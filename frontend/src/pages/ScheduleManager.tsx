import { useState } from "react";
import toast from "react-hot-toast";
import { format } from "date-fns";
import { useSchedules, useCreateSchedule, useDeleteSchedule } from "../hooks/useApi";

const SCHEDULE_TYPES = [
  { id: "hourly", label: "매 N시간", example: "0 */2 * * *" },
  { id: "daily", label: "매일", example: "0 9 * * *" },
  { id: "weekly", label: "매주", example: "0 9 * * 1" },
  { id: "monthly", label: "매월", example: "0 9 1 * *" },
  { id: "custom", label: "커스텀 cron", example: "*/30 * * * *" },
];

export default function ScheduleManager() {
  const [showDialog, setShowDialog] = useState(false);
  const [selectedUrlId, setSelectedUrlId] = useState("");
  const [scheduleType, setScheduleType] = useState("daily");
  const [cronExpr, setCronExpr] = useState("0 9 * * *");

  const { data: schedules, isLoading } = useSchedules();
  const createSchedule = useCreateSchedule();
  const deleteSchedule = useDeleteSchedule();

  const handleCreate = async () => {
    if (!selectedUrlId || !cronExpr) {
      toast.error("URL ID와 cron 표현식을 입력해주세요.");
      return;
    }
    try {
      await createSchedule.mutateAsync({
        url_id: selectedUrlId,
        schedule_type: scheduleType,
        cron_expression: cronExpr,
        timezone: "Asia/Seoul",
      });
      toast.success("스케줄이 등록되었습니다.");
      setShowDialog(false);
    } catch (e: any) {
      toast.error(e.response?.data?.detail ?? "스케줄 등록에 실패했습니다.");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("스케줄을 삭제하시겠습니까?")) return;
    await deleteSchedule.mutateAsync(id);
    toast.success("스케줄이 삭제되었습니다.");
  };

  const handleTypeChange = (type: string) => {
    setScheduleType(type);
    const preset = SCHEDULE_TYPES.find((t) => t.id === type);
    if (preset) setCronExpr(preset.example);
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">스케줄 관리</h2>
        <button
          onClick={() => setShowDialog(true)}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
        >
          + 스케줄 추가
        </button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">로딩 중...</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">Cron</th>
                <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">유형</th>
                <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">다음 실행</th>
                <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">실행/성공</th>
                <th className="text-left px-4 py-3 text-gray-600 dark:text-gray-300 font-medium">상태</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {(schedules ?? []).map((s: any) => (
                <tr key={s.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-4 py-3 font-mono text-xs">{s.cron_expression}</td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{s.schedule_type}</td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-300 text-xs">
                    {s.next_run_at ? format(new Date(s.next_run_at), "MM/dd HH:mm") : "-"}
                  </td>
                  <td className="px-4 py-3 text-xs">
                    <span className="text-gray-500">{s.run_count}회</span> /
                    <span className="text-green-600 ml-1">{s.success_count}성공</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${s.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {s.is_active ? "활성" : "정지"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleDelete(s.id)}
                      className="text-xs text-red-500 hover:text-red-700"
                    >
                      삭제
                    </button>
                  </td>
                </tr>
              ))}
              {(!schedules || schedules.length === 0) && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                    등록된 스케줄이 없습니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {showDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 w-full max-w-md shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">스케줄 추가</h3>

            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">URL ID</label>
                <input
                  type="text"
                  placeholder="URL UUID 입력"
                  value={selectedUrlId}
                  onChange={(e) => setSelectedUrlId(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">스케줄 유형</label>
                <div className="grid grid-cols-3 gap-2">
                  {SCHEDULE_TYPES.map((t) => (
                    <button
                      key={t.id}
                      onClick={() => handleTypeChange(t.id)}
                      className={`py-1.5 text-xs rounded-lg border transition-colors ${
                        scheduleType === t.id
                          ? "bg-blue-600 text-white border-blue-600"
                          : "border-gray-300 text-gray-600 hover:bg-gray-50"
                      }`}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Cron 표현식
                </label>
                <input
                  type="text"
                  value={cronExpr}
                  onChange={(e) => setCronExpr(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono"
                />
                <p className="text-xs text-gray-400 mt-1">예: 매일 09:00 = "0 9 * * *"</p>
              </div>
            </div>

            <div className="flex gap-2 mt-4">
              <button onClick={() => setShowDialog(false)}
                className="flex-1 py-2 text-sm border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50">
                취소
              </button>
              <button onClick={handleCreate} disabled={createSchedule.isPending}
                className="flex-1 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60">
                {createSchedule.isPending ? "등록 중..." : "등록"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
