import { useCallback, useRef, useState } from 'react';

/**
 * Microphone capture via MediaRecorder.
 *
 * This replaces the browser Web Speech API, which only recognised a handful of
 * languages and silently transcribed Tamil, Telugu and Malayalam as English.
 * Here we just capture audio; Sarvam does the recognition server-side and
 * identifies the language itself.
 */

export type RecorderError = 'permission-denied' | 'unsupported' | 'no-audio' | 'failed';

interface UseVoiceRecorder {
  isRecording: boolean;
  start: () => Promise<boolean>;
  stop: () => Promise<Blob | null>;
  cancel: () => void;
  error: RecorderError | null;
}

/** Pick a container the browser can actually produce. */
function pickMimeType(): string | undefined {
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
  return candidates.find((type) => MediaRecorder.isTypeSupported?.(type));
}

export function useVoiceRecorder(): UseVoiceRecorder {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<RecorderError | null>(null);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const releaseStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  const start = useCallback(async (): Promise<boolean> => {
    setError(null);

    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      setError('unsupported');
      return false;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];

      const mimeType = pickMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      recorder.start();
      recorderRef.current = recorder;
      setIsRecording(true);
      return true;
    } catch (err) {
      const name = (err as DOMException)?.name;
      setError(name === 'NotAllowedError' || name === 'SecurityError' ? 'permission-denied' : 'failed');
      releaseStream();
      return false;
    }
  }, [releaseStream]);

  const stop = useCallback((): Promise<Blob | null> => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === 'inactive') {
      setIsRecording(false);
      return Promise.resolve(null);
    }

    return new Promise((resolve) => {
      recorder.onstop = () => {
        const type = recorder.mimeType || 'audio/webm';
        const blob = new Blob(chunksRef.current, { type });
        chunksRef.current = [];
        recorderRef.current = null;
        releaseStream();
        setIsRecording(false);

        // A blob this small holds no speech — treat it as nothing said rather
        // than shipping silence to the API.
        if (blob.size < 1200) {
          setError('no-audio');
          resolve(null);
          return;
        }
        resolve(blob);
      };
      recorder.stop();
    });
  }, [releaseStream]);

  const cancel = useCallback(() => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      recorder.onstop = null;
      recorder.stop();
    }
    chunksRef.current = [];
    recorderRef.current = null;
    releaseStream();
    setIsRecording(false);
  }, [releaseStream]);

  return { isRecording, start, stop, cancel, error };
}
