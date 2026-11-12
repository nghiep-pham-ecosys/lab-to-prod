import { Composition } from 'remotion';
import { Short } from './Short';
import type { ShortProps } from './types';

export const FPS = 30;

const defaultProps: ShortProps = {
  title: 'Sample',
  kicker: 'Series · Part 1',
  name: 'Nghiep Pham · Lab to Prod',
  brandKey: 'a',
  style: { mark: 'arrow', wordmark: 'arrow' },
  fonts: { display: 'Fraunces', body: 'Inter', mono: 'JetBrainsMono' },
  theme: { bg: '#1B1F23', fg: '#F6F1E7', muted: '#A39C8F', accent: '#5EEAD4', line: '#2A3036', panel: '#11151A', panel_fg: '#E8E2D6', panel_accent: '#5EEAD4' },
  scenes: [
    { type: 'title', text: 'A sample\nShort', say: 'This is a sample.', seconds: 3 },
    { type: 'outro', say: 'The end.', seconds: 2 },
  ],
};

export const Root = () => (
  <Composition
    id="Short"
    component={Short}
    width={1080}
    height={1920}
    fps={FPS}
    durationInFrames={150}
    defaultProps={defaultProps}
    calculateMetadata={({ props }) => ({
      durationInFrames: Math.round(props.scenes.reduce((sum, s) => sum + s.seconds, 0) * FPS),
    })}
  />
);
