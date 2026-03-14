"use client";

import { useEffect, useRef, useImperativeHandle, forwardRef } from "react";

declare global {
  interface Window {
    YT: typeof YT;
    onYouTubeIframeAPIReady: (() => void) | undefined;
  }
}

export interface YouTubePlayerHandle {
  unmute: () => void;
}

interface Props {
  videoId: string;
  muted?: boolean;
}

function loadYTApi(): Promise<void> {
  return new Promise((resolve) => {
    if (window.YT && window.YT.Player) {
      resolve();
      return;
    }
    const existing = document.getElementById("yt-iframe-api");
    if (existing) {
      const check = setInterval(() => {
        if (window.YT && window.YT.Player) {
          clearInterval(check);
          resolve();
        }
      }, 100);
      return;
    }
    const prev = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      prev?.();
      resolve();
    };
    const script = document.createElement("script");
    script.id = "yt-iframe-api";
    script.src = "https://www.youtube.com/iframe_api";
    document.head.appendChild(script);
  });
}

const YouTubePlayer = forwardRef<YouTubePlayerHandle, Props>(({ videoId, muted = true }, ref) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const playerRef = useRef<YT.Player | null>(null);
  const readyRef = useRef(false);
  const mutedRef = useRef(muted);
  mutedRef.current = muted;

  useImperativeHandle(ref, () => ({
    unmute: () => {
      if (playerRef.current && readyRef.current) {
        playerRef.current.unMute();
        playerRef.current.setVolume(100);
      }
    },
  }));

  // React to muted prop changes
  useEffect(() => {
    if (playerRef.current && readyRef.current) {
      if (muted) {
        playerRef.current.mute();
      } else {
        playerRef.current.unMute();
        playerRef.current.setVolume(100);
      }
    }
  }, [muted]);

  useEffect(() => {
    let cancelled = false;

    loadYTApi().then(() => {
      if (cancelled || !containerRef.current) return;

      if (playerRef.current) {
        try { playerRef.current.destroy(); } catch {}
        playerRef.current = null;
        readyRef.current = false;
      }

      playerRef.current = new window.YT.Player(containerRef.current, {
        videoId,
        width: "100%",
        height: "100%",
        playerVars: {
          autoplay: 1,
          mute: 1,
          enablejsapi: 1,
          rel: 0,
          modestbranding: 1,
          origin: window.location.origin,
        },
        events: {
          onReady: () => {
            readyRef.current = true;
            // Apply muted state as soon as player is ready
            if (!mutedRef.current) {
              playerRef.current?.unMute();
              playerRef.current?.setVolume(100);
            }
          },
        },
      });
    });

    return () => {
      cancelled = true;
      if (playerRef.current) {
        try { playerRef.current.destroy(); } catch {}
        playerRef.current = null;
        readyRef.current = false;
      }
    };
  }, [videoId]);

  return <div ref={containerRef} className="absolute inset-0 w-full h-full" />;
});

YouTubePlayer.displayName = "YouTubePlayer";
export default YouTubePlayer;
