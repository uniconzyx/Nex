/**
 * HelpPage.tsx —— 使用说明
 *
 * 从「设置」与「我的」进入。目标：第一次打开的人不用问人，照着做就能学完一章、判一道题。
 * 全部内容与真实功能对齐，不写没做的能力（账号同步、云端进度）。
 */
import type { KmPage } from '../lib/nav';

export function HelpPage({ onNavigate }: { onNavigate: (page: KmPage) => void }) {
  return (
    <div className="km-view">
      <section className="km-card">
        <h3>五分钟上手</h3>
        <p className="km-hint" style={{ marginTop: 0 }}>
          不用注册、不用联网、不用装数据库。进度自动存在本机，关掉再开还在。
        </p>
        <ol className="help-steps">
          <li>
            <b>选学科</b>
            <span>
              在「知识试炼区」顶部切换 C/C++、Java、Python 等 13 个方向；首页的「下一章」会跟着换。
            </span>
          </li>
          <li>
            <b>学一章</b>
            <span>
              展开任意章节看摘要、前置知识与延伸仓库；读完点「标记已掌握」，+20 EXP。
            </span>
          </li>
          <li>
            <b>练一题</b>
            <span>
              进「试炼实验室」，选语言、改示例代码、点「提交判题」；结果会逐用例给出耗时与内存。
            </span>
          </li>
          <li>
            <b>做项目</b>
            <span>
              「BOSS 项目实战」按 T1 能跑起来 → T4 能进简历分四档，每个项目都有验收清单。
            </span>
          </li>
          <li>
            <b>看笔记</b>
            <span>「考研手札」是 11408 的索引与要点，只存链接和提纲，点「看原文」跳 GitHub。</span>
          </li>
        </ol>
        <div className="help-actions">
          <button type="button" className="km-btn km-btn-primary km-btn-sm" onClick={() => onNavigate('learn')}>
            去知识试炼区
          </button>
          <button type="button" className="km-btn km-btn-ghost km-btn-sm" onClick={() => onNavigate('lab')}>
            去判题台
          </button>
        </div>
      </section>

      <section className="km-card">
        <h3>判题怎么用</h3>
        <div className="help-split">
          <div className="help-pane">
            <b>桌面端（.exe）</b>
            <p className="km-hint">
              打开就能判。go-judge 沙箱随安装包一起装好，不依赖 Docker，也不需要启动任何服务。
            </p>
          </div>
          <div className="help-pane">
            <b>手机端（.apk）</b>
            <p className="km-hint">
              手机不跑编译器。先在电脑打开客户端，手机连同一个 Wi-Fi，
              在判题台顶部填电脑地址（形如 <code>192.168.1.5:8080</code>）再点「测试连接」。
            </p>
          </div>
        </div>
        <p className="km-hint">
          判题比对会忽略行尾空格与末尾空行；编译错误会完整显示 g++ / javac 的诊断信息。
        </p>
      </section>

      <section className="km-card">
        <h3>账号与数据</h3>
        <div className="km-kv">
          <span>当前模式</span>
          <b>本地模式 · 无需登录</b>
        </div>
        <div className="km-kv">
          <span>数据存放</span>
          <b>本机 localStorage</b>
        </div>
        <div className="km-kv">
          <span>是否上传</span>
          <b>不上传</b>
        </div>
        <p className="km-hint">
          登录只用于多设备同步，目前尚未开放；不登录也能用全部离线功能。
          换设备前到「设置 → 导出进度 JSON」，在新设备上导入即可。
        </p>
      </section>

      <section className="km-card">
        <h3>常见问题</h3>
        <dl className="help-faq">
          <dt>判题提示「环境检测失败 / 连不上电脑」</dt>
          <dd>
            手机端先确认电脑地址填对、在同一 Wi-Fi；电脑端首次启动时 Windows 防火墙要允许「专用网络」。
            桌面端出现这条，说明安装包缺少 <code>binaries/go-judge.exe</code>，请用完整便携包解压后运行。
          </dd>
          <dt>换了电脑，进度没了</dt>
          <dd>进度只在本机。旧电脑「设置 → 导出进度 JSON」，新电脑导入同一份文件。</dd>
          <dt>想要深色模式</dt>
          <dd>顶栏的月亮图标，或「设置 → 外观 → 深色模式」。桌面与手机同时生效。</dd>
          <dt>为什么有些页面是空的</dt>
          <dd>怪物图鉴、剧情日志、背包、支线、成就、衣柜要等真实使用数据（判题历史、签到、收藏）逐步解锁。</dd>
        </dl>
      </section>
    </div>
  );
}

export default HelpPage;
