import { useState, useEffect, useCallback } from 'react';
import { useMemo } from "react";
import { FileUpload } from './components/FileUpload';
import { DocumentList } from './components/DocumentList';
import { DocumentSummary } from './components/DocumentSummary';
import { ChatInterface } from './components/ChatInterface';
import { MediaPlayer } from './components/MediaPlayer';
import { MessageSquare, FileText, RefreshCw } from 'lucide-react';
import type { Document, TimestampSegment } from './types';
import { getDocuments, deleteDocument, getDocumentStatus, getFileUrl, getDocumentTimestamps } from './api';

function App() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [timestamps, setTimestamps] = useState<TimestampSegment[]>([]);
  const [seekTimestamp, setSeekTimestamp] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadDocuments = useCallback(async () => {
    try {
      const response = await getDocuments();
      setDocuments(response.documents);
    } catch (error) {
      console.error('Failed to load documents:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // Poll for document status updates
  useEffect(() => {
    const unprocessedDocs = documents.filter((d) => !d.processed);
    if (unprocessedDocs.length === 0) return;

    const interval = setInterval(async () => {
      for (const doc of unprocessedDocs) {
        try {
          const updated = await getDocumentStatus(doc.id);
          if (updated.processed) {
            setDocuments((prev) =>
              prev.map((d) => (d.id === updated.id ? updated : d))
            );
            if (selectedDocument?.id === updated.id) {
              setSelectedDocument(updated);
            }
          }
        } catch (error) {
          console.error('Failed to check document status:', error);
        }
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [documents, selectedDocument]);

  // Load timestamps when selecting audio/video document
  useEffect(() => {
    if (selectedDocument && ['audio', 'video'].includes(selectedDocument.file_type) && selectedDocument.processed) {
      getDocumentTimestamps(selectedDocument.id)
        .then((data) => setTimestamps(data.timestamps))
        .catch((error) => console.error('Failed to load timestamps:', error));
    } else {
      setTimestamps([]);
    }
  }, [selectedDocument]);

  const handleUploadComplete = (document: Document) => {
    setDocuments((prev) => [document, ...prev]);
    setSelectedDocument(document);
  };

  const handleSelectDocument = (document: Document) => {
    setSelectedDocument(document);
    setSeekTimestamp(null);
  };

  const handleDeleteDocument = async (documentId: string) => {
    if (!confirm('Are you sure you want to delete this document?')) return;

    try {
      await deleteDocument(documentId);
      setDocuments((prev) => prev.filter((d) => d.id !== documentId));
      if (selectedDocument?.id === documentId) {
        setSelectedDocument(null);
      }
    } catch (error) {
      console.error('Failed to delete document:', error);
    }
  };

  const handleSeekToTimestamp = (seconds: number) => {
    console.log("App seek:", seconds);
    setSeekTimestamp(seconds);
    // Reset after a short delay to allow seeking again to the same timestamp
    // setTimeout(() => setSeekTimestamp(null), 100);
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadDocuments();
  };

  const isMediaDocument = selectedDocument && ['audio', 'video'].includes(selectedDocument.file_type);

  const mediaUrl = useMemo(() => {
    if (!selectedDocument?.id) return "";
    return getFileUrl(selectedDocument.id);
  }, [selectedDocument?.id]);


  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-600 rounded-lg">
                <MessageSquare className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">
                  AI Document Q&A
                </h1>
                <p className="text-sm text-gray-500">
                  Upload documents and ask questions powered by AI
                </p>
              </div>
            </div>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <RefreshCw
                className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`}
              />
              Refresh
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="grid grid-cols-12 gap-6">
          {/* Left Sidebar - Document List */}
          <div className="col-span-12 lg:col-span-3">
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <FileText className="w-5 h-5" />
                Documents
              </h2>
              <FileUpload onUploadComplete={handleUploadComplete} />
              <div className="mt-4">
                <DocumentList
                  documents={documents}
                  selectedId={selectedDocument?.id || null}
                  onSelect={handleSelectDocument}
                  onDelete={handleDeleteDocument}
                  loading={loading}
                />
              </div>
            </div>
          </div>

          {/* Main Content Area */}
          <div className="col-span-12 lg:col-span-9">
            {selectedDocument ? (
              <div className="space-y-6">
                {/* Document Summary */}
                <DocumentSummary document={selectedDocument} />

                {/* Media Player for Audio/Video */}
                {isMediaDocument && selectedDocument.processed && (
                  <MediaPlayer
                  key={selectedDocument.id}
                  url={mediaUrl}
                    // url={getFileUrl(selectedDocument.id)}
                    type={selectedDocument.file_type as "audio" | "video"}
                    timestamps={timestamps}
                    seekToTimestamp={seekTimestamp}
                    onTimestampClick={handleSeekToTimestamp}
                  />
                )}

                {/* Chat Interface */}
                {selectedDocument.processed && (
                  <div className="h-[500px]">
                    <ChatInterface
                      documentId={selectedDocument.id}
                      onSeekToTimestamp={handleSeekToTimestamp}
                    />
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
                <FileText className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  No Document Selected
                </h3>
                <p className="text-gray-500 max-w-md mx-auto">
                  Upload a PDF, audio, or video file from the sidebar, then
                  select it to start asking questions. The AI will answer based
                  on the document content.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
