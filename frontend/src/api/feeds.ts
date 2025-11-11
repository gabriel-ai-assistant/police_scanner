// src/api/feeds.ts
export type Feed = {
  feedId: number;
  descr: string;
  sdescr?: string;
  listeners?: number;
  relay_server?: string;
  relay_mount?: string;
};

const MOCK_FEEDS: Feed[] = [
  {
    feedId: 32602,
    descr: "Indianapolis Metropolitan Police",
    listeners: 396,
    relay_server: "beau.broadcastify.com",
    relay_mount: "jm736vwk2ry8f9q",
  },
  { feedId: 11111, descr: "Dallas / Collin County Public Safety", listeners: 182 },
  { feedId: 22222, descr: "Prosper Police / Fire", listeners: 74 },
];

export async function fetchTopFeeds(top = 25): Promise<Feed[]> {
  return MOCK_FEEDS.slice(0, top);
}
