import React, { useState } from 'react';
import { Send } from 'lucide-react';

interface OrcaTextInputProps {
  placeholder?: string;
  onSubmit: (text: string) => void;
  disabled?: boolean;
}

export const OrcaTextInput: React.FC<OrcaTextInputProps> = ({
  placeholder = 'Type your question…',
  onSubmit,
  disabled = false,
}) => {
  const [value, setValue] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!value.trim() || disabled) return;
    onSubmit(value.trim());
    setValue('');
  };

  return (
    <form
      onSubmit={handleSubmit}
      id="orca-ask-text-form"
      className="w-full relative flex items-center select-none"
    >
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        id="orca-ask-text-input"
        aria-label="Type your question about the sea"
        className="w-full py-2.5 sm:py-3 pl-4 pr-12 rounded-full bg-white/95 border border-[#D0DFEB] focus:border-[#062A43] focus:bg-white text-[14px] min-[390px]:text-[14.5px] text-[#062A43] placeholder-[#8198AA] font-ui shadow-2xs focus:outline-hidden transition-all duration-150"
      />

      <button
        type="submit"
        disabled={!value.trim() || disabled}
        id="orca-ask-send-btn"
        aria-label="Send typed question"
        className="absolute right-1.5 w-[34px] h-[34px] rounded-full bg-[#062A43] hover:bg-[#06365A] disabled:opacity-40 disabled:hover:bg-[#062A43] text-white flex items-center justify-center transition-all cursor-pointer disabled:cursor-not-allowed active:scale-95"
      >
        <Send size={15} className="stroke-[2.3] -ml-0.5" />
      </button>
    </form>
  );
};
