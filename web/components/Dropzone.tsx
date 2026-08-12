"use client";

import { useCallback, useRef, useState } from "react";

/**
 * Drop target and recorder.
 *
 * Two ways in, because the two artifacts this system is built for arrive
 * differently: a photograph already exists on the phone, and a voice note is
 * made on the spot. Forcing the second through a file picker would mean
 * recording in another app first, which is exactly the friction the product
 * claims to remove.
 *
 * Recording uses MediaRecorder — no library, no upload of anything until the
 * user stops. Permission is requested at the moment of pressing record, not on
 * page load, so a visitor who only wants to look at the timeline is never asked
 * for their microphone.
 */

const ACCEPT = ".pdf,.png,.jpg,.jpeg,.webp,.wav,.m4a,.mp3,.webm,application/pdf,image/*,audio/*";

export interface Dropped {
  file: File;
  kind: "document" | "photo" | "voice_note";
}

function classify(file: File): Dropped["kind"] {
  if (file.type.startsWith("image/")) return "photo";
  if (file.type.startsWith("audio/")) return "voice_note";
  return "document";
}

export function Dropzone({
  onFiles,
  disabled,
}: {
  onFiles: (dropped: Dropped[]) => void;
  disabled?: boolean;
}) {
  const [over, setOver] = useState(false);
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [micError, setMicError] = useState<string | null>(null);

  const input = useRef<HTMLInputElement>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const ticker = useRef<ReturnType<typeof setInterval> | null>(null);

  const accept = useCallback(
    (files: FileList | null) => {
      if (!files?.length) return;
      onFiles(Array.from(files).map((file) => ({ file, kind: classify(file) })));
    },
    [onFiles],
  );

  const startRecording = useCallback(async () => {
    setMicError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks: BlobPart[] = [];
      const mr = new MediaRecorder(stream);

      mr.ondataavailable = (event) => event.data.size > 0 && chunks.push(event.data);
      mr.onstop = () => {
        // Release the microphone as soon as we are done with it. A tab holding
        // an open mic after the user pressed stop is a small betrayal.
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunks, { type: mr.mimeType || "audio/webm" });
        const file = new File([blob], `voice-note-${Date.now()}.webm`, { type: blob.type });
        onFiles([{ file, kind: "voice_note" }]);
      };

      mr.start();
      recorder.current = mr;
      setRecording(true);
      setSeconds(0);
      ticker.current = setInterval(() => setSeconds((s) => s + 1), 1000);
    } catch (error) {
      setMicError(
        error instanceof Error && error.name === "NotAllowedError"
          ? "Microphone permission was denied — you can still drop an audio file."
          : "No microphone available — you can still drop an audio file.",
      );
    }
  }, [onFiles]);

  const stopRecording = useCallback(() => {
    recorder.current?.stop();
    recorder.current = null;
    if (ticker.current) clearInterval(ticker.current);
    setRecording(false);
  }, []);

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          if (!disabled) accept(e.dataTransfer.files);
        }}
        className="rounded-[var(--radius)] border border-dashed p-8 text-center transition-colors"
        style={{
          borderColor: over ? "var(--phosphor)" : "var(--line)",
          background: over ? "color-mix(in oklab, var(--phosphor) 6%, transparent)" : undefined,
          opacity: disabled ? 0.5 : 1,
        }}
      >
        <p className="text-[0.95rem]">
          {over ? "Let go" : "Drop a photo, a recording or a scan"}
        </p>
        <p className="text-[var(--text-2)] text-[0.82rem] mt-1">
          Crooked, dim and half-legible is expected — that is what this is for.
        </p>

        <div className="flex items-center justify-center gap-2 mt-3 flex-wrap">
          <button
            type="button"
            className="btn"
            disabled={disabled}
            onClick={() => input.current?.click()}
          >
            Choose files
          </button>

          {recording ? (
            <button type="button" className="btn btn-deny" onClick={stopRecording}>
              <span className="live-dot" aria-hidden />
              Stop — {String(Math.floor(seconds / 60)).padStart(2, "0")}:
              {String(seconds % 60).padStart(2, "0")}
            </button>
          ) : (
            <button type="button" className="btn" disabled={disabled} onClick={startRecording}>
              ◈ Record a voice note
            </button>
          )}
        </div>

        {micError && (
          <p className="mt-2 text-[0.8rem]" style={{ color: "var(--amber)" }}>
            {micError}
          </p>
        )}

        <input
          ref={input}
          type="file"
          accept={ACCEPT}
          multiple
          hidden
          onChange={(e) => accept(e.target.files)}
        />
      </div>
    </div>
  );
}
