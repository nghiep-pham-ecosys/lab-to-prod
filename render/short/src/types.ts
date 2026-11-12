export type Theme = { bg: string; bg2?: string; fg: string; muted: string; accent: string; line: string; panel: string; panel_fg: string; panel_accent: string; foil?: string[] };

export type Scene =
  | { type: 'title'; text: string; say: string; seconds: number }
  | { type: 'code'; code: string[]; say: string; seconds: number }
  | { type: 'text'; text: string; note?: string; say: string; seconds: number }
  | { type: 'outro'; say: string; seconds: number };

export type ShortProps = {
  title: string;
  kicker: string;
  scenes: Scene[];
  theme: Theme;
  fonts: { display: string; body: string; mono: string };
  brandKey: string;
  style: { mark: string; wordmark: string; lockup?: boolean };
  name: string;
};
