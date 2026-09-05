import { useCallback, useRef, useState } from 'react';

/**
 * Microphone capture via MediaRecorder.
 *
 * This replaces the browser Web Speech API, which only recognised a handful of
 * languages and silently transcribed Tamil, Telugu and Malayalam as English.
 * Here we just capture audio; Sarvam does the recognition server-side and
 * identifies the language itself.
 *
 * start() and stop() return the failure reason directly rather than leaving the
 * caller to read `error`. React state is not visible on the line after the call
 * that set it, so a caller reading `error` immediately got the previous render's
 * value — which made every failure look like silence, whatever really happened.
 */

export type RecorderError =
  | 'permission-denied'
  | 'no-microphone'
  | 'microphone-busy'
  | 'unsupported'
  | 'no-audio'
  | 'failed';

export interface StopResult {
  blob: Blob | null;
  error: RecorderError | null;
}

interface UseVoiceRecorder {
  isRecording: boolean;
  /** Returns null on success, or the reason recording could not start. */
  start: () => Promise<RecorderError | null>;
  stop: () => Promise<StopResult>;
  cancel: () => void;
  error: RecorderError | null;
}

/** Pick a container the browser can actually produce. */
function pickMimeType(): string | undefined {
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
  return candidates.find((type) => MediaRecorder.isTypeSupported?.(type));
}

/** Map a getUserMedia DOMException to something we can explain to a fisherman. */
function classify(err: unknown): RecorderError {
  const name = (err as DOMException)?.name;
  if (name === 'NotAllowedError' || name === 'SecurityError') return 'permission-denied';
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError') return 'no-microphone';
  if (name === 'NotReadableError' || name === 'TrackStartError') return 'microphone-busy';
  return 'failed';
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

  const fail = useCallback((reason: RecorderError): RecorderError => {
    setError(reason);
    return reason;
  }, []);

  const start = useCallback(async (): Promise<RecorderError | null> => {
    setError(null);

    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      return fail('unsupported');
    }
    if (typeof MediaRecorder === 'undefined') {
      return fail('unsupported');
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
      return null;
    } catch (err) {
      releaseStream();
      return fail(classify(err));
    }
  }, [fail, releaseStream]);

  const stop = useCallback((): Promise<StopResult> => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === 'inactive') {
      setIsRecording(false);
      return Promise.resolve({ blob: null, error: 'failed' });
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
          resolve({ blob: null, error: 'no-audio' });
          return;
        }
        resolve({ blob, error: null });
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
