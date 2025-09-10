import { z } from "zod";

export const SearchRequestSchema = z.object({
  query: z.string().optional(),
  page: z.number().int().min(1).default(1),
  per_page: z.number().int().min(1).max(100).default(20),
  sort: z.string().optional(),
  filters: z.record(z.string(), z.array(z.string())).optional()
});
export type SearchRequest = z.infer<typeof SearchRequestSchema>;

export const CompanySchema = z.object({
  source_id: z.string(),
  name: z.string(),
  lat: z.number().optional(),
  lng: z.number().optional(),
  events: z.array(z.string()).optional()
});

export const SearchResponseSchema = z.object({
  results: z.array(CompanySchema),
  total: z.number(),
  facets: z.record(z.string(), z.array(z.object({
    value: z.string(),
    count: z.number()
  }))).optional()
});
export type SearchResponse = z.infer<typeof SearchResponseSchema>;

export const ExportRequestSchema = z.object({
  format: z.enum(["csv", "xlsx", "parquet"]),
  preset: z.enum(["core", "sales", "full"]),
  columns: z.array(z.string()).optional(),
  ids: z.array(z.string()).optional(),
  filters: z.any().optional()
});
export type ExportRequest = z.infer<typeof ExportRequestSchema>;

export const ImportResponseSchema = z.object({
  import_label: z.string(),
  s3_key: z.string(),
  task_id: z.string()
});
export type ImportResponse = z.infer<typeof ImportResponseSchema>;
