import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, File, Music, Video, Loader2, CheckCircle, XCircle } from 'lucide-react';
import type { Document, UploadProgress } from '../types';
import { uploadFile } from '../api';

interface FileUploadProps {
  onUploadComplete: (document: Document) => void;
}

const ALLOWED_TYPES = {
  'application/pdf': ['.pdf'],
  'audio/mpeg': ['.mp3'],
  'audio/wav': ['.wav'],
  'audio/mp4': ['.m4a'],
  'audio/ogg': ['.ogg'],
  'video/mp4': ['.mp4'],
  'video/webm': ['.webm'],
};

export function FileUpload({ onUploadComplete }: FileUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;

      const file = acceptedFiles[0];
      setUploading(true);
      setError(null);
      setSuccess(false);
      setProgress({ loaded: 0, total: file.size, percentage: 0 });

      try {
        const document = await uploadFile(file, setProgress);
        setSuccess(true);
        onUploadComplete(document);

        // Reset after 2 seconds
        setTimeout(() => {
          setSuccess(false);
          setProgress(null);
        }, 2000);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Upload failed';
        setError(errorMessage);
      } finally {
        setUploading(false);
      }
    },
    [onUploadComplete]
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: ALLOWED_TYPES,
    maxFiles: 1,
    maxSize: 100 * 1024 * 1024, // 100MB
    disabled: uploading,
  });

  const getFileIcon = (type: string) => {
    if (type.startsWith('audio/')) return <Music className="w-12 h-12 text-purple-500" />;
    if (type.startsWith('video/')) return <Video className="w-12 h-12 text-blue-500" />;
    return <File className="w-12 h-12 text-red-500" />;
  };

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-xl p-8 text-center cursor-pointer
          transition-all duration-200 ease-in-out
          ${isDragActive && !isDragReject ? 'border-blue-500 bg-blue-50' : ''}
          ${isDragReject ? 'border-red-500 bg-red-50' : ''}
          ${!isDragActive && !uploading ? 'border-gray-300 hover:border-gray-400 hover:bg-gray-50' : ''}
          ${uploading ? 'border-gray-300 bg-gray-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />

        {uploading ? (
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="w-12 h-12 text-blue-500 animate-spin" />
            <div className="w-full max-w-xs">
              <div className="flex justify-between text-sm text-gray-600 mb-1">
                <span>Uploading...</span>
                <span>{progress?.percentage || 0}%</span>
              </div>
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 transition-all duration-300"
                  style={{ width: `${progress?.percentage || 0}%` }}
                />
              </div>
            </div>
          </div>
        ) : success ? (
          <div className="flex flex-col items-center gap-3">
            <CheckCircle className="w-12 h-12 text-green-500" />
            <p className="text-green-600 font-medium">Upload successful!</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center gap-3">
            <XCircle className="w-12 h-12 text-red-500" />
            <p className="text-red-600 font-medium">{error}</p>
            <p className="text-sm text-gray-500">Click to try again</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4">
            <div className="flex gap-4">
              <File className="w-10 h-10 text-red-400" />
              <Music className="w-10 h-10 text-purple-400" />
              <Video className="w-10 h-10 text-blue-400" />
            </div>
            <div>
              <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
              {isDragActive ? (
                <p className="text-blue-600 font-medium">Drop the file here</p>
              ) : (
                <>
                  <p className="text-gray-700 font-medium">
                    Drag & drop a file here, or click to select
                  </p>
                  <p className="text-sm text-gray-500 mt-1">
                    PDF, Audio (MP3, WAV), or Video (MP4, WebM) - Max 100MB
                  </p>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
