import { File, Music, Video, Trash2, Loader2, Clock, CheckCircle } from 'lucide-react';
import type { Document } from '../types';

interface DocumentListProps {
  documents: Document[];
  selectedId: string | null;
  onSelect: (document: Document) => void;
  onDelete: (documentId: string) => void;
  loading?: boolean;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getFileIcon(fileType: string) {
  switch (fileType) {
    case 'audio':
      return <Music className="w-5 h-5 text-purple-500" />;
    case 'video':
      return <Video className="w-5 h-5 text-blue-500" />;
    default:
      return <File className="w-5 h-5 text-red-500" />;
  }
}

export function DocumentList({
  documents,
  selectedId,
  onSelect,
  onDelete,
  loading,
}: DocumentListProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <File className="w-12 h-12 mx-auto mb-3 text-gray-300" />
        <p>No documents uploaded yet</p>
        <p className="text-sm">Upload a file to get started</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {documents.map((doc) => (
        <div
          key={doc.id}
          className={`
            flex items-center gap-3 p-3 rounded-lg cursor-pointer
            transition-colors duration-150
            ${selectedId === doc.id ? 'bg-blue-50 border border-blue-200' : 'hover:bg-gray-50 border border-transparent'}
          `}
          onClick={() => doc.processed && onSelect(doc)}
        >
          {getFileIcon(doc.file_type)}
          
          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-900 truncate" title={doc.filename}>
              {doc.filename}
            </p>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span>{formatFileSize(doc.file_size)}</span>
              <span>•</span>
              <span>{formatDate(doc.created_at)}</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {doc.processed ? (
              <CheckCircle className="w-4 h-4 text-green-500" title="Processed" />
            ) : (
              <div className="flex items-center gap-1 text-amber-500" title="Processing...">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-xs">Processing</span>
              </div>
            )}
            
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(doc.id);
              }}
              className="p-1 text-gray-400 hover:text-red-500 rounded transition-colors"
              title="Delete document"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
