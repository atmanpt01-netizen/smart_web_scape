import { useState } from "react";
import toast from "react-hot-toast";

export default function NotificationSettings() {
  const [slackWebhook, setSlackWebhook] = useState("");
  const [slackEnabled, setSlackEnabled] = useState(false);
  const [smtpHost, setSmtpHost] = useState("smtp.gmail.com");
  const [smtpPort, setSmtpPort] = useState(587);
  const [smtpUser, setSmtpUser] = useState("");
  const [smtpPass, setSmtpPass] = useState("");
  const [smtpFrom, setSmtpFrom] = useState("");
  const [emailEnabled, setEmailEnabled] = useState(false);
  const [failThreshold, setFailThreshold] = useState(5);
  const [testingSlack, setTestingSlack] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleTestSlack = async () => {
    if (!slackWebhook) { toast.error("Slack Webhook URL을 입력해주세요."); return; }
    setTestingSlack(true);
    await new Promise((r) => setTimeout(r, 800));
    setTestingSlack(false);
    toast.success("Slack 테스트 메시지를 전송했습니다.");
  };

  const handleSave = async () => {
    setSaving(true);
    await new Promise((r) => setTimeout(r, 600));
    setSaving(false);
    toast.success("알림 설정이 저장되었습니다.");
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">알림 설정</h2>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-60"
        >
          {saving ? "저장 중..." : "저장"}
        </button>
      </div>

      {/* 알림 규칙 */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">알림 조건</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              연속 실패 알림 임계값
            </label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={1}
                max={20}
                value={failThreshold}
                onChange={(e) => setFailThreshold(Number(e.target.value))}
                className="w-40"
              />
              <span className="text-sm font-semibold text-gray-900 dark:text-white w-16">
                {failThreshold}회 연속
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-1">동일 URL에서 N회 연속 실패 시 알림 발송</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {[
              { label: "안티봇 감지 시 알림", key: "antibot" },
              { label: "Self-Healing 실패 시 알림", key: "healing_fail" },
              { label: "스케줄 실행 실패 알림", key: "schedule_fail" },
              { label: "시스템 오류 알림", key: "system_error" },
            ].map((item) => (
              <label key={item.key} className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
                <input type="checkbox" defaultChecked className="rounded" />
                {item.label}
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Slack */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Slack 알림</h3>
          <button
            onClick={() => setSlackEnabled(!slackEnabled)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              slackEnabled ? "bg-blue-600" : "bg-gray-300 dark:bg-gray-600"
            }`}
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${slackEnabled ? "translate-x-6" : "translate-x-1"}`} />
          </button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Incoming Webhook URL</label>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="https://hooks.slack.com/services/..."
                value={slackWebhook}
                onChange={(e) => setSlackWebhook(e.target.value)}
                disabled={!slackEnabled}
                className="flex-1 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white disabled:opacity-50"
              />
              <button
                onClick={handleTestSlack}
                disabled={!slackEnabled || testingSlack}
                className="px-3 py-2 text-sm border border-gray-300 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
              >
                {testingSlack ? "전송 중..." : "테스트"}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Email / SMTP */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">이메일 알림 (SMTP)</h3>
          <button
            onClick={() => setEmailEnabled(!emailEnabled)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              emailEnabled ? "bg-blue-600" : "bg-gray-300 dark:bg-gray-600"
            }`}
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${emailEnabled ? "translate-x-6" : "translate-x-1"}`} />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">SMTP 호스트</label>
            <input
              type="text"
              value={smtpHost}
              onChange={(e) => setSmtpHost(e.target.value)}
              disabled={!emailEnabled}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white disabled:opacity-50"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">포트</label>
            <input
              type="number"
              value={smtpPort}
              onChange={(e) => setSmtpPort(Number(e.target.value))}
              disabled={!emailEnabled}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white disabled:opacity-50"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">사용자 이름</label>
            <input
              type="text"
              placeholder="user@gmail.com"
              value={smtpUser}
              onChange={(e) => setSmtpUser(e.target.value)}
              disabled={!emailEnabled}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white disabled:opacity-50"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">비밀번호 / 앱 패스워드</label>
            <input
              type="password"
              value={smtpPass}
              onChange={(e) => setSmtpPass(e.target.value)}
              disabled={!emailEnabled}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white disabled:opacity-50"
            />
          </div>
          <div className="col-span-2">
            <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">발신자 주소</label>
            <input
              type="email"
              placeholder="noreply@example.com"
              value={smtpFrom}
              onChange={(e) => setSmtpFrom(e.target.value)}
              disabled={!emailEnabled}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white disabled:opacity-50"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
