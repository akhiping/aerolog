import { useState, useRef, useCallback } from "react";

interface MicButtonProps {
  onTranscript: (text: string) => void;
  language: string;
  disabled?: boolean;
}

export default function MicButton({ onTranscript, language, disabled }: MicButtonProps) {
  const [listening, setListening] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);

  const langMap: Record<string, string> = {
    en: "en-US",
    hi: "hi-IN",
    te: "te-IN",
  };

  const toggle = useCallback(() => {
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const w = window as any;
    const SpeechRecognitionCtor = w.SpeechRecognition ?? w.webkitSpeechRecognition;

    if (!SpeechRecognitionCtor) {
      alert("Speech recognition not supported in this browser. Use the text input instead.");
      return;
    }

    const recognition = new SpeechRecognitionCtor();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = langMap[language] ?? "en-US";

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onresult = (e: any) => {
      const last = e.results[e.results.length - 1];
      if (last.isFinal) {
        onTranscript(last[0].transcript);
      }
    };
    recognition.onerror = () => setListening(false);
    recognition.onend = () => setListening(false);

    recognition.start();
    recognitionRef.current = recognition;
    setListening(true);
  }, [listening, onTranscript, language]);

  return (
    <button
      onClick={toggle}
      disabled={disabled}
      className={`relative w-20 h-20 rounded-full flex items-center justify-center transition-all ${
        disabled
          ? "bg-gray-700 cursor-not-allowed"
          : listening
          ? "bg-red-600 hover:bg-red-500"
          : "bg-blue-600 hover:bg-blue-500"
      }`}
    >
      {listening && (
        <span className="absolute inset-0 rounded-full bg-red-500/40 animate-pulse-ring" />
      )}
      <svg
        className="w-8 h-8 text-white"
        fill="currentColor"
        viewBox="0 0 24 24"
      >
        {listening ? (
          <rect x="6" y="6" width="12" height="12" rx="2" />
        ) : (
          <path d="M12 14a3 3 0 003-3V5a3 3 0 00-6 0v6a3 3 0 003 3zm5-3a5 5 0 01-10 0H5a7 7 0 0014 0h-2zm-5 9a1 1 0 01-1-1v-2h2v2a1 1 0 01-1 1z" />
        )}
      </svg>
    </button>
  );
}
