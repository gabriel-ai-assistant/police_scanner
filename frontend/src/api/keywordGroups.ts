/**
 * Keyword Groups API module
 */

import { api, isMock } from '@/lib/api';
import type {
  KeywordGroup,
  KeywordGroupSummary,
  KeywordGroupListResponse,
  KeywordGroupDetail,
  TemplateListResponse,
  Keyword,
  KeywordListResponse,
  KeywordGroupCreate,
  KeywordGroupUpdate,
  KeywordCreate,
  KeywordUpdate,
  BulkKeywordImport,
  BulkImportResponse,
  CloneTemplateRequest,
} from '@/types/keywordGroup';

// Mock data for development
const mockGroups: KeywordGroupSummary[] = [
  {
    id: 'group-1',
    name: 'Home Streets',
    description: 'Streets near my home',
    isTemplate: false,
    isActive: true,
    keywordCount: 15,
    subscriptionCount: 1,
  },
  {
    id: 'group-2',
    name: 'Emergency Codes',
    description: 'Common police radio codes',
    isTemplate: false,
    isActive: true,
    keywordCount: 25,
    subscriptionCount: 2,
  },
];

const mockTemplates: KeywordGroupSummary[] = [
  {
    id: 'template-1',
    name: 'Emergency Codes',
    description: 'Common police radio codes indicating emergencies',
    isTemplate: true,
    isActive: true,
    keywordCount: 9,
    subscriptionCount: 0,
  },
  {
    id: 'template-2',
    name: 'Common Alerts',
    description: 'Frequently used alert keywords for critical incidents',
    isTemplate: true,
    isActive: true,
    keywordCount: 8,
    subscriptionCount: 0,
  },
];

const mockKeywords: Keyword[] = [
  { id: 'kw-1', keywordGroupId: 'group-1', keyword: 'Main Street', matchType: 'substring', isActive: true, createdAt: new Date().toISOString() },
  { id: 'kw-2', keywordGroupId: 'group-1', keyword: 'Oak Avenue', matchType: 'substring', isActive: true, createdAt: new Date().toISOString() },
];

/**
 * List all keyword groups for the current user
 */
