/**
 * Keyword group types for notification filtering
 */

export type MatchType = 'exact' | 'substring' | 'fuzzy' | 'regex' | 'phrase';

export const MATCH_TYPES: { value: MatchType; label: string; description: string }[] = [
  { value: 'substring', label: 'Contains', description: 'Matches if text contains the keyword anywhere' },
  { value: 'exact', label: 'Exact', description: 'Matches only exact word (case-insensitive)' },
  { value: 'phrase', label: 'Phrase', description: 'Matches exact phrase with word boundaries' },
  { value: 'fuzzy', label: 'Fuzzy', description: 'Matches similar words (allows typos)' },
  { value: 'regex', label: 'Regex', description: 'Advanced: Regular expression pattern' },
];

export interface KeywordGroup {
  id: string;
  userId?: string;
  name: string;
  description?: string;
  isTemplate: boolean;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
  keywordCount: number;
  subscriptionCount: number;
}

export interface KeywordGroupSummary {
  id: string;
  name: string;
  description?: string;
  isTemplate: boolean;
  isActive: boolean;
  keywordCount: number;
  subscriptionCount: number;
}

export interface KeywordGroupListResponse {
  groups: KeywordGroupSummary[];
  total: number;
}

export interface TemplateListResponse {
  templates: KeywordGroupSummary[];
  total: number;
}

export interface Keyword {
  id: string;
  keywordGroupId: string;
  keyword: string;
  matchType: MatchType;
  isActive: boolean;
  createdAt: string;
}

export interface KeywordListResponse {
  keywords: Keyword[];
  total: number;
}

export interface KeywordGroupDetail extends KeywordGroup {
  keywords: Keyword[];
  linkedSubscriptions: LinkedSubscription[];
}

export interface LinkedSubscription {
  subscriptionId: string;
  playlistUuid: string;
  playlistName?: string;
  createdAt: string;
}

// Request types
export interface KeywordGroupCreate {
  name: string;
  description?: string;
}

export interface KeywordGroupUpdate {
  name?: string;
  description?: string;
  is_active?: boolean;
}

export interface KeywordCreate {
  keyword: string;
  match_type?: MatchType;
}

export interface KeywordUpdate {
  keyword?: string;
  match_type?: MatchType;
  is_active?: boolean;
}

export interface BulkKeywordImport {
  keywords: string;
  match_type?: MatchType;
}

export interface BulkImportResponse {
  imported: number;
  skipped: number;
  errors: string[];
}

export interface CloneTemplateRequest {
  template_id: string;
  name: string;
  description?: string;
}
