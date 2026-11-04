# -*- coding: utf-8 -*-
"""tooling 学科来源锚点重写（批次 T1，6 章 24 条）。

依据：逐章 grep concept/*.md 的真实 `##` 标题，按「文件序号.文件内小节序号」重编 §。
本学科四个仓库（the-book-of-secret-knowledge / ohmyzsh / the-art-of-command-line /
devops-exercises）与各章贴合度不均，Docker 两章（tool-ch05/06）尤其要挑真正相关的入口，
不能拿 oh-my-zsh 的 `lib/` 硬凑。
"""
import json
import os
import re

MANIFEST = "content/tooling/_manifest.json"
CH_DIR = "content/tooling"

RE_GH_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([\d,]+)\s*\|\s*([^|]*?)\s*\|\s*(.*?)\s*\|\s*$"
)


def split_note(note: str) -> tuple[str, str]:
    if " · " not in note:
        return "全章", note
    head, tail = note.split(" · ", 1)
    return head.strip(), tail.strip()


def rewrite_goals_table(cid: str, notes: list[str]) -> tuple[bool, str]:
    path = os.path.join(CH_DIR, cid, "goals.md")
    if not os.path.exists(path):
        return False, "goals.md 不存在"
    with open(path, encoding="utf-8") as f:
        s = f.read()
    lines = s.split("\n")

    try:
        start = next(i for i, ln in enumerate(lines) if ln.startswith("## 本章 GitHub"))
    except StopIteration:
        return False, "找不到「## 本章 GitHub」小节"
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break

    row_idx = [i for i in range(start, end) if RE_GH_ROW.match(lines[i])]
    if not row_idx:
        return False, "小节内无表格行"
    if len(row_idx) != len(notes):
        return False, f"表格 {len(row_idx)} 行、notes {len(notes)} 条，不匹配"

    for i, note in zip(row_idx, notes):
        m = RE_GH_ROW.match(lines[i])
        head, tail = split_note(note)
        lines[i] = (
            f"| {m.group(1)} | [{m.group(2)}]({m.group(3)}) | {m.group(4)} "
            f"| {head} | {tail} |"
        )

    out = "\n".join(lines)
    if out == s:
        return True, "已是同源"
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    return True, f"表格 {len(row_idx)} 行已同步"


