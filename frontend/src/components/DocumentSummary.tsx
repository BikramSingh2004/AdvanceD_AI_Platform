import { File, Music, Video, Clock, Layers, Loader2 } from 'lucide-react';
import type { Document } from '../types';

interface DocumentSummaryProps {
  document: Document | null;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileIcon(fileType: string) {
  switch (fileType) {
    case 'audio':
      return <Music className="w-8 h-8 text-purple-500" />;
    case 'video':
      return <Video className="w-8 h-8 text-blue-500" />;
    default:
      return <File className="w-8 h-8 text-red-500" />;
  }
}

export function DocumentSummary({ document }: DocumentSummaryProps) {
  if (!document) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="text-center text-gray-500 py-8">
          <File className="w-12 h-12 mx-auto mb-3 text-gray-300" />
          <p>Select a document to view details</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-start gap-4 mb-4">
        {getFileIcon(document.file_type)}
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900 truncate" title={document.filename}>
            {document.filename}
          </h3>
          <div className="flex items-center gap-4 text-sm text-gray-500 mt-1">
            <span className="capitalize">{document.file_type}</span>
            <span>•</span>
            <span>{formatFileSize(document.file_size)}</span>
            {document.chunk_count > 0 && (
              <>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Layers className="w-3 h-3" />
                  {document.chunk_count} chunks
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="border-t border-gray-100 pt-4">
        <h4 className="text-sm font-medium text-gray-700 mb-2">Summary</h4>
        {document.processed ? (
          document.summary ? (
            <p className="text-sm text-gray-600 leading-relaxed">{document.summary}</p>
          ) : (
            <p className="text-sm text-gray-400 italic">No summary available</p>
          )
        ) : (
          <div className="flex items-center gap-2 text-amber-600">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Processing document...</span>
          </div>
        )}
      </div>
    </div>
  );
}
