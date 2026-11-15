export interface Recommendation {
  title?: string;
  media_type?: string;
  creator?: string;
  pitch?: string;
  score?: number;
  graph_reasoning?: string[];
  // passage-match shape returned by the current backend
  passage?: string;
  quote?: string;
  text?: string;
  book?: string;
  location?: string;
  explanation?: string;
  fit?: string;
}

export interface Message {
  sender: 'user' | 'mirrora';
  text: string;
  mode?: string;
  recommendations?: Recommendation[];
  crisis?: boolean;
}

export interface GraphNode {
  id: string;
  group: string;
  label?: string;
  weight?: number;
  score?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  label: string;
  weight?: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Mode {
  id?: string;
  name: string;
  role: string;
  system_prompt?: string;
}

export interface HistoryEntry {
  id?: string | number;
  text?: string;
  created_at?: string;
  date?: string;
  emotions?: Array<{ label?: string; name?: string; intensity?: number } | string>;
  themes?: string[];
  situation?: string;
  passage?: { text?: string; book?: string; location?: string } | string;
  match?: { passage?: { book?: string } } | null;
  abstained?: boolean;
  crisis?: boolean;
}