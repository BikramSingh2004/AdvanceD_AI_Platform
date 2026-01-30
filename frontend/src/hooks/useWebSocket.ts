// import { useState, useCallback, useRef, useEffect } from 'react';
// import type { StreamToken, Source, TimestampSegment } from '../types';
// import { createChatWebSocket } from '../api';
// 
// interface UseWebSocketOptions {
//   documentId: string;
//   onMessage?: (token: StreamToken) => void;
//   onError?: (error: string) => void;
//   onComplete?: (response: { sources: Source[]; timestamps: TimestampSegment[] }) => void;
// }
// 
// export function useWebSocket({
//   documentId,
//   onMessage,
//   onError,
//   onComplete,
// }: UseWebSocketOptions) {
//   const [isConnected, setIsConnected] = useState(false);
//   const [isStreaming, setIsStreaming] = useState(false);
//   const wsRef = useRef<WebSocket | null>(null);
//   const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
// 
//   const connect = useCallback(() => {
//     if (wsRef.current?.readyState === WebSocket.OPEN) {
//       return;
//     }
// 
//     const ws = createChatWebSocket(documentId);
// 
//     ws.onopen = () => {
//       setIsConnected(true);
//       console.log('WebSocket connected');
//     };
// 
//     ws.onclose = () => {
//       setIsConnected(false);
//       setIsStreaming(false);
//       console.log('WebSocket disconnected');
// 
//       // Attempt to reconnect after 3 seconds
//       reconnectTimeoutRef.current = setTimeout(() => {
//         connect();
//       }, 3000);
//     };
// 
//     ws.onerror = (error) => {
//       console.error('WebSocket error:', error);
//       onError?.('WebSocket connection error');
//     };
// 
//     ws.onmessage = (event) => {
//       try {
//         const data: StreamToken = JSON.parse(event.data);
// 
//         if (data.error) {
//           onError?.(data.error);
//           setIsStreaming(false);
//           return;
//         }
// 
//         onMessage?.(data);
// 
//         if (data.done) {
//           setIsStreaming(false);
//           onComplete?.({
//             sources: data.sources || [],
//             timestamps: data.timestamps || [],
//           });
//         }
//       } catch (e) {
//         console.error('Failed to parse WebSocket message:', e);
//       }
//     };
// 
//     wsRef.current = ws;
//   }, [documentId, onMessage, onError, onComplete]);
// 
//   const disconnect = useCallback(() => {
//     if (reconnectTimeoutRef.current) {
//       clearTimeout(reconnectTimeoutRef.current);
//     }
//     if (wsRef.current) {
//       wsRef.current.close();
//       wsRef.current = null;
//     }
//     setIsConnected(false);
//     setIsStreaming(false);
//   }, []);
// 
//   const sendMessage = useCallback(
//     (message: string, includeTimestamps = true) => {
//       if (wsRef.current?.readyState !== WebSocket.OPEN) {
//         onError?.('WebSocket not connected');
//         return false;
//       }
// 
//       setIsStreaming(true);
//       wsRef.current.send(
//         JSON.stringify({
//           message,
//           include_timestamps: includeTimestamps,
//         })
//       );
//       return true;
//     },
//     [onError]
//   );
// 
//   useEffect(() => {
//     connect();
//     return () => {
//       disconnect();
//     };
//   }, [connect, disconnect]);
// 
//   return {
//     isConnected,
//     isStreaming,
//     sendMessage,
//     connect,
//     disconnect,
//   };
// }



import { useState, useCallback, useRef, useEffect } from "react";
import type { StreamToken, Source, TimestampSegment } from "../types";
import { createChatWebSocket } from "../api";

interface UseWebSocketOptions {
  documentId: string;
  onMessage?: (token: StreamToken) => void;
  onError?: (error: string) => void;
  onComplete?: (response: {
    sources: Source[];
    timestamps: TimestampSegment[];
  }) => void;
}

export function useWebSocket({
  documentId,
  onMessage,
  onError,
  onComplete,
}: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current) return;

    const ws = createChatWebSocket(documentId);

    ws.onopen = () => {
      setIsConnected(true);
      console.log("WebSocket connected");
    };

    ws.onclose = () => {
      console.log("WebSocket closed");
      setIsConnected(false);
      setIsStreaming(false);
      wsRef.current = null;
    };

    ws.onerror = () => {
      onError?.("WebSocket connection error");
    };

    ws.onmessage = (event) => {
      try {
        const data: StreamToken = JSON.parse(event.data);

        if (data.error) {
          onError?.(data.error);
          setIsStreaming(false);
          ws.close();
          return;
        }

        // Stream token
        // ONLY stream real tokens
        if (
          !data.done &&
          typeof data.token === "string" &&
          data.token.length > 0
        ) {
          onMessage?.(data);
        }

        // Final message
        if (data.done) {
          setIsStreaming(false);
          onComplete?.({
            sources: data.sources || [],
            timestamps: data.timestamps || [],
          });

          // 🔑 IMPORTANT: close socket on completion
          ws.close();
        }
      } catch (e) {
        console.error("Failed to parse WebSocket message", e);
      }
    };

    wsRef.current = ws;
  }, [documentId, onMessage, onError, onComplete]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
    setIsStreaming(false);
  }, []);

  const sendMessage = useCallback(
    (message: string, includeTimestamps = true) => {
      // 🔁 reconnect if needed
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        connect();
      }
      const ws = wsRef.current;

      if (!ws) {
        onError?.("WebSocket not ready");
        return false;
      }
      // Wait briefly for connection to open
      if (ws.readyState === WebSocket.CONNECTING) {
        ws.onopen = () => {
          setIsStreaming(true);
          ws.send(
            JSON.stringify({
              message,
              include_timestamps: includeTimestamps,
            }),
          );
        };
        return true;
      }

      if (ws.readyState !== WebSocket.OPEN) {
        onError?.("WebSocket not connected");
        return false;
      }
      setIsStreaming(true);
      ws.send(
        JSON.stringify({
          message,
          include_timestamps: includeTimestamps,
        }),
      );
      return true;
    },
    [connect, onError],
  );


  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    isConnected,
    isStreaming,
    sendMessage,
    connect,
    disconnect,
  };
}

