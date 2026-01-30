import { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, Loader2, AlertCircle, Play, Clock } from 'lucide-react';
import type { ChatMessage, Source, TimestampSegment, StreamToken } from '../types';
import { useWebSocket } from '../hooks/useWebSocket';

interface ChatInterfaceProps {
  documentId: string;
  onSeekToTimestamp?: (seconds: number) => void;
}


function formatTimestamp(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Parse timestamps from text like [01:23] or [1:23:45]
function parseTimestampLinks(text: string): Array<{ match: string; seconds: number }> {
  const regex = /\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]/g;
  const links: Array<{ match: string; seconds: number }> = [];
  let match;

  while ((match = regex.exec(text)) !== null) {
    let seconds = 0;
    if (match[3]) {
      // HH:MM:SS format
      seconds = parseInt(match[1]) * 3600 + parseInt(match[2]) * 60 + parseInt(match[3]);
    } else {
      // MM:SS format
      seconds = parseInt(match[1]) * 60 + parseInt(match[2]);
    }
    links.push({ match: match[0], seconds });
  }

  return links;
}

export function ChatInterface({ documentId, onSeekToTimestamp }: ChatInterfaceProps) {
const streamingRef = useRef("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [streamingContent, setStreamingContent] = useState('');
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  // const handleMessage = useCallback((token: StreamToken) => {
  //   setStreamingContent((prev) => prev + token.token);
  // }, []);

  const handleMessage = useCallback((token: StreamToken) => {
    streamingRef.current += token.token;
    setStreamingContent(streamingRef.current);
  }, []);


  const handleError = useCallback((errorMsg: string) => {
    setError(errorMsg);
    setStreamingContent('');
  }, []);

  
  // const handleComplete = useCallback(
  //   (response: { sources: Source[]; timestamps: TimestampSegment[] }) => {
  //     setMessages((prev) => [
  //       ...prev,
  //       {
  //         role: 'assistant',
  //         content: streamingContent,
  //         sources: response.sources,
  //       },
  //     ]);
  //     setStreamingContent('');
  //   },
  //   [streamingContent]
  // );

const handleComplete = useCallback(
  (response: { sources: Source[]; timestamps: TimestampSegment[] }) => {
    const finalAnswer = streamingRef.current;

    if (!finalAnswer.trim()) return;

    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: finalAnswer,
        sources: response.sources,
      },
    ]);

    // clear AFTER commit
    streamingRef.current = "";
    setStreamingContent("");
  },
  [],
);





  const { isConnected, isStreaming, sendMessage } = useWebSocket({
    documentId,
    onMessage: handleMessage,
    onError: handleError,
    onComplete: handleComplete,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming ) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: input.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setError(null);
    setStreamingContent('');

    const sent = sendMessage(input.trim());
    if (sent) {
      setInput('');
    }
  };

  const handleTimestampClick = (seconds?: number) => {
   console.log("🔥 Chat timestamp clicked:", seconds);
    // console.log("Chat → App seek:", seconds);
      if (typeof seconds !== "number") return;
      onSeekToTimestamp?.(seconds);
  };

  const renderMessageContent = (content: string, isStreaming = false) => {
    const timestampLinks = parseTimestampLinks(content);

    // Replace timestamp patterns with clickable buttons
    let processedContent = content;
    timestampLinks.forEach(({ match, seconds }) => {
      processedContent = processedContent.replace(
        match,
        `<timestamp data-seconds="${seconds}">${match}</timestamp>`
      );
    });

    return (
      <div className={`prose prose-sm max-w-none ${isStreaming ? 'streaming-cursor' : ''}`}>
        <ReactMarkdown
          components={{
            // Custom renderer for code blocks
            code: ({ children }) => (
              <code className="bg-gray-100 px-1 py-0.5 rounded text-sm">{children}</code>
            ),
            // Handle paragraphs to process timestamps
            p: ({ children }) => {
              // Check if children contains timestamp elements
              if (typeof children === 'string') {
                const parts = children.split(/(\[[\d:]+\])/g);
                return (
                  <p>
                    {parts.map((part, idx) => {
                      const tsMatch = part.match(/^\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]$/);
                      if (tsMatch) {
                        let seconds = 0;
                        if (tsMatch[3]) {
                          seconds =
                            parseInt(tsMatch[1]) * 3600 +
                            parseInt(tsMatch[2]) * 60 +
                            parseInt(tsMatch[3]);
                        } else {
                          seconds = parseInt(tsMatch[1]) * 60 + parseInt(tsMatch[2]);
                        }
                        return (
                          <button
                            key={idx}
                            onClick={() => handleTimestampClick(seconds)}
                            className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-sm font-mono hover:bg-blue-200 transition-colors"
                          >
                            <Play className="w-3 h-3" />
                            {part}
                          </button>
                        );
                      }
                      return part;
                    })}
                  </p>
                );
              }
              return <p>{children}</p>;
            },
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-xl border border-gray-200">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">Chat</h3>
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-500" : "bg-red-500"}`}
            title={isConnected ? "Connected" : "Disconnected"}
          />
          <span className="text-xs text-gray-500">
            {isConnected ? "Connected" : "Reconnecting..."}
          </span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && !streamingContent && (
          <div className="text-center text-gray-500 py-8">
            <p className="text-lg mb-2">Ask questions about your document</p>
            <p className="text-sm">
              The AI will answer based on the document content.
              {onSeekToTimestamp &&
                " Click on timestamps to jump to that point in the media."}
            </p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`animate-fade-in ${msg.role === "user" ? "flex justify-end" : ""}`}
          >
            <div
              className={`max-w-[85%] rounded-xl px-4 py-3 ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-900"
              }`}
            >
              {msg.role === "user" ? (
                <p>{msg.content}</p>
              ) : (
                renderMessageContent(msg.content)
              )}

              {/* Sources */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <p className="text-xs text-gray-500 mb-2">Sources:</p>
                  <div className="space-y-1">
                    {msg.sources.slice(0, 3).map((source, sIdx) => (
                      <div
                        key={sIdx}
                        className="text-xs text-gray-600 bg-white rounded p-2"
                      >
                        <p className="line-clamp-2">{source.content}</p>
                        {typeof source.timestamp?.start === "number" && (
                          <button
                            onClick={() => {

                              handleTimestampClick(source.timestamp?.start);
                            }}
                          >
                            <Clock className="w-3 h-3" />
                            {formatTimestamp(source.timestamp.start)}
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Streaming message */}
        {streamingContent && (
          <div className="animate-fade-in">
            <div className="max-w-[85%] rounded-xl px-4 py-3 bg-gray-100 text-gray-900">
              {renderMessageContent(streamingContent, true)}
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 text-red-600 bg-red-50 rounded-lg p-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <p className="text-sm">{error}</p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about the document..."
            disabled={isStreaming}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            {isStreaming ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
