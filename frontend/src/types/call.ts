export interface Call {
  id: string;
  feedId: string;
  talkgroup: string;
  timestamp: string;
  description: string;
  priority: 'low' | 'medium' | 'high';
  duration: number;
  audioUrl: string;
}
