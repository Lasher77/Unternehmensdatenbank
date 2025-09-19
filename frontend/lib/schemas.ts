import { z } from "zod";

export const SearchRequestSchema = z.object({
  // Free text search query
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
  // Matching companies for the search request
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

export const ImportSummaryResponseSchema = z.object({
  run_id: z.number(),
  summary: z.record(z.string(), z.number()).default({}),
  finished: z.boolean(),
  finished_at: z.string().nullable().optional()
});
export type ImportSummaryResponse = z.infer<typeof ImportSummaryResponseSchema>;

export const EventSchema = z.object({
  event_id: z.number().optional(),
  event_date: z.string().optional(),
  event_type: z.string().optional(),
  description: z.string().optional()
});
export type Event = z.infer<typeof EventSchema>;

export const PersonRoleSchema = z.object({
  role_name: z.string().optional(),
  role_type: z.string().optional(),
  role_date: z.string().optional()
});

export const PersonSchema = z.object({
  source_person_id: z.string(),
  first_name: z.string().optional(),
  last_name: z.string().optional(),
  birth_date: z.string().optional(),
  roles: z.array(PersonRoleSchema)
});
export type Person = z.infer<typeof PersonSchema>;

export const IndustryCodeSchema = z.object({
  scheme: z.string(),
  code: z.string()
});

export const CompanyDetailCompanySchema = CompanySchema.extend({
  raw_name: z.string().optional(),
  legal_form: z.string().optional(),
  street: z.string().optional(),
  postal_code: z.string().optional(),
  city: z.string().optional(),
  state: z.string().optional(),
  country: z.string().optional(),
  register_id: z.string().optional(),
  register_city: z.string().optional(),
  register_country: z.string().optional(),
  register_unique_key: z.string().optional(),
  status: z.string().optional(),
  terminated: z.boolean().optional()
});
export type CompanyDetailCompany = z.infer<typeof CompanyDetailCompanySchema>;

export const CompanyDetailResponseSchema = z.object({
  company: CompanyDetailCompanySchema,
  events: z.array(EventSchema),
  persons: z.array(PersonSchema),
  industry_codes: z.array(IndustryCodeSchema)
});
export type CompanyDetailResponse = z.infer<typeof CompanyDetailResponseSchema>;
