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
  /**
   * Live input loudness, 0..1, while recording. Drives the ring around the mic
   * so the user can see their voice registering — proof the microphone is
   * actually hearing them, without any streaming transcription.
   */
  level: number;
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

  const [level, setLevel] = useState(0);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const rafRef = useRef<number | null>(null);

  const stopMeter = useCallback(() => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
    audioCtxRef.current?.close().catch(() => {});
    audioCtxRef.current = null;
    setLevel(0);
  }, []);

  const releaseStream = useCallback(() => {
    stopMeter();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, [stopMeter]);

  /** Read RMS loudness off the live stream on each animation frame. */
  const startMeter = useCallback((stream: MediaStream) => {
    try {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      audioCtxRef.current = ctx;
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 512;
      ctx.createMediaStreamSource(stream).connect(analyser);

      const data = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteTimeDomainData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i += 1) {
          const v = (data[i] - 128) / 128;
          sum += v * v;
        }
        const rms = Math.sqrt(sum / data.length);
        // Speech RMS sits well below 1, so scale it into a usable range.
        setLevel(Math.min(1, rms * 4));
        rafRef.current = requestAnimationFrame(tick);
      };
      tick();
    } catch {
      // Metering is decorative; recording must still work without it.
    }
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
      startMeter(stream);
      setIsRecording(true);
      return null;
    } catch (err) {
      releaseStream();
      return fail(classify(err));
    }
  }, [fail, releaseStream, startMeter]);

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

  return { isRecording, level, start, stop, cancel, error };
}