NOTES: dict[str, list[str]] = {
    # ---------------- tool-ch01 Linux 基础：文件系统与权限 ----------------
    "tool-ch01": [
        "§1.2 inode 里到底有什么 · 读 `topics/linux/README.md`："
        "它把磁盘相关排障题按「症状」组织，其中「`df` 报满但 `du` 加起来没那么多」正是 inode 被占满"
        "或「已删除但仍被打开」的文件；配合 §1.3 三条反直觉推论，"
        "就能把「磁盘满了」拆成「块满」与「inode 满」两种现场",

        "§2.2 核心难点：rwx 对目录的含义完全不同 · 看 `topics/linux/exercises/`："
        "权限题会要求你只给某用户「进得去但列不出」的组合，答案只能靠「目录 `x` 管进入、`r` 管列出」来凑；"
        "做完再回本章验证那条：`ls dir` 能列但 `stat dir/file` 报 Permission denied，就是缺 `x`",

        "§4.6 组合成真实工具：四条经典管道 · 读 `the-art-of-command-line/README.md` 的"
        "「文件及数据处理」一节：`find` / `xargs` / `grep` 的组合用法给了可直接抄的一行命令；"
        "读时对照 §4.5「find 是文件系统的查询语言」——`-print0` + `xargs -0` 为什么必要，"
        "在文件名带空格时一眼可见",

        "§2.3 umask：权限的「默认值生成器」 · 看 `topics/linux/exercises/` 里新建文件与目录的题目："
        "`chmod 755` 与 `chmod u+x` 的等价关系、`umask 022` 下新建文件为什么是 644 而不是 755，"
        "题后都有答案；先把 §2.5 权限判定顺序读完再做题，才能解释「属主是 root 为什么我还是能读」",
    ],
    # ---------------- tool-ch02 Linux 进程、管道与 Shell 脚本 ----------------
    "tool-ch02": [
        "§3.2 xargs/find -exec/tee：批量与组合的工程取舍 · 读 `the-art-of-command-line/README.md` 的"
        "「一行命令」部分：它把常见运维动作压成单行，读的时候盯住每行用 `xargs` 还是 `-exec`"
        "——前者批量传参、后者逐个执行，差别在 §3.1「管道本质是 fd 表复制」之后才讲得清",

        "§4.1 变量、条件、循环、$? 与 set -euo pipefail · 读 `oh-my-zsh.sh` 开头的选项设置："
        "`setopt` 系列让脚本遇错即停、未定义变量报错——这是「脚本别默默跑错」的开关；"
        "对照 bash 的 `set -euo pipefail` 逐条看，就明白 §5.4「管道的退出码陷阱」为什么只能靠 `pipefail` 解",

        "§1.2 进程状态机：R / S / D / Z / T 与僵尸、孤儿 · 读 `topics/os/README.md` 的进程相关题目："
        "它要求你解释「为什么 `kill -9` 杀不掉 D 状态进程」，答案在状态机里——"
        "D 是等待不可中断 IO，信号要等系统调用返回才送达；这正是本章「信号的递送模型」的边界",

        "§3.1 管道与重定向的本质：fd 表的复制与重定向 · 看 `topics/linux/exercises/`："
        "`|`、`>`、`2>`、`tee` 的差别被拆成若干小问，答错会立刻暴露理解漏洞；"
        "做完再回 §2.1 信号的递送模型，就明白 `kill` 为什么是「发信号」而不是「杀掉」",
    ],
    # ---------------- tool-ch03 Git 核心 ----------------
    "tool-ch03": [
        "§3.1 快进合并 vs 三方合并（非快进） · 读 `topics/git/branch_01.md` 与 `solutions/branch_01_solution.md`："
        "题目要求在两条分叉分支上完成合并，答案里能看到 fast-forward 与 `--no-ff` 两种结果的图；"
        "读之前先看 §1.2「tree 与 commit 是快照而非差异」——"
        "正因为存快照，三方合并才需要 `merge-base` 找共同祖先",

        "§4.1 reset 三模式 + checkout/restore/revert 的区别 · 读 `plugins/git/git.plugin.zsh`："
        "几十个别名把长命令压成两三个字母，理解它们等于理解「日常 Git 的主力命令是哪些」；"
        "重点找 `grhh`（reset --hard）与 `gco`（checkout）这对——"
        "它们分别对应 §4.1 的「动哪个区」与 §4.2 的「HEAD 怎么动」",

        "§1.1 三类核心对象（blob/tree/commit）与内容寻址（CAS） · 读 `topics/git/commit_01.md` 与"
        "`solutions/commit_01_solution.md`：题目让你解释「同一个文件改一行，为什么 hash 全变而其他文件不变」；"
        "答案就落在 blob 内容寻址上——这正是 §2.1 三区模型里 `add` 把 blob 写进对象库那一步",

        "§2.2 分支是指向 commit 的指针；HEAD 是「当前位置」 · 读 `topics/git/squashing_commits.md`："
        "压缩提交本质上是在移动分支指针，而不改 commit 内容；"
        "对照 §4.2 的 detached HEAD——那时 HEAD 直接指向 commit 而非分支，"
        "所以新提交没有分支认领，这才需要 `reflog` 救援",
    ],
    # ---------------- tool-ch04 Git 协作 ----------------
    "tool-ch04": [
        "§4.2 仓库卫生：`.gitignore`、`.gitattributes` 与 Git LFS · 看 `the-art-of-command-line/README.md` 里"
        "与 `git` 相关的条目：它给了清理与检查的一行命令；"
        "注意 `git gc` / `git prune` 会真的删掉未引用对象——这正是 §3.2 reflog 救援网失效的边界，"
        "所以本章强调「先确认 reflog 里没有要救的东西再 prune」",

        "§1.2 push 为什么被拒绝，以及 `--force-with-lease` 为什么比 `--force` 安全 · "
        "读 `plugins/git/` 里的 `gst`/`gd`/`gl` 别名：把「看状态 → 看差异 → 看历史」压成三个动作，形成固定节奏；"
        "push 被拒时正是这套节奏救场——先 `gst` 看本地领先什么、`gl` 看远端多了什么，再决定 rebase 还是 merge",

        "§2.2 冲突标记、解决流程与 `rerere` · 读 `topics/git/README.md` 的合并与冲突题目："
        "它要求按「先 `git status` 看冲突文件、再逐个处理 `<<<<<<<` 标记、最后 `add` 结束合并」的顺序操作"
        "——顺序错了会卡在中间态；读时对照 §2.1「冲突的充要条件是两边改了同一段」，"
        "就明白为什么有些改动永远不冲突",

        "§4.1 分支策略选型（Git Flow / GitHub Flow / Trunk Based）与 PR 流程 · 看 `topics/git/branch_01.md`："
        "题目要求从指定基点切分支再合并回去，答案是「什么情况下该从哪个分支切」的具体示例；"
        "配合 §3.1 三种「复制/抵消」语义，就能说清 hotfix 该 cherry-pick 还是 merge 回主干",
    ],
    # ---------------- tool-ch05 Docker 基础 ----------------
    "tool-ch05": [
        "§1.1 容器 = namespace（隔离视图）+ cgroup（限制用量）+ 共享内核 · 看 `topics/containers/README.md` 与 "
        "`run_forest_run.md`：前者解释容器与虚拟机的边界，后者让你在同机上跑多个容器观察隔离；"
        "做完再读 §1.2 三方权衡，就明白隔离强度差在哪里（共享内核意味着内核漏洞无法隔离）",

        "§2.1 镜像 = 只读层的有序栈 + 内容寻址 · 读 `topics/containers/image_layers.md`："
        "它要求你解释「同一个 `RUN` 写在 Dockerfile 不同位置为什么层数不同」；"
        "这是本章最有说服力的一条验证——层是只读且不可合并的，"
        "所以 §2.2 的 overlayfs 只能叠不能改",

        "§4.1 指令语义：CMD vs ENTRYPOINT、COPY vs ADD · 读 `topics/containers/write_containerfile_run_container.md`："
        "题目要求你写一份完整 Dockerfile 并跑起来，答案会展示 `CMD` 与 `ENTRYPOINT` 组合时的参数覆盖规则；"
        "对照 §3.1「可写层归属容器实例」，就明白为什么 `docker exec` 里改的配置在 `docker rm` 后消失",

        "§2.2 联合文件系统 overlayfs：lower / upper / merged / work · 读 `topics/containers/working_with_images.md`："
        "它让你对比镜像大小与 `docker history` 输出的层结构；"
        "配合 §3.3 数据卷——写入 merged 目录会落到 upper 层，"
        "这解释了「容器里明明改了文件，重启后又变回去」，要持久化必须挂卷",
    ],
    # ---------------- tool-ch06 Docker Compose 与部署 ----------------
    "tool-ch06": [
        "§4.4 常见故障排查：症状 → 根因 → 处置 · 看 `topics/containers/running_containers.md`："
        "题目按「容器起不来 / 起来了但连不通 / 起来了但立刻退出」分场景排查；"
        "这套分层正是本章排障表的骨架，先分清「没起来」还是「起来了但连不通」，比盲查日志快得多",

        "§2.2 环境变量：五级优先级与变量插值 · 读 `lib/` 里对 `PATH` 的处理："
        "容器里同样靠环境变量注入配置，理解 Shell 的变量作用域能避免「变量在容器里读不到」；"
        "关键要分清 compose 文件里的 `${VAR}`（编排时插值）与容器内的运行时变量——这是两级不同的作用点",

        "§1.2 网络：自定义 bridge、服务名即 DNS、暴露 vs 发布 · 读 `topics/containers/containerized_web_server.md`"
        "与 `flask_container_ci2`：前者验证服务名解析，后者展示多容器间的网络打通；"
        "配合本章 `expose` 与 `ports` 的区别，就能解释「同网段服务名能通、宿主机 curl 不通」",

        "§2.1 数据卷：命名卷 vs 绑定挂载，持久化与备份 · 读 `topics/containers/containerized_db_persistent_storage.md`："
        "题目要求让数据库数据在容器重建后仍存在，答案对比命名卷与绑定挂载两种写法；"
        "这直接验证本章那条——容器的可写层随实例消亡，"
        "只有卷是「越过容器生命周期」的存储",
    ],
}


def main() -> None:
    with open(MANIFEST, "rb") as fb:
        nl = "\r\n" if b"\r\n" in fb.read() else "\n"
    data = json.load(open(MANIFEST, encoding="utf-8"))

    done = 0
    changed = False
    for ch in data.get("chapters", []):
        cid = ch.get("id")
        if cid not in NOTES:
            continue
        new = NOTES[cid]
        res = ch.setdefault("resources", {})
        old = res.get("github_notes", [])
        if len(old) != len(new):
            print(f"!! {cid} 原 {len(old)} 条、新 {len(new)} 条，不匹配，跳过")
            continue
        if old != new:
            res["github_notes"] = new
            changed = True
        done += 1
        ok, msg = rewrite_goals_table(cid, new)
        print(f"{'OK ' if ok else '!! '}{cid}: notes {len(new)} 条｜{msg}")

    if changed:
        with open(MANIFEST, "w", encoding="utf-8", newline=nl) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"manifest 已写盘（{done} 章）")
    else:
        print(f"manifest 已是目标状态（{done} 章），未写盘")


if __name__ == "__main__":
    main()
