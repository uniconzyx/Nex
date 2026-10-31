/**
 * MonsterSprite.tsx —— 程序化怪物形象（图鉴素材）
 * ============================================================================
 * 不引入图片资源，全部由 questionId 哈希出的参数生成：
 *   体型宽高、眼睛间距、角数、倾斜角、颜色都不同 → 每道题有稳定且唯一的形象。
 *
 * 表情分三态：
 *   wild  皱眉 + 尖牙（还没收服）
 *   tamed 眯眼 + 微笑 + 光环（已收服）
 *   hit   短暂受击（遭遇弹窗里用的抖动帧）
 * ============================================================================
 */
import { seedOf, visualOf } from '../lib/bestiary';
import type { Monster } from '../lib/gameTypes';

export function MonsterSprite({
  monster,
  size = 96,
  mood,
  className = '',
}: {
  monster: Monster;
  size?: number;
  mood?: 'hit';
  className?: string;
}) {
  const v = visualOf(monster);
  /**
   * 渐变 id 必须全域唯一：同页多只怪时，id 撞车会让所有 SVG 都用第一只的颜色。
   * 用稳定哈希而不是 questionId 原文，顺带兼容含中文/斜杠的 id。
   */
  const gradId = `mg-${seedOf(monster.questionId).toString(36)}`;
  const bodyRx = 34 * v.bodyW;
  const bodyRy = 27 * v.bodyH;
  const tamed = v.tamed;

  return (
    <svg
      className={`km-mon-spr${tamed ? ' is-tamed' : ' is-wild'}${mood === 'hit' ? ' is-hit' : ''}${
        v.rarity === 'shiny' ? ' is-shiny' : ''
      } ${className}`}
      width={size}
      height={size}
      viewBox="0 0 120 120"
      role="img"
      aria-label={`${v.label}${tamed ? '（已收服）' : ''}`}
    >
      <defs>
        <radialGradient id={gradId} cx="38%" cy="30%" r="78%">
          <stop offset="0%" stopColor={v.color} stopOpacity="0.95" />
          <stop offset="62%" stopColor={v.color} stopOpacity="0.55" />
          <stop offset="100%" stopColor={v.color} stopOpacity="0.22" />
        </radialGradient>
      </defs>

      {/* 稀有度光环：变异为虚线旋转环 */}
      <circle
        cx="60"
        cy="62"
        r="46"
        fill="none"
        stroke={v.ring}
        strokeWidth={v.rarity === 'boss' ? 2.4 : 1.6}
        strokeDasharray={v.rarity === 'shiny' ? '5 6' : undefined}
        className="km-mon-halo"
      />

      {/* 角：数量由稀有度决定 */}
      <g transform={`rotate(${v.tilt} 60 44)`} fill={v.color} opacity="0.85">
        {Array.from({ length: v.horns }).map((_, i) => {
          const spread = 13;
          const x = 60 + (i - (v.horns - 1) / 2) * spread;
          return <path key={i} d={`M${x} 36 l5 -13 l5 13 z`} />;
        })}
      </g>

      {/* 身体 */}
      <ellipse cx="60" cy={64} rx={bodyRx} ry={bodyRy} fill={`url(#${gradId})`} stroke={v.color} strokeWidth="1.4" />

      {/* 小脚：让轮廓不是一个纯椭圆 */}
      <ellipse cx={60 - bodyRx * 0.45} cy={64 + bodyRy * 0.92} rx="7" ry="4.5" fill={v.color} opacity="0.55" />
      <ellipse cx={60 + bodyRx * 0.45} cy={64 + bodyRy * 0.92} rx="7" ry="4.5" fill={v.color} opacity="0.55" />

      {/* 眼睛 */}
      {tamed ? (
        <g stroke="#25384c" strokeWidth="2.6" strokeLinecap="round" fill="none" opacity="0.9">
          <path d={`M${60 - v.eyeGap - 6} ${v.eyeY} q6 -6 12 0`} />
          <path d={`M${60 + v.eyeGap - 6} ${v.eyeY} q6 -6 12 0`} />
        </g>
      ) : (
        <g>
          <ellipse cx={60 - v.eyeGap} cy={v.eyeY} rx="6.4" ry="7" fill="#fdfdff" opacity="0.95" />
          <ellipse cx={60 + v.eyeGap} cy={v.eyeY} rx="6.4" ry="7" fill="#fdfdff" opacity="0.95" />
          <circle cx={60 - v.eyeGap + 1} cy={v.eyeY + 1.4} r="3.1" fill="#25384c" />
          <circle cx={60 + v.eyeGap + 1} cy={v.eyeY + 1.4} r="3.1" fill="#25384c" />
          {/* 怒眉：wild 的辨识度主要来自这两笔 */}
          <path
            d={`M${60 - v.eyeGap - 8} ${v.eyeY - 10} l12 4`}
            stroke="#25384c"
            strokeWidth="2.2"
            strokeLinecap="round"
            opacity="0.75"
          />
          <path
            d={`M${60 + v.eyeGap + 8} ${v.eyeY - 10} l-12 4`}
            stroke="#25384c"
            strokeWidth="2.2"
            strokeLinecap="round"
            opacity="0.75"
          />
        </g>
      )}

      {/* 嘴：收服后是笑，未收服是尖牙 */}
      {tamed ? (
        <path
          d={`M${60 - 10} ${v.eyeY + 15} q10 8 20 0`}
          fill="none"
          stroke="#25384c"
          strokeWidth="2.4"
          strokeLinecap="round"
          opacity="0.85"
        />
      ) : (
        <g fill="#fdfdff" opacity="0.9">
          <path d={`M${60 - 9} ${v.eyeY + 16} l4 7 l4 -7 z`} />
          <path d={`M${60 + 1} ${v.eyeY + 16} l4 7 l4 -7 z`} />
        </g>
      )}

      {/* 已收服：头顶小星 */}
      {tamed && (
        <path
          d="M60 16 l2.4 5.6 6 .5 -4.6 3.9 1.4 5.9L60 28.8 54.8 31.9l1.4-5.9-4.6-3.9 6-.5z"
          fill="#e3b44f"
          opacity="0.9"
        />
      )}
    </svg>
  );
}

export default MonsterSprite;
