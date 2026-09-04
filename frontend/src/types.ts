export interface LanguageOption {
  code: string;
  name: string;
  nativeName: string;
  eyebrow: string;
  headlineLine1: string;
  headlineLine2: string;
  supporting: string;
  cta: string;
  trust: string;
}

export type ModalType = 'about' | 'how-it-helps' | 'safety' | 'get-started' | null;
