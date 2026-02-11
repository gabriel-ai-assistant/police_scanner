/**
 * Dashboard API types for personalized user experience.
 */

export interface DashboardStats {
  myFeeds: number;
  myCalls1h: number;
  myTranscripts24h: number;
}

export interface MyFeed {
  id: string;
  name: string;
  description?: string;
  listeners: number;
  isActive: boolean;
  updatedAt?: string;
  subscribedAt?: string;
}

export interface MyFeedsResponse {
  feeds: MyFeed[];
  total: number;
  hasMore: boolean;
}

export interface RecentCall {
  id: string;
  timestamp?: string;
  talkgroup?: string;
  duration?: number;
  feedName?: string;
  feedId?: string;
  audioUrl?: string;
}

export interface RecentCallsResponse {
  calls: RecentCall[];
}

export interface RecentTranscript {
  id: number;
  text?: string;
  confidence?: number;
  createdAt?: string;
  feedName?: string;
  feedId?: string;
  callId?: string;
}

export interface RecentTranscriptsResponse {
  transcripts: RecentTranscript[];
}

export interface KeywordGroupSummary {
  name: string;
  keywordCount: number;
  isActive: boolean;
}

export interface KeywordSummaryResponse {
  groups: KeywordGroupSummary[];
  totalKeywords: number;
  message: string;
}

export interface RecentActivity {
  id: string;  // call_uid
  timestamp?: string;
  talkgroup?: string;
  duration?: number;
  feedName?: string;
  feedId?: string;
  audioUrl?: string;
  transcriptId?: number;
  transcriptText?: string;
  transcriptConfidence?: number;
  userRating?: boolean | null;  // true=up, false=down, null=no rating
}

export interface RecentActivityResponse {
  activities: RecentActivity[];
}

export interface TranscriptRating {
  id: string;
  transcriptId: number;
  rating: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface TranscriptRatingRequest {
  rating: boolean;
}

export interface TranscriptRatingDeleteResponse {
  deleted: boolean;
  message: string;
}
