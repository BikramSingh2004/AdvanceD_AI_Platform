export interface Document {
  id: string;
  filename: string;
  file_type: 'pdf' | 'audio' | 'video';
  file_size: number;
  summary: string | null;
  processed: boolean;
  created_at: string;
  chunk_count: number;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
}

export interface TimestampSegment {
  start: number;
  end: number;
  text: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  sources?: Source[];
}

export interface Source {
  document_id: string;
  chunk_index: number;
  content: string;
  score: number;
  metadata: Record<string, unknown>;
  timestamp?: {
    start: number;
    end: number;
  };
}

export interface ChatResponse {
  message: string;
  sources: Source[];
  timestamps: TimestampSegment[];
}

export interface StreamToken {
  token: string;
  done: boolean;
  sources?: Source[];
  timestamps?: TimestampSegment[];
  error?: string;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}
