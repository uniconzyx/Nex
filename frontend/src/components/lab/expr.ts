/**
 * 沙盒公式求值器（不 eval、不 new Function）
 * ═════════════════════════════════════════════════════════════════════
 * `interactive.json` 里的 sandbox 指标写成表达式字符串，例如
 *
 *   "expr": "ceil(bits - log2(pages))"
 *   "expr": "hitRate * hitCost + (1 - hitRate) * memCost"
 *
 * 为什么不用 `new Function`：这份数据将来会被别的宿主复用（App 内嵌、
 * 分享页），一旦有人能改 JSON 就等于能改任人执行任意脚本。这里只放行
 * 数字、标识符、四则/幂/比较/逻辑与 12 个纯函数，越界一律报错。
 *
 * 语法（优先级由低到高）
 *   ?:   ||   &&   == !=   比较   + -   * / %   一元 - !    ^（右结合）
 * 布尔当 1/0 参与运算，所以 `checks` 直接写 `levels <= 3` 即可。
 */

type Env = Record<string, number>;

const FN: Record<string, (...a: number[]) => number> = {
  min: (a, b) => Math.min(a, b),
  max: (a, b) => Math.max(a, b),
  abs: (a) => Math.abs(a),
  ceil: (a) => Math.ceil(a),
  floor: (a) => Math.floor(a),
  round: (a) => Math.round(a),
  sqrt: (a) => Math.sqrt(a),
  pow: (a, b) => Math.pow(a, b),
  log: (a) => Math.log(a),
  ln: (a) => Math.log(a),
  log2: (a) => Math.log2(a),
  log10: (a) => Math.log10(a),
  exp: (a) => Math.exp(a),
  clamp: (x, a, b) => Math.min(b, Math.max(a, x)),
  /** if(cond, then, else) —— 比三元更好读，且避免嵌套括号 */
  if: (c, a, b) => (c ? a : b),
};

const NUM = /^\d+(?:\.\d+)?/;
const IDENT = /^[A-Za-z_][A-Za-z0-9_]*/;

function tokenize(src: string): string[] {
  const out: string[] = [];
  let i = 0;
  while (i < src.length) {
    const c = src[i];
    if (/\s/.test(c)) {
      i++;
      continue;
    }
    const two = src.slice(i, i + 2);
    if (two === '**' || two === '>=' || two === '<=' || two === '==' || two === '!=' || two === '&&' || two === '||') {
      out.push(two);
      i += 2;
      continue;
    }
    if ('+-*/%^<>!?:(),'.includes(c)) {
      out.push(c);
      i++;
      continue;
    }
    const n = NUM.exec(src.slice(i));
    if (n) {
      out.push(n[0]);
      i += n[0].length;
      continue;
    }
    const id = IDENT.exec(src.slice(i));
    if (id) {
      out.push(id[0]);
      i += id[0].length;
      continue;
    }
    throw new Error(`公式里有不认识的字符：${c} @${i}`);
  }
  return out;
}

/**
 * 求值。`vars` 里可以塞参数和已算出的指标。
 * 抛错时上层显示成 `—` 而不是崩掉整页 —— 一条写错的公式不该毁掉整章交互。
 */
export function evalExpr(src: string, vars: Env = {}): number {
  const tk = tokenize(src);
  let p = 0;

  const peek = () => tk[p];
  const eat = (t?: string) => {
    if (t && tk[p] !== t) throw new Error(`期望 ${t}，实际 ${tk[p] ?? 'EOF'}`);
    return tk[p++];
  };

  // 一元
  const unary = (): number => {
    if (peek() === '-') {
      eat('-');
      return -unary();
    }
    if (peek() === '+') {
      eat('+');
      return unary();
    }
    if (peek() === '!') {
      eat('!');
      return unary() ? 0 : 1;
    }
    return power();
  };

  // 幂：右结合，且指数侧允许再取一元（2^-1）
  const power = (): number => {
    const base = primary();
    if (peek() === '^' || peek() === '**') {
      eat();
      return Math.pow(base, unary());
    }
    return base;
  };

  const primary = (): number => {
    const t = tk[p];
    if (t === undefined) throw new Error('公式意外结束');
    if (t === '(') {
      eat('(');
      const v = ternary();
      eat(')');
      return v;
    }
    if (NUM.test(t)) {
      p++;
      return parseFloat(t);
    }
    if (IDENT.test(t)) {
      p++;
      if (peek() === '(') {
        eat('(');
        const args: number[] = [];
        if (peek() !== ')') {
          args.push(ternary());
          while (peek() === ',') {
            eat(',');
            args.push(ternary());
          }
        }
        eat(')');
        const f = FN[t];
        if (!f) throw new Error(`不认识函数 ${t}`);
        return f(...args);
      }
      if (!(t in vars)) throw new Error(`未定义的量 ${t}`);
      return vars[t];
    }
    throw new Error(`公式里有不认识的符号 ${t}`);
  };

  const mul = (): number => {
    let v = unary();
    while (peek() === '*' || peek() === '/' || peek() === '%') {
      const op = eat();
      const r = unary();
      v = op === '*' ? v * r : op === '/' ? v / r : v % r;
    }
    return v;
  };

  const add = (): number => {
    let v = mul();
    while (peek() === '+' || peek() === '-') {
      const op = eat();
      const r = mul();
      v = op === '+' ? v + r : v - r;
    }
    return v;
  };

  const cmp = (): number => {
    let v = add();
    while (['<', '>', '<=', '>=', '==', '!='].includes(peek())) {
      const op = eat();
      const r = add();
      v =
        op === '<' ? (v < r ? 1 : 0)
        : op === '>' ? (v > r ? 1 : 0)
        : op === '<=' ? (v <= r ? 1 : 0)
        : op === '>=' ? (v >= r ? 1 : 0)
        : op === '==' ? (v === r ? 1 : 0)
        : v !== r ? 1 : 0;
    }
    return v;
  };

  const and = (): number => {
    let v = cmp();
    while (peek() === '&&') {
      eat('&&');
      const r = cmp();
      v = v && r ? 1 : 0;
    }
    return v;
  };

  const or = (): number => {
    let v = and();
    while (peek() === '||') {
      eat('||');
      const r = and();
      v = v || r ? 1 : 0;
    }
    return v;
  };

  const ternary = (): number => {
    const c = or();
    if (peek() === '?') {
      eat('?');
      const a = ternary();
      eat(':');
      const b = ternary();
      return c ? a : b;
    }
    return c;
  };

  const v = ternary();
  if (p < tk.length) throw new Error(`公式尾部有多余内容 ${tk.slice(p).join(' ')}`);
  return v;
}

/** 指标显示：整数位用千分位，小数位按 fmt 定 */
export function fmtNum(v: number, fmt?: 'int' | 'fix2' | 'pct'): string {
  if (!Number.isFinite(v)) return '—';
  if (fmt === 'int') return Math.round(v).toLocaleString('zh-CN');
  if (fmt === 'fix2') return v.toFixed(2);
  if (fmt === 'pct') return (v * 100).toFixed(1) + '%';
  if (Math.abs(v) >= 1000) return Math.round(v).toLocaleString('zh-CN');
  if (Number.isInteger(v)) return String(v);
  return v.toFixed(2);
}
