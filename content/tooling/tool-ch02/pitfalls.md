# 常见陷阱：Linux 进程、管道与 Shell 脚本

> 每条都是「执行能通过、但结果或安全性是错的」类型。按「现象 → 根因 → 正确做法」组织。

1. **把 kill PID 当成 SIGKILL** —— 现象：进程没退，你以为 kill 失效了又连发几次。根因：kill 默认发 **SIGTERM(15)**，进程可以选择**忽略或延迟处理**（比如正在刷盘）。正确做法：先 kill PID（SIGTERM）给优雅退出机会；超时仍未退出再 kill -9 PID（SIGKILL）。把 SIGKILL 当首选会跳过清理逻辑，造成数据损坏或临时文件泄漏。

2. **用 SIGKILL 杀正在写数据的进程** —— 现象：数据库/日志进程被 kill -9 后文件损坏、索引不一致。根因：SIGKILL 是**不可捕获、不可阻塞、不可忽略**的，进程收到即被内核直接回收，**没有机会执行 atexit、flush、释放锁**。正确做法：优先 SIGTERM；只有确认进程已卡死（D 状态超时、死锁）才用 SIGKILL，且之后必须做一致性恢复（如 DB 的 crash recovery）。

3. **僵尸进程用 kill -9 杀不掉** —— 现象：ps 里一堆 <defunct>，kill -9 毫无反应。根因：僵尸已经死了，只是**父进程还没 wait() 回收它的退出状态**，残留一个 task_struct（占 pid 槽）。SIGKILL 对尸体无效。正确做法：杀掉**它的父进程**（或让父进程正确调用 wait/waitpid），父进程死后僵尸被 init/subreaper 收养并立即回收。

4. **误以为孤儿进程「丢失」了** —— 现象：父进程先退出，子进程还在跑，你担心它变成野进程。根因：父进程退出后，子进程会被 **init（pid 1）或最近的 subreaper 收养**，ppid 变成 1，调度与回收都正常。正确做法：这不是 bug；若你希望子进程随父退出而退出，应当显式处理 SIGHUP/SIGTERM 或 prctl(PR_SET_PDEATHSIG)。

5. **2>&1 > file 把 stderr 也写进了 file** —— 现象：想「stderr 和 stdout 都进文件」，但 stderr 还是打到了终端。根因：重定向是**按顺序、对 fd 表即时生效**的。2>&1 先把 fd 2 复制到「fd 1 当前指向的目标」（此时还是终端），随后 > file 才把 fd 1 指向 file——fd 2 仍指向终端。正确做法：写成 > file 2>&1（先把 fd 1 指向 file，再把 fd 2 复制过去），或现代写法 &> file / cmd > file 2>&1。

6. **echo $? 取到的是管道里最后一个命令的退出码** —— 现象：false | true; echo $? 打印 0，你以为「整条管道成功了」。根因：$? 只保存**最近一条命令**的退出码；管道整体退出码默认是**最后一个命令**的。正确做法：需要「任一失败即失败」用 set -o pipefail（此时 $? 取管道中第一个非零退出码）；需要每个命令的码用 ${PIPESTATUS[@]}。

7. **以为 set -e 能拦住管道里的失败** —— 现象：脚本里 curl ... | grep ok 失败（curl 500）但脚本继续跑、后续全错。根因：set -e 默认只看**整条管道最后一个命令**的退出码，中间的失败被忽略。正确做法：**必须**配 set -o pipefail，或显式检查 ${PIPESTATUS[0]}；推荐脚本开头永远 set -euo pipefail。

8. **set -e 下条件里的命令失败却不退出** —— 现象：if mycmd; then ...; fi 里 mycmd 失败，脚本没退出，你以为 set -e 失效了。根因：这是 set -e 的**标准例外**——if/while/until 的条件表达式、&&/|| 链中非末位的命令，其失败是「被预期用来控制流程」的，不触发退出。正确做法：真正需要「失败即停」的逻辑不要塞进条件；或在条件后单独 || exit 1。

