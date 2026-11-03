import React from 'react';
import { Composition } from 'remotion';
import { FontGate } from './theme';
import { S03Breakdown } from './S03Breakdown';
import { S05WriteOrder } from './S05WriteOrder';
import { S06Quiz } from './S06Quiz';
import { S07Recap } from './S07Recap';

/**
 * 统一 1280×720 / 30fps。
 * 时长按分镜：S03 16s / S05 15s / S06 14s / S07 4s。
 * FontGate 把每个 composition 都包住：字体没加载完不出帧，避免首帧字宽跳变。
 */
const withFonts = (C: React.FC) => {
  const Wrapped: React.FC = () => (
    <FontGate>
      <C />
    </FontGate>
  );
  return Wrapped;
};

export const Root: React.FC = () => (
  <>
    <Composition
      id="S03Breakdown"
      component={withFonts(S03Breakdown)}
      durationInFrames={480}
      fps={30}
      width={1280}
      height={720}
    />
    <Composition
      id="S05WriteOrder"
      component={withFonts(S05WriteOrder)}
      durationInFrames={450}
      fps={30}
      width={1280}
      height={720}
    />
    <Composition
      id="S06Quiz"
      component={withFonts(S06Quiz)}
      durationInFrames={420}
      fps={30}
      width={1280}
      height={720}
    />
    <Composition
      id="S07Recap"
      component={withFonts(S07Recap)}
      durationInFrames={120}
      fps={30}
      width={1280}
      height={720}
    />
  </>
);
