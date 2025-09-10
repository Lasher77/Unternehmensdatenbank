import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "./api";
import { env } from "./env";
import { SearchRequest, SearchResponse, ImportResponse } from "./schemas";
import { sleep } from "./utils";

export function useSearchCompanies(params: SearchRequest) {
  return useQuery<SearchResponse>({
    queryKey: ["search", params],
    queryFn: async () => {
      const { data } = await api.post<SearchResponse>("/api/search/companies", params);
      return data;
    },
    keepPreviousData: true
  });
}

export function useCompanyDetail(id: string) {
  return useQuery({
    queryKey: ["company", id],
    enabled: !!id,
    queryFn: async () => {
      const { data } = await api.get(`/api/companies/${id}`);
      return data;
    }
  });
}

export function useCreateExport() {
  return useMutation({
    mutationFn: async (body: any) => {
      const { data } = await api.post("/api/exports", body);
      return data;
    }
  });
}

export function useCreateImport() {
  return useMutation({
    mutationFn: async ({ label, file, onUploadProgress }: { label: string; file: File; onUploadProgress?: (e: ProgressEvent) => void; }) => {
      const form = new FormData();
      form.append("label", label);
      form.append("file", file);
      const { data } = await api.post<ImportResponse>("/api/imports", form, { onUploadProgress });
      return data;
    }
  });
}

export function useTaskPoller(taskId?: string) {
  return useQuery<{ state: string }>({
    queryKey: ["task", taskId],
    enabled: !!taskId,
    queryFn: async () => {
      if (env.fakeTaskPoll) {
        await sleep(2000);
        return { state: "SUCCESS" };
      }
      const { data } = await api.get(`/api/tasks/${taskId}`);
      return data;
    },
    refetchInterval: 2000
  });
}
