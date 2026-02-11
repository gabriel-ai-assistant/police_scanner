/**
 * Subscription types for user playlist subscriptions
 */

export interface Subscription {
  id: string;
  userId: string;
  playlistUuid: string;
  notificationsEnabled: boolean;
  createdAt: string;
  updatedAt: string;
  // Joined data
  playlistName?: string;
  playlistDescr?: string;
  keywordGroupCount: number;
}

export interface SubscriptionSummary {
  id: string;
  playlistUuid: string;
  playlistName?: string;
  notificationsEnabled: boolean;
  keywordGroupCount: number;
}

export interface SubscriptionListResponse {
  subscriptions: SubscriptionSummary[];
  total: number;
}

export interface SubscriptionStatus {
  playlistUuid: string;
  isSubscribed: boolean;
  subscriptionId?: string;
}

export interface SubscriptionCreate {
  playlist_uuid: string;
}

export interface SubscriptionUpdate {
  notifications_enabled?: boolean;
}

export interface LinkedKeywordGroup {
  id: string;
  keywordGroupId: string;
  keywordGroupName: string;
  keywordCount: number;
  createdAt: string;
}

export interface LinkKeywordGroupRequest {
  keyword_group_id: string;
}
