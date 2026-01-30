import axios from 'axios';
import type { Document, DocumentListResponse, ChatResponse, UploadProgress } from './types';

// const API_BASE = '/api';
const API_BASE = import.meta.env.VITE_API_BASE_URL + "/api";


export const api = axios.create({
  baseURL: API_BASE,
});

export async function uploadFile(
  file: File,
  onProgress?: (progress: UploadProgress) => void
): Promise<Document> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post<Document>('/upload/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (event) => {
      if (event.total && onProgress) {
        onProgress({
          loaded: event.loaded,
          total: event.total,
          percentage: Math.round((event.loaded * 100) / event.total),
        });
      }
    },
  });

  return response.data;
}

export async function getDocuments(
  skip = 0,
  limit = 20
): Promise<DocumentListResponse> {
  const response = await api.get<DocumentListResponse>('/documents/', {
    params: { skip, limit },
  });
  return response.data;
}

export async function getDocument(documentId: string): Promise<Document> {
  const response = await api.get<Document>(`/documents/${documentId}`);
  return response.data;
}

export async function getDocumentStatus(documentId: string): Promise<Document> {
  const response = await api.get<Document>(`/upload/status/${documentId}`);
  return response.data;
}

export async function deleteDocument(documentId: string): Promise<void> {
  await api.delete(`/documents/${documentId}`);
}

export async function sendChatMessage(
  documentId: string,
  message: string,
  includeTimestamps = true
): Promise<ChatResponse> {
  const response = await api.post<ChatResponse>('/chat/', {
    document_id: documentId,
    message,
    include_timestamps: includeTimestamps,
  });
  return response.data;
}

export async function getChatHistory(
  documentId: string
): Promise<{ document_id: string; messages: Array<{ role: string; content: string }> }> {
  const response = await api.get(`/chat/history/${documentId}`);
  return response.data;
}

export async function clearChatHistory(documentId: string): Promise<void> {
  await api.delete(`/chat/history/${documentId}`);
}

export async function getDocumentTimestamps(
  documentId: string
): Promise<{ id: string; timestamps: Array<{ start: number; end: number; text: string }> }> {
  const response = await api.get(`/documents/${documentId}/timestamps`);
  return response.data;
}

export function getFileUrl(documentId: string): string {
  return `${API_BASE}/documents/${documentId}/file`;
}

// export function createChatWebSocket(documentId: string): WebSocket {
//   const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
//   const host = window.location.host;
//   return new WebSocket(`${protocol}//${host}/api/chat/stream/${documentId}`);
// }

export function createChatWebSocket(documentId: string): WebSocket {
  const baseUrl = import.meta.env.VITE_API_BASE_URL;
  const wsBase = baseUrl.replace("http", "ws");
  return new WebSocket(`${wsBase}/api/chat/stream/${documentId}`);
}