9. **for 循环里文件名含空格被拆成多个参数** —— 现象：for f in $(ls); do ...; done 遇到 my file.txt 当成两个文件。根因：未加引号的 $(...) 会经历**词拆分（word splitting）**与路径展开（globbing）。正确做法：用 while IFS= read -r -d '' f; do ...; done < <(find ... -print0) 或 for f in ./*.txt; do [ -e "$f" ] || continue; ...; done，且 $f 永远加双引号。

10. **后台 & 进程在终端关闭后被 SIGHUP 杀掉** —— 现象：python server.py & 关掉终端后服务停了。根因：终端关闭会向**该会话的控制进程组**发 SIGHUP，后台进程默认属于该组。正确做法：用 nohup python server.py &（忽略 SIGHUP 并把输出重定向到 nohup.out），或更现代地 setsid/disown -h，最推荐交给 systemd 托管。

11. **export VAR 指望影响父 shell 或已启动的兄弟进程** —— 现象：在脚本里 export PATH=...，退出脚本后父 shell 的 PATH 没变。根因：环境变量**只能沿 fork 向下传给子进程**，不能回传给父 shell，也不能横向传给无关的兄弟进程。正确做法：要改「当前及之后所有 shell」用 source script.sh（在当前进程执行）；要持久化写 ~/.bashrc//etc/environment。

12. **cron 里脚本手动能跑、定时跑就报 command not found** —— 现象：手动 ./backup.sh 正常，cron 跑却 xxx: command not found。根因：cron 的**环境变量极简**（PATH 通常只有 /usr/bin:/bin，没有你交互 shell 的 PATH；HOME、LANG 也缺失）。正确做法：脚本里用**绝对路径**命令，或脚本开头显式 export PATH=/usr/local/bin:/usr/bin:/bin；在 crontab 里设置 PATH= 与 SHELL=；不要把依赖交互环境的别名写进 cron 脚本。

13. **xargs 默认按空白拆分，含空格文件名被破坏** —— 现象：find . -name '*.log' | xargs rm 删错文件。根因：xargs 默认按空白/换行切分，文件名含空格或换行就被拆碎；文件名以 - 开头还会被当成选项。正确做法：find ... -print0 | xargs -0 rm，或 find ... -delete，或 find ... -exec rm {} +（用 NUL 或批量传参，天然免疫空格）。

14. **find -exec cmd {} \; 导致海量进程创建** —— 现象：处理 10 万个文件时脚本奇慢且系统负载飙高。根因：\; 是「每匹配一个文件就 fork+exec 一次 cmd」，10 万文件 = 10 万次进程创建。正确做法：用 find ... -exec cmd {} +（+ 把多个文件批量传给一次 cmd，像 xargs 默认），进程数从 N 降到「⌈N/每批上限⌉」；实测 12 个示例 ex10 给出量化对比。

15. **读文件的同时把结果重定向回同一文件，把文件清空** —— 现象：while read l; do ...; done < config.txt > config.txt 跑完 config.txt 变空。根因：shell 在循环开始前就**先打开重定向目标 > config.txt**，截断文件，然后 read 读到的已是空文件。正确做法：写到临时文件再 mv（原子替换）：> config.tmp; mv config.tmp config.txt；或用 sponge（moreutils）。

16. **SSH 用密码登录 + 私钥文件权限过宽** —— 现象：密钥登录被拒 UNPROTECTED PRIVATE KEY FILE；或图省事用密码登录遭中间人/暴力。根因：SSH 要求私钥文件权限**必须 ≤ 600**，否则认为可能被他人读取而拒绝加载；密码登录则无法防御中间人且易暴力。正确做法：用 ssh-keygen 生成密钥对，chmod 600 ~/.ssh/id_rsa，公钥追加到目标 ~/.ssh/authorized_keys（600），服务端配置 PasswordAuthentication no；known_hosts 校验防中间人。
