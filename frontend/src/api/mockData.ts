import type { Call } from '../types/call';
import type { Feed } from '../types/feed';
import type { Transcript } from '../types/transcript';

export type KeywordSummary = {
  keyword: string;
  hits: number;
};

export const mockFeeds: Feed[] = [
  {
    id: '1',
    name: 'Metro Police Dispatch',
    state: 'IL',
    listeners: 124,
    isActive: true,
    updatedAt: new Date().toISOString()
  },
  {
    id: '2',
    name: 'Fire & EMS North District',
    state: 'IL',
    listeners: 82,
    isActive: true,
    updatedAt: new Date(Date.now() - 1000 * 60 * 10).toISOString()
  },
  {
    id: '3',
    name: 'County Sheriff',
    state: 'IL',
    listeners: 56,
    isActive: false,
    updatedAt: new Date(Date.now() - 1000 * 60 * 45).toISOString()
  }
];

export const mockCalls: Call[] = [
  {
    id: 'call-1',
    feedId: '1',
    talkgroup: 'Dispatch 1',
    timestamp: new Date().toISOString(),
    description: 'Traffic stop near 5th Ave and Pine.',
    priority: 'low',
    duration: 75,
    audioUrl: 'https://example.com/audio/call-1.mp3'
  },
  {
    id: 'call-2',
    feedId: '1',
    talkgroup: 'Dispatch 2',
    timestamp: new Date(Date.now() - 1000 * 60 * 8).toISOString(),
    description: 'Burglary alarm triggered at 1200 Oak Street.',
    priority: 'high',
    duration: 132,
    audioUrl: 'https://example.com/audio/call-2.mp3'
  },
  {
    id: 'call-3',
    feedId: '2',
    talkgroup: 'EMS North',
    timestamp: new Date(Date.now() - 1000 * 60 * 16).toISOString(),
    description: 'Medical emergency, unresponsive person reported.',
    priority: 'medium',
    duration: 210,
    audioUrl: 'https://example.com/audio/call-3.mp3'
  }
];

export const mockTranscripts: Transcript[] = [
  {
    id: 'transcript-1',
    callId: 'call-2',
    feedId: '1',
    createdAt: new Date().toISOString(),
    summary: 'Units responded to a burglary alarm with no signs of forced entry.',
    segments: [
      {
        id: 'segment-1',
        start: 0,
        end: 12,
        text: 'Dispatch to unit 12, burglary alarm triggered at 1200 Oak Street.',
        keywords: ['burglary', 'alarm']
      },
      {
        id: 'segment-2',
        start: 13,
        end: 32,
        text: 'Unit 12 en route, requesting additional unit for perimeter check.',
        keywords: ['perimeter']
      },
      {
        id: 'segment-3',
        start: 33,
        end: 64,
        text: 'Additional units arrived, building secure, no forced entry discovered.',
        keywords: ['secure']
      }
    ]
  },
  {
    id: 'transcript-2',
    callId: 'call-3',
    feedId: '2',
    createdAt: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
    segments: [
      {
        id: 'segment-4',
        start: 0,
        end: 18,
        text: 'Medic unit responding to unresponsive individual, CPR in progress.',
        keywords: ['CPR']
      }
    ]
  }
];

export const mockKeywordHits: KeywordSummary[] = [
  { keyword: 'burglary', hits: 12 },
  { keyword: 'pursuit', hits: 7 },
  { keyword: 'medical', hits: 15 },
  { keyword: 'fire', hits: 9 }
];
