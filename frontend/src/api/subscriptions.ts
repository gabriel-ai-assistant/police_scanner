/**
 * Subscriptions API module
 */

import { api, isMock } from '@/lib/api';
import type {
  Subscription,
  SubscriptionSummary,
  SubscriptionListResponse,
  SubscriptionStatus,
  SubscriptionCreate,
  SubscriptionUpdate,
  LinkedKeywordGroup,
  LinkKeywordGroupRequest,
} from '@/types/subscription';

// Mock data for development
const mockSubscriptions: SubscriptionSummary[] = [
  {
    id: 'sub-1',
    playlistUuid: 'playlist-1',
    playlistName: 'Prosper PD',
    notificationsEnabled: true,
    keywordGroupCount: 2,
  },
  {
    id: 'sub-2',
    playlistUuid: 'playlist-2',
    playlistName: 'Frisco PD',
    notificationsEnabled: true,
    keywordGroupCount: 1,
  },
];

/**
 * List all subscriptions for the current user
 */
export async function listSubscriptions(): Promise<SubscriptionListResponse> {
  if (isMock()) {
    return { subscriptions: mockSubscriptions, total: mockSubscriptions.length };
  }

  try {
    const response = await api.get<SubscriptionListResponse>('/subscriptions');
    return response.data;
  } catch (error) {
    console.warn('Using mock subscriptions due to API error', error);
    return { subscriptions: mockSubscriptions, total: mockSubscriptions.length };
  }
}

/**
 * Get subscription status for a playlist
 */
export async function getSubscriptionStatus(playlistUuid: string): Promise<SubscriptionStatus> {
  if (isMock()) {
    const sub = mockSubscriptions.find(s => s.playlistUuid === playlistUuid);
    return {
      playlistUuid,
      isSubscribed: !!sub,
      subscriptionId: sub?.id,
    };
  }

  try {
    const response = await api.get<SubscriptionStatus>(`/subscriptions/status/${playlistUuid}`);
    return response.data;
  } catch (error) {
    console.warn('Using mock subscription status due to API error', error);
    return { playlistUuid, isSubscribed: false };
  }
}

/**
 * Get a single subscription with details
 */
export async function getSubscription(subscriptionId: string): Promise<Subscription> {
  if (isMock()) {
    const sub = mockSubscriptions.find(s => s.id === subscriptionId);
    if (!sub) throw new Error('Subscription not found');
    return {
      ...sub,
      userId: 'user-1',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
  }

  const response = await api.get<Subscription>(`/subscriptions/${subscriptionId}`);
  return response.data;
}

/**
 * Subscribe to a playlist
 */
export async function createSubscription(data: SubscriptionCreate): Promise<Subscription> {
  if (isMock()) {
    return {
      id: `sub-${Date.now()}`,
      userId: 'user-1',
      playlistUuid: data.playlist_uuid,
      notificationsEnabled: true,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      keywordGroupCount: 0,
    };
  }

  const response = await api.post<Subscription>('/subscriptions', data);
  return response.data;
}

/**
 * Update subscription settings
 */
export async function updateSubscription(
  subscriptionId: string,
  data: SubscriptionUpdate
): Promise<Subscription> {
  if (isMock()) {
    const sub = mockSubscriptions.find(s => s.id === subscriptionId);
    if (!sub) throw new Error('Subscription not found');
    return {
      ...sub,
      userId: 'user-1',
      notificationsEnabled: data.notifications_enabled ?? sub.notificationsEnabled,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
  }

  const response = await api.patch<Subscription>(`/subscriptions/${subscriptionId}`, data);
  return response.data;
}

/**
 * Unsubscribe from a playlist
 */
export async function deleteSubscription(subscriptionId: string): Promise<void> {
  if (isMock()) {
    return;
  }

  await api.delete(`/subscriptions/${subscriptionId}`);
}

/**
 * List keyword groups linked to a subscription
 */
export async function listLinkedKeywordGroups(subscriptionId: string): Promise<LinkedKeywordGroup[]> {
  if (isMock()) {
    return [
      {
        id: 'link-1',
        keywordGroupId: 'group-1',
        keywordGroupName: 'Home Streets',
        keywordCount: 15,
        createdAt: new Date().toISOString(),
      },
    ];
  }

  const response = await api.get<LinkedKeywordGroup[]>(`/subscriptions/${subscriptionId}/keyword-groups`);
  return response.data;
}

/**
 * Link a keyword group to a subscription
 */
export async function linkKeywordGroup(
  subscriptionId: string,
  data: LinkKeywordGroupRequest
): Promise<LinkedKeywordGroup> {
  if (isMock()) {
    return {
      id: `link-${Date.now()}`,
      keywordGroupId: data.keyword_group_id,
      keywordGroupName: 'Mock Group',
      keywordCount: 0,
      createdAt: new Date().toISOString(),
    };
  }

  const response = await api.post<LinkedKeywordGroup>(
    `/subscriptions/${subscriptionId}/keyword-groups`,
    data
  );
  return response.data;
}

/**
 * Unlink a keyword group from a subscription
 */
export async function unlinkKeywordGroup(subscriptionId: string, groupId: string): Promise<void> {
  if (isMock()) {
    return;
  }

  await api.delete(`/subscriptions/${subscriptionId}/keyword-groups/${groupId}`);
}
