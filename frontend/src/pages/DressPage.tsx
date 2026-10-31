/**
 * DressPage.tsx —— 装扮衣柜（消费闭环）
 *
 * 8 套立绘都是真实素材（web-preview/assets/kaimao → public/assets/kaimao），
 * 选中后写入本地进度，右侧伙伴面板会立刻换装。
 *
 * 2026-10-30 起接入消费：
 *   · 每套标价，`default` 免费且永远拥有；
 *   · 未拥有 → 点击先出确认条，第二次点击才扣款，避免手滑掉 1600 结晶；
 *   · 余额不足时按钮禁用并直接写「还差 N 结晶」，不用点了才知道；
 *   · 每次购买都写进 coinLedger（`购买装扮：名字`），背包页能查到每一笔。
 *
 * 老用户兼容在 lib/progress 的 sanitizeState：正穿着的那件会被自动视为已拥有，
 * 不会因为这次收费升级把衣服扒掉。
 */
import { useState } from 'react';

import { buyOutfit, setOutfit, useProgress } from '../lib/progress';

interface Outfit {
  id: string;
  name: string;
  img: string;
  desc: string;
  tag: string;
  /** 结晶价格；0 = 初始拥有 */
  price: number;
}

export const OUTFITS: Outfit[] = [
  {
    id: 'default',
    name: '日常便装',
    img: '/assets/kaimao/mood-idle.png',
    desc: '初始服装，怎么穿都精神',
    tag: '默认',
    price: 0,
  },
  {
    id: 'cape',
    name: '见习披风',
    img: '/assets/kaimao/outfit-cape.png',
    desc: '冒险者的第一件行头，风一吹就有干劲',
    tag: '入门',
    price: 200,
  },
  {
    id: 'scarf',
    name: '绒线围巾',
    img: '/assets/kaimao/outfit-scarf.png',
    desc: '冬日限定，学习时更暖和',
    tag: '季节',
    price: 320,
  },
  {
    id: 'glasses',
    name: '黑框眼镜',
    img: '/assets/kaimao/outfit-glasses.png',
    desc: '读源码专用，看起来更专注',
    tag: '气质',
    price: 420,
  },
  {
    id: 'nightprowler',
    name: '暗夜行者',
    img: '/assets/kaimao/outfit-nightprowler.png',
    desc: '深夜刷题套，低调但锋利',
    tag: '稀有',
    price: 680,
  },
  {
    id: 'cyberpunk',
    name: '赛博朋克',
    img: '/assets/kaimao/outfit-cyberpunk.png',
    desc: '霓虹配色，打扰到邻居不负责',
    tag: '史诗',
    price: 980,
  },
  {
    id: 'panda',
    name: '熊猫卫衣',
    img: '/assets/kaimao/outfit-panda.png',
    desc: '可爱度拉满，写 bug 也会被原谅',
    tag: '限定',
    price: 1200,
  },
  {
    id: 'wizard',
    name: '魔法学院长袍',
    img: '/assets/kaimao/outfit-wizard.png',
    desc: '念一句 std::move 就算施法',
    tag: '传说',
    price: 1600,
  },
];

export function DressPage() {
  const p = useProgress();
  const [pending, setPending] = useState<Outfit | null>(null);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const owned = new Set(p.ownedOutfits);

  const choose = (o: Outfit) => {
    setErr('');
    setMsg('');
    // 已拥有：直接换；未拥有：先出确认条，不在这里扣钱
    if (owned.has(o.id)) {
      setOutfit(o.id);
      setPending(null);
      return;
    }
    setPending(o);
  };

  const confirmBuy = () => {
    if (!pending) return;
    const r = buyOutfit(pending.id, pending.price, pending.name);
    if (!r.ok) {
      setErr(`买不了：${r.reason}`);
      return;
    }
    setMsg(`已买下「${pending.name}」并换上，花掉 ${r.paid} 结晶`);
    setPending(null);
    window.setTimeout(() => setMsg(''), 3600);
  };

  return (
    <div className="km-view">
      <section className="km-card">
        <div className="km-cont-top">
          <h3 style={{ margin: 0 }}>装扮衣柜 · 8 套</h3>
          <span className="pct">{p.coins} 结晶</span>
        </div>
        <p className="km-hint" style={{ marginTop: 6 }}>
          已拥有 {owned.size} / {OUTFITS.length} 套。点击换上；未拥有的会先问一句再扣结晶。
          买过的装扮永久归你，之后随便换不花钱。
        </p>
      </section>

      <section className="km-card">
        <div className="km-dress-grid">
          {OUTFITS.map((o) => {
            const has = owned.has(o.id);
            const wearing = p.outfit === o.id;
            const afford = p.coins >= o.price;
            const tagClass =
              o.tag === '传说' ? 'km-tag-lv' : o.tag === '史诗' ? 'km-tag-epic' : 'km-tag-gray';
            return (
              <button
                key={o.id}
                type="button"
                className={`km-dress${wearing ? ' on' : ''}${has ? '' : ' locked'}`}
                onClick={() => choose(o)}
                title={o.desc}
                aria-label={
                  has
                    ? `${o.name}，${wearing ? '穿着中' : '已拥有，点击换上'}`
                    : `${o.name}，未拥有，售价 ${o.price} 结晶${afford ? '' : '，余额不足'}`
                }
              >
                <span className={`km-tag ${tagClass}`}>{o.tag}</span>
                <img src={o.img} alt={o.name} loading="lazy" />
                <b>{o.name}</b>
                {wearing ? (
                  <span className="km-tag km-tag-ok">穿着中</span>
                ) : has ? (
                  <span className="dress-price owned">已拥有 · 点击换上</span>
                ) : (
                  <span className={`dress-price${afford ? '' : ' short'}`}>
                    {afford ? `${o.price} 结晶` : `还差 ${o.price - p.coins} 结晶`}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {pending && (
          <div className="dress-confirm">
            <p>
              买下「<b>{pending.name}</b>」将花 <b>{pending.price}</b> 结晶，余额 {p.coins} →{' '}
              {p.coins - pending.price}。
            </p>
            <div className="dress-confirm-actions">
              <button
                type="button"
                className="km-btn km-btn-primary km-btn-sm"
                onClick={confirmBuy}
                disabled={p.coins < pending.price}
              >
                {p.coins < pending.price ? `还差 ${pending.price - p.coins} 结晶` : '确认购买'}
              </button>
              <button
                type="button"
                className="km-btn km-btn-ghost km-btn-sm"
                onClick={() => setPending(null)}
              >
                再想想
              </button>
            </div>
          </div>
        )}

        {err && (
          <p className="km-hint" style={{ color: 'var(--km-bad)' }}>
            {err}
          </p>
        )}
        {msg && (
          <p className="km-hint" style={{ color: 'var(--km-ok)' }}>
            {msg}
          </p>
        )}
        <p className="km-hint">
          结晶来自清空试炼、收服怪物、掌握章节与签到。每一笔支出都能在「背包 → 结晶流水」里查到。
        </p>
      </section>
    </div>
  );
}
