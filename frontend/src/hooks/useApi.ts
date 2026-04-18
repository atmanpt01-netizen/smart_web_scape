import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";

const api = axios.create({ baseURL: "/api/v1" });

// ─── URL API ──────────────────────────────────────────────

export function useUrls(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ["urls", params],
    queryFn: () => api.get("/urls", { params }).then((r) => r.data),
  });
}

export function useUrl(id: string) {
  return useQuery({
    queryKey: ["urls", id],
    queryFn: () => api.get(`/urls/${id}`).then((r) => r.data),
    enabled: !!id,
  });
}

export function useCreateUrl() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: unknown) => api.post("/urls", data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["urls"] }),
  });
}

export function useUpdateUrl() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: unknown }) =>
      api.put(`/urls/${id}`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["urls"] }),
  });
}

export function useDeleteUrl() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/urls/${id}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["urls"] }),
  });
}

export function useScrapeNow() {
  return useMutation({
    mutationFn: (data: { url_id: string }) =>
      api.post("/scrape/now", data).then((r) => r.data),
  });
}

// ─── Dashboard API ─────────────────────────────────────────

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: () => api.get("/dashboard/summary").then((r) => r.data),
    refetchInterval: 30_000,
  });
}

export function useSuccessRateTrend(days = 30) {
  return useQuery({
    queryKey: ["dashboard", "success-rate", days],
    queryFn: () =>
      api.get("/dashboard/success-rate", { params: { days } }).then((r) => r.data),
    refetchInterval: 60_000,
  });
}

export function usePipelineStats() {
  return useQuery({
    queryKey: ["dashboard", "pipeline-stats"],
    queryFn: () => api.get("/dashboard/pipeline-stats").then((r) => r.data),
    refetchInterval: 60_000,
  });
}

export function useCategoryStats() {
  return useQuery({
    queryKey: ["dashboard", "category-stats"],
    queryFn: () => api.get("/dashboard/category-stats").then((r) => r.data),
    refetchInterval: 60_000,
  });
}

export function useAlerts(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ["alerts", params],
    queryFn: () => api.get("/dashboard/alerts", { params }).then((r) => r.data),
    refetchInterval: 15_000,
  });
}

export function useUpcomingSchedules() {
  return useQuery({
    queryKey: ["schedules", "upcoming"],
    queryFn: () => api.get("/dashboard/schedules/upcoming").then((r) => r.data),
    refetchInterval: 30_000,
  });
}

// ─── Schedule API ─────────────────────────────────────────

export function useSchedules(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ["schedules", params],
    queryFn: () => api.get("/schedules", { params }).then((r) => r.data),
  });
}

export function useCreateSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: unknown) => api.post("/schedules", data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["schedules"] }),
  });
}

export function useDeleteSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/schedules/${id}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["schedules"] }),
  });
}

// ─── History API ──────────────────────────────────────────

export function useHistory(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ["history", params],
    queryFn: () => api.get("/history", { params }).then((r) => r.data),
  });
}

export function useVisitLog(id: string) {
  return useQuery({
    queryKey: ["history", id],
    queryFn: () => api.get(`/history/${id}`).then((r) => r.data),
    enabled: !!id,
  });
}

// ─── Settings API ─────────────────────────────────────────

export function useSystemSettings() {
  return useQuery({
    queryKey: ["settings", "system"],
    queryFn: () => api.get("/settings/system").then((r) => r.data),
  });
}

export function useUpdateSystemSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: unknown) => api.put("/settings/system", data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings"] }),
  });
}

export function useNotificationSettings() {
  return useQuery({
    queryKey: ["settings", "notifications"],
    queryFn: () => api.get("/settings/notifications").then((r) => r.data),
  });
}

export function useUpdateNotificationSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: unknown) => api.put("/settings/notifications", data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings"] }),
  });
}

export function useTestSlack() {
  return useMutation({
    mutationFn: (webhookUrl: string) =>
      api.post("/settings/notifications/test-slack", { webhook_url: webhookUrl }).then((r) => r.data),
  });
}