export async function listKeywordGroups(includeTemplates = false): Promise<KeywordGroupListResponse> {
  if (isMock()) {
    const groups = includeTemplates ? [...mockGroups, ...mockTemplates] : mockGroups;
    return { groups, total: groups.length };
  }

  try {
    const response = await api.get<KeywordGroupListResponse>('/keyword-groups', {
      params: { include_templates: includeTemplates },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch keyword groups', error);
    throw error;
  }
}

/**
 * List available template keyword groups
 */
export async function listTemplates(): Promise<TemplateListResponse> {
  if (isMock()) {
    return { templates: mockTemplates, total: mockTemplates.length };
  }

  try {
    const response = await api.get<TemplateListResponse>('/keyword-groups/templates');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch templates', error);
    throw error;
  }
}

/**
 * Get a keyword group with details
 */
export async function getKeywordGroup(groupId: string): Promise<KeywordGroupDetail> {
  if (isMock()) {
    const group = [...mockGroups, ...mockTemplates].find(g => g.id === groupId);
    if (!group) throw new Error('Keyword group not found');
    return {
      ...group,
      userId: group.isTemplate ? undefined : 'user-1',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      keywords: mockKeywords.filter(k => k.keywordGroupId === groupId),
      linkedSubscriptions: [],
    };
  }

  const response = await api.get<KeywordGroupDetail>(`/keyword-groups/${groupId}`);
  return response.data;
}

/**
 * Create a new keyword group
 */
export async function createKeywordGroup(data: KeywordGroupCreate): Promise<KeywordGroup> {
  if (isMock()) {
    return {
      id: `group-${Date.now()}`,
      userId: 'user-1',
      name: data.name,
      description: data.description,
      isTemplate: false,
      isActive: true,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      keywordCount: 0,
      subscriptionCount: 0,
    };
  }

  const response = await api.post<KeywordGroup>('/keyword-groups', data);
  return response.data;
}

/**
 * Clone a template keyword group
 */
export async function cloneTemplate(data: CloneTemplateRequest): Promise<KeywordGroup> {
  if (isMock()) {
    const template = mockTemplates.find(t => t.id === data.template_id);
    return {
      id: `group-${Date.now()}`,
      userId: 'user-1',
      name: data.name,
      description: data.description || template?.description,
      isTemplate: false,
      isActive: true,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      keywordCount: template?.keywordCount || 0,
      subscriptionCount: 0,
    };
  }

  const response = await api.post<KeywordGroup>('/keyword-groups/clone', data);
  return response.data;
}

/**
 * Update a keyword group
 */
export async function updateKeywordGroup(
  groupId: string,
  data: KeywordGroupUpdate
): Promise<KeywordGroup> {
  if (isMock()) {
    const group = mockGroups.find(g => g.id === groupId);
    if (!group) throw new Error('Keyword group not found');
    return {
      ...group,
      userId: 'user-1',
      name: data.name ?? group.name,
      description: data.description ?? group.description,
      isActive: data.is_active ?? group.isActive,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
  }

  const response = await api.patch<KeywordGroup>(`/keyword-groups/${groupId}`, data);
  return response.data;
}

/**
 * Delete a keyword group
 */
export async function deleteKeywordGroup(groupId: string): Promise<void> {
  if (isMock()) {
    return;
  }

  await api.delete(`/keyword-groups/${groupId}`);
}

/**
 * List keywords in a group
 */
export async function listKeywords(groupId: string): Promise<KeywordListResponse> {
  if (isMock()) {
    const keywords = mockKeywords.filter(k => k.keywordGroupId === groupId);
    return { keywords, total: keywords.length };
  }

  const response = await api.get<KeywordListResponse>(`/keyword-groups/${groupId}/keywords`);
  return response.data;
}

/**
 * Add a keyword to a group
 */
export async function createKeyword(groupId: string, data: KeywordCreate): Promise<Keyword> {
  if (isMock()) {
    return {
      id: `kw-${Date.now()}`,
      keywordGroupId: groupId,
      keyword: data.keyword,
      matchType: data.match_type || 'substring',
      isActive: true,
      createdAt: new Date().toISOString(),
    };
  }

  const response = await api.post<Keyword>(`/keyword-groups/${groupId}/keywords`, data);
  return response.data;
}

/**
 * Bulk import keywords
 */
export async function bulkImportKeywords(
  groupId: string,
  data: BulkKeywordImport
): Promise<BulkImportResponse> {
  if (isMock()) {
    const lines = data.keywords.split('\n').filter(l => l.trim());
    return {
      imported: lines.length,
      skipped: 0,
      errors: [],
    };
  }

  const response = await api.post<BulkImportResponse>(
    `/keyword-groups/${groupId}/keywords/bulk`,
    data
  );
  return response.data;
}

/**
 * Update a keyword
 */
export async function updateKeyword(
  groupId: string,
  keywordId: string,
  data: KeywordUpdate
): Promise<Keyword> {
  if (isMock()) {
    const keyword = mockKeywords.find(k => k.id === keywordId);
    if (!keyword) throw new Error('Keyword not found');
    return {
      ...keyword,
      keyword: data.keyword ?? keyword.keyword,
      matchType: data.match_type ?? keyword.matchType,
      isActive: data.is_active ?? keyword.isActive,
    };
  }

  const response = await api.patch<Keyword>(
    `/keyword-groups/${groupId}/keywords/${keywordId}`,
    data
  );
  return response.data;
}

/**
 * Delete a keyword
 */
export async function deleteKeyword(groupId: string, keywordId: string): Promise<void> {
  if (isMock()) {
    return;
  }

  await api.delete(`/keyword-groups/${groupId}/keywords/${keywordId}`);
}
