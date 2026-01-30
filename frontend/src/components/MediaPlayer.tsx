import { useRef, useEffect, useState } from 'react';
import ReactPlayer from 'react-player';
import { Play, Pause, Volume2, VolumeX, Maximize, Clock } from 'lucide-react';
import type { TimestampSegment } from '../types';

interface MediaPlayerProps {
  url: string;
  type: "audio" | "video";
  timestamps?: TimestampSegment[];
  onTimestampClick?: (seconds: number) => void;
  // onTimestampClick?: (timestamp: TimestampSegment) => void;
  seekToTimestamp?: number | null;
}

function formatTime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
 
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

export function MediaPlayer({
  url,
  type,
  timestamps = [],
  onTimestampClick,
  seekToTimestamp,
}: MediaPlayerProps) {
  const playerRef = useRef<ReactPlayer>(null);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [played, setPlayed] = useState(0);
  const [duration, setDuration] = useState(0);
  const [seeking, setSeeking] = useState(false);
  const [isReady, setIsReady] = useState(false);

  const readyOnceRef = useRef(false);

  // Seek to timestamp when prop changes
  useEffect(() => {
    if (isReady && typeof seekToTimestamp === "number" && playerRef.current) {
      console.log("🎯 MediaPlayer seek:", seekToTimestamp);
      playerRef.current.seekTo(seekToTimestamp, "seconds");
      setPlaying(true);
    }

  }, [seekToTimestamp, isReady]);

// useEffect(() => {
//   // console.log("MediaPlayer mounted");
//   return () => console.log("MediaPlayer unmounted");
// }, []);



  const handleProgress = (state: { played: number; playedSeconds: number }) => {
    if (!seeking) {
      setPlayed(state.played);
    }
  };

  const handleSeekChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPlayed(parseFloat(e.target.value));
  };

  const handleSeekMouseDown = () => {
    setSeeking(true);
  };

  const handleSeekMouseUp = (e: React.MouseEvent<HTMLInputElement>) => {
    setSeeking(false);
    const target = e.target as HTMLInputElement;
    playerRef.current?.seekTo(parseFloat(target.value));
  };

//   const handleTimestampClick = (timestamp: TimestampSegment) => {
//     if (typeof timestamp.start !== "number") return;
//     console.log("🎯 MediaPlayer local seek:", timestamp.start);
// 
//     playerRef.current?.seekTo(timestamp.start, 'seconds');
//     setPlaying(true);
//     // onTimestampClick?.(timestamp);
//   };

  return (
    <div className="bg-gray-900 rounded-xl overflow-hidden">
      {/* Player */}
      <div
        className={`relative ${type === "audio" ? "h-20 bg-gradient-to-r from-purple-900 to-blue-900" : ""}`}
      >
        <ReactPlayer
          ref={playerRef}
          url={url}
          playing={playing}
          muted={muted}
          width="100%"
          height={type === "audio" ? "80px" : "100%"}
          onReady={() => {
            if (readyOnceRef.current) return;
            readyOnceRef.current = true;

            console.log("Player ready");
            setIsReady(true);
          }}
          onProgress={handleProgress}
          onDuration={setDuration}
          progressInterval={100}
          config={{
            file: {
              attributes: {
                controlsList: "nodownload",
              },
            },
          }}
        />
      </div>

      {/* Controls */}
      <div className="p-4">
        {/* Progress bar */}
        <div className="mb-3">
          <input
            type="range"
            min={0}
            max={0.999999}
            step="any"
            value={played}
            onChange={handleSeekChange}
            onMouseDown={handleSeekMouseDown}
            onMouseUp={handleSeekMouseUp}
            className="w-full h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer
                       [&::-webkit-slider-thumb]:appearance-none
                       [&::-webkit-slider-thumb]:w-3
                       [&::-webkit-slider-thumb]:h-3
                       [&::-webkit-slider-thumb]:rounded-full
                       [&::-webkit-slider-thumb]:bg-white
                       [&::-webkit-slider-thumb]:cursor-pointer"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>{formatTime(played * duration)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>

        {/* Control buttons */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => setPlaying(!playing)}
            className="p-2 bg-white rounded-full text-gray-900 hover:bg-gray-200 transition-colors"
          >
            {playing ? (
              <Pause className="w-5 h-5" />
            ) : (
              <Play className="w-5 h-5" />
            )}
          </button>

          <button
            onClick={() => setMuted(!muted)}
            className="p-2 text-gray-400 hover:text-white transition-colors"
          >
            {muted ? (
              <VolumeX className="w-5 h-5" />
            ) : (
              <Volume2 className="w-5 h-5" />
            )}
          </button>

          <div className="flex-1" />

          {type === "video" && (
            <button
              onClick={() =>
                playerRef.current?.getInternalPlayer()?.requestFullscreen?.()
              }
              className="p-2 text-gray-400 hover:text-white transition-colors"
            >
              <Maximize className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>

      {/* Timestamps */}
      {timestamps.length > 0 && (
        <div className="border-t border-gray-800 p-4 max-h-48 overflow-y-auto">
          <h4 className="text-sm font-medium text-gray-400 mb-2 flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Timestamps
          </h4>
          <div className="space-y-1">
            {timestamps.slice(0, 20).map((ts, idx) => (
              <button
                key={idx}
                onClick={() => {
                  if (typeof ts.start === "number") {
                    onTimestampClick?.(ts.start);
                  }
                }}
                // onClick={() => onTimestampClick?.(ts.start)}
                // onClick={() => handleTimestampClick(ts)}
                className="w-full text-left p-2 rounded hover:bg-gray-800 transition-colors group"
              >
                <span className="text-xs text-blue-400 font-mono group-hover:text-blue-300">
                  {formatTime(ts.start)}
                </span>
                <span className="text-sm text-gray-300 ml-2 line-clamp-1">
                  {ts.text}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
