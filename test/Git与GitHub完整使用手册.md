# Git 与 GitHub 完整使用手册

> 本文档基于实际项目操作经验整理，目标是让一个完全没接触过 Git 的人，能在 30 分钟内独立完成日常开发、推送、协作的全部流程。

---

## 一、Git 是什么？为什么非学不可

### 1.1 真实场景对比

**没有 Git 的开发流程**（你可能正在经历的）：

```
D:\AI_Program\langent\
├── 03_循环工作流——人机交互式文本优化.py          # 最初的版本
├── 03_循环工作流——人机交互式文本优化_备份.py     # 改坏了，复制一份
├── 03_循环工作流——人机交互式文本优化_新功能.py   # 加了新功能
├── 03_循环工作流——人机交互式文本优化_最终版.py   # 又改了一版
├── 03_循环工作流——人机交互式文本优化_真的最终.py
├── 03_循环工作流——人机交互式文本优化_给老板看.py
```

**用 Git 的开发流程**：

```
D:\AI_Program\langent\
└── 03_循环工作流——人机交互式文本优化.py  # 只有一份文件
```

所有"旧版本"、"新功能"、"分支版本"都被 Git 记录在 `.git` 文件夹里，**不污染你的工作目录**。

### 1.2 Git 解决的具体问题

| 问题 | 没有 Git | 有 Git |
|------|---------|--------|
| 改坏代码想恢复 | 手动找备份 | `git checkout` 30 秒恢复 |
| 同时开发多个功能 | 复制一堆文件 | 用分支并行 |
| 多人协作 | U 盘互传 | `push` / `pull` 自动同步 |
| 半年后想看"当时为什么这么写" | 记忆消失 | `git log` 查看完整历史 |
| 想给老板演示旧版本 | 文件丢了 | `git checkout` 切回任意版本 |

---

## 二、三个核心概念（必须搞懂）

### 2.1 工作区 / 暂存区 / 版本库（三区）

```
┌─────────────────┐    git add .    ┌─────────────────┐    git commit    ┌─────────────────┐
│   工作区          │  ──────────►  │   暂存区          │  ──────────────► │   版本库          │
│  (你看到的文件)    │                │  (准备提交的)     │                  │  (永久保存)       │
│  *.py            │                │  *.py            │                  │  commit 记录     │
└─────────────────┘                └─────────────────┘                  └─────────────────┘
                                                                              ▲
                                                                              │ git push
                                                                              │
                                                                        ┌─────────────────┐
                                                                        │  远程仓库         │
                                                                        │  (GitHub)        │
                                                                        └─────────────────┘
```

**为什么要分三个区？** 因为有时候你改了好几个文件，但只想提交其中一部分。这时候可以**选择性** `git add` 想要的，**忽略**不想要的。

### 2.2 Commit（提交）

一次 commit 是一份"代码快照"，包含：
- 改动了哪些文件
- 改动的内容
- 改动时间
- 改动人
- 一条描述信息

**commit 的本质是"做一件事，做完拍张照"**。一次 commit 只解决一个问题。

```
❌ 错误示范：一次 commit 包含 3 个不相关的修改
feat: 修复登录 bug + 改 UI 颜色 + 升级依赖

✅ 正确示范：拆成 3 次 commit
fix: 修复登录接口的 500 错误
style: 调整主按钮颜色为品牌色
chore: 升级 requests 到 2.31.0
```

### 2.3 Branch（分支）

**分支就是"指向某个 commit 的可移动指针"**。

```
main:           A---B---C---D
                       \
feature/login:         E---F
                       ↑
                  你现在在这里开发
```

**分支存在的意义**：
- 让你**独立开发新功能**，不干扰主分支
- 万一新功能搞砸了，**删除这个分支**就行，main 不受影响
- 多人协作时，**每个人有自己的分支**，互不冲突

---

## 三、Feature 分支的真正意义（重点）

### 3.1 一个反例：直接在 main 上改

```bash
# 你正在 main 分支上
# 你开始写新功能，写了 2 小时，写了一半
# 这时候产品经理说："main 上有紧急 bug 立刻修"
# 你的状态：
#   - main 上有未完成的新功能代码
#   - 紧急 bug 没法修（因为一改就和新功能混在一起）
#   - 提交了会把半成品代码污染 main
#   - 不提交切走的话，工作又丢了一半
```

**这就是没有分支的灾难。**

### 3.2 用 feature 分支的优雅流程

```bash
# 你正在 main 分支上，发现 main 有紧急 bug
git checkout main
git checkout -b fix/urgent-bug
# 修 bug，提交
git commit -m "fix: 修复紧急 bug"
git checkout main
git merge fix/urgent-bug

# 现在 main 是干净的
# 切回你的新功能分支继续开发
git checkout feature/new-function
```

**分支保护机制的核心思想**：
- main 是"金本位"，任何时候都要能跑
- 所有开发都在 feature 分支进行
- 测试通过后，再合到 main

### 3.3 Feature 分支的 5 大价值

| 价值 | 具体体现 |
|------|---------|
| **隔离** | 一个分支 = 一个功能，互不干扰 |
| **可丢弃** | 写崩了就 `git branch -D`，无心理负担 |
| **可并行** | 多个功能同时开发，每个一个分支 |
| **可 review** | 提 PR 后同事/未来的你能逐行 review |
| **可追溯** | 分支名 + commit 消息 = 完整的故事线 |

### 3.4 命名规范

```
feature/xxx    新功能
fix/xxx        bug 修复
docs/xxx       文档
refactor/xxx   重构
test/xxx       测试
chore/xxx      构建/工具
```

**好名字**：`feature/add-pdf-export`、`fix/typo-in-optimize-node`
**坏名字**：`test`、`new`、`abc`、`最终版`

---

## 四、Git 安装与配置（5 分钟搞定）

### 4.1 Windows 安装

1. 访问 https://git-scm.com/download/win
2. 下载 64-bit Git for Windows Setup
3. 安装时全部默认选项即可
4. 验证安装：
   ```bash
   git --version
   # 输出：git version 2.43.0
   ```

### 4.2 必做配置（配置一次永久生效）

```bash
# 设置用户名（commit 时会显示）
git config --global user.name "你的名字"

# 设置邮箱（commit 时会显示）
git config --global user.email "你的邮箱@qq.com"

# 设置默认分支名为 main
git config --global init.defaultBranch main

# 设置中文编码（避免乱码）
git config --global core.quotepath false

# 设置换行符（Windows 用户必做，避免跨平台冲突）
git config --global core.autocrlf true
```

### 4.3 验证配置

```bash
git config --list
```

能看到刚才设置的 5 个配置项就说明成功。

---

## 五、创建项目的两种方式

### 方式 A：GitHub 上先创建，本地 clone（推荐用于正式项目）

```bash
# 1. 浏览器打开 GitHub，点 New repository
# 2. 填写仓库名、描述，勾不勾选 README 都可以
# 3. 复制仓库地址（HTTPS 或 SSH）

# 4. 本地克隆
git clone https://github.com/你的用户名/你的仓库名.git
cd 你的仓库名

# 5. 创建工作分支
git checkout -b feature/first-feature

# 6. 开始写代码
```

**适用场景**：正式项目、需要 GitHub Issues/Projects 管理、长期维护。

### 方式 B：本地已有项目，推送到 GitHub

```bash
# 1. 进入项目目录
cd d:\AI_Program\langent\langgraph基础\07_综合实操

# 2. 初始化 Git
git init

# 3. 添加所有文件
git add .

# 4. 第一次提交
git commit -m "feat: 初始化项目"

# 5. 关联远程仓库（先在 GitHub 上创建空仓库，不勾选 README）
git remote add origin https://github.com/你的用户名/你的仓库名.git

# 6. 推送
git branch -M main
git push -u origin main
```

**适用场景**：本地已有的代码、想和原作者项目区分开。

### 方式 C：从原作者下载 ZIP 后再推送（你之前的场景）

```bash
# 1. 在 GitHub 上点原作者的 Fork 按钮
# 2. 然后用方式 A clone 你自己的 fork
git clone https://github.com/你的用户名/原项目名.git
cd 原项目名

# 3. 添加原作者仓库为 upstream
git remote add upstream https://github.com/原作者/原项目名.git

# 4. 拉取原作者完整历史（关键！解决 ZIP 没有 git 历史的问题）
git fetch upstream
git reset --hard upstream/main

# 5. 创建新分支做修改
git checkout -b feature/my-improvements

# 6. 在这个分支上修改、提交、push
```

---

## 六、常用命令速查（覆盖 90% 场景）

### 6.1 查看类

| 命令 | 作用 | 使用频率 |
|------|------|---------|
| `git status` | 看工作区/暂存区状态 | ⭐⭐⭐⭐⭐ 每天 |
| `git log --oneline -10` | 看最近 10 条 commit | ⭐⭐⭐⭐ |
| `git log --oneline --graph` | 图形化看分支历史 | ⭐⭐⭐ |
| `git diff` | 看未暂存的修改 | ⭐⭐⭐ |
| `git diff --staged` | 看已暂存的修改 | ⭐⭐ |
| `git branch` | 看所有本地分支 | ⭐⭐⭐⭐ |
| `git branch -a` | 看所有分支（含远程） | ⭐⭐⭐ |
| `git remote -v` | 看远程仓库地址 | ⭐⭐ |

### 6.2 提交类

| 命令 | 作用 |
|------|------|
| `git add 文件名` | 暂存某个文件 |
| `git add .` | 暂存所有修改 |
| `git add -p` | 交互式暂存（按块选择） |
| `git commit -m "msg"` | 提交并写消息 |
| `git commit --amend` | 修改最后一次 commit |
| `git commit -am "msg"` | add + commit 合一（仅对已跟踪文件） |

### 6.3 分支类

| 命令 | 作用 |
|------|------|
| `git branch xxx` | 创建分支（不切换） |
| `git checkout xxx` | 切换到分支 |
| `git checkout -b xxx` | 创建并切换（最常用） |
| `git branch -d xxx` | 删除已合并的分支 |
| `git branch -D xxx` | 强制删除分支 |
| `git branch -m old new` | 重命名分支 |

### 6.4 同步类

| 命令 | 作用 |
|------|------|
| `git fetch origin` | 拉取远程信息（不自动合并） |
| `git pull origin main` | 拉取并自动合并 |
| `git pull --rebase origin main` | 拉取并变基（更干净） |
| `git push origin xxx` | 推送到远程 |
| `git push -u origin xxx` | 第一次推送（关联上游） |
| `git push --force-with-lease` | 强制推送（安全的 force） |

### 6.5 撤销类

| 命令 | 作用 | 危险度 |
|------|------|-------|
| `git checkout -- 文件名` | 丢弃工作区的修改 | ⚠️ 修改丢失 |
| `git restore --staged 文件名` | 取消暂存 | 安全 |
| `git reset --soft HEAD~1` | 撤销 commit，保留修改在暂存区 | 安全 |
| `git reset --mixed HEAD~1` | 撤销 commit，保留修改在工作区 | 安全 |
| `git reset --hard HEAD~1` | 撤销 commit + 丢弃修改 | ⚠️⚠️ 不可恢复 |
| `git revert HEAD` | 生成新 commit 反向撤销 | 安全（不丢历史） |

---

## 七、完整日常工作流（每天 80% 的操作）

### 7.1 开工前

```bash
# 1. 看当前在哪个分支
git branch

# 2. 切到 main 并拉取最新
git checkout main
git pull origin main

# 3. 切回自己的功能分支
git checkout feature/my-work

# 4. 把 main 的最新代码合并进来
git merge main
# 或者：git rebase main（历史更干净）
```

### 7.2 写代码 & 提交

```bash
# 1. 修改文件...

# 2. 查看改了什么
git status
git diff

# 3. 暂存
git add .

# 4. 提交
git commit -m "feat: 添加某某功能"
```

### 7.3 推送

```bash
# 1. 准备 push 前再同步一次 main
git fetch origin
git merge origin/main

# 2. 推送
git push origin feature/my-work
```

### 7.4 合并到 main（开发完成）

**方式 A：本地合并**
```bash
git checkout main
git pull origin main
git merge --no-ff feature/my-work -m "merge: 完成某某功能"
git push origin main
git branch -d feature/my-work
```

**方式 B：GitHub PR（更规范）**
```bash
# 1. 推送后去 GitHub 网站
# 2. 点 "Compare & pull request"
# 3. 填写 PR 标题、说明
# 4. 创建 PR
# 5. 页面 review → 点 "Merge pull request"
# 6. 本地清理：
git checkout main
git pull origin main
git branch -d feature/my-work
```

---

## 八、与原作者项目协作：Fork + PR 流程

### 8.1 为什么要 Fork

直接 clone 原作者项目 → 你没有 push 权限 → 没法贡献回去。

**Fork 的作用**：在你自己账号下创建一份**完整副本**，你有完全控制权。

### 8.2 完整流程

```
原作者仓库 (upstream) ──你点 Fork──→ 你的 fork (origin)
        ↑                                    ↓
        │                              git clone origin
        │                                    ↓
        │                              本地修改
        │                                    ↓
        │                              git push origin
        │                                    ↓
        │                              GitHub 上开 PR
        │                                    ↓
        ←────── 作者 review + merge ←────────┘
```

### 8.3 具体命令

```bash
# 1. 在 GitHub 上点 Fork

# 2. clone 你的 fork
git clone https://github.com/你的用户名/原项目名.git
cd 原项目名

# 3. 添加原作者仓库为 upstream
git remote add upstream https://github.com/原作者/原项目名.git

# 4. 验证
git remote -v
# origin    https://github.com/你的用户名/原项目名.git
# upstream  https://github.com/原作者/原项目名.git

# 5. 创建工作分支
git checkout -b feature/my-improvement

# 6. 修改、提交、推送
git add .
git commit -m "feat: 改进某某功能"
git push origin feature/my-improvement

# 7. 去 GitHub 网站开 PR
# base: 原作者/原项目名 main
# compare: 你的用户名/原项目名 feature/my-improvement
```

---

## 九、Commit 规范（Conventional Commits）

### 9.1 为什么需要规范

**不规范**：
```
fix bug
改了一下
更新
完成了
```

**规范**：
```
feat: 修复了人机协作中无法中断的 bug
fix: 修复了 PDF 导出的中文乱码
docs: 更新 README 安装步骤
```

规范的好处：
- 工具能自动生成 CHANGELOG
- 一眼看出这次改动属于什么类型
- 团队协作无歧义

### 9.2 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 9.3 常用 type

| type | 含义 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 添加 PDF 导出功能` |
| `fix` | 修复 bug | `fix: 修复优化节点崩溃问题` |
| `docs` | 文档 | `docs: 更新 README` |
| `style` | 格式 | `style: 格式化代码` |
|
| `refactor` | 重构 | `refactor: 重构状态机逻辑` |
| `test` | 测试 | `test: 添加单元测试` |
| `chore` | 构建/工具 | `chore: 更新依赖` |
| `perf` | 性能 | `perf: 优化检索速度 30%` |

### 9.4 好的 commit 原则

1. **单一职责**：一个 commit 只做一件事
2. **消息首行 ≤ 50 字**：能在终端一行看完
3. **首行用祈使句**："fix" 而非 "fixed"
4. **body 解释 why**：不是改了什么，而是为什么改
5. **避免空泛**：不要写 "update" 这种无意义消息

---

## 十、常见错误与解决

### 10.1 `RPC failed; curl 28 Recv failure: Connection was reset`

**原因**：网络连接被中断（国内访问 GitHub 常见）

**解决**：
```bash
# 方案 1：重试
git pull origin main

# 方案 2：换 SSH 协议（推荐）
git remote set-url origin git@github.com:你的用户名/你的仓库.git
ssh -T git@github.com  # 验证 SSH 是否通

# 方案 3：增大缓冲区
git config --global http.postBuffer 524288000
```

### 10.2 `src refspec xxx does not match any`

**原因**：本地没有叫 xxx 的分支

**解决**：
```bash
# 1. 看当前分支真实名字
git branch --show-current

# 2. 用真实名字重新 push
git push -u origin <真实名字>
```

### 10.3 `no branch named 'xxx'`

**原因**：想改名的源分支不存在（可能已经改过了）

**解决**：
```bash
# 查看所有分支
git branch -a

# 用真实存在的名字
```

### 10.4 `invalid branch name`

**原因**：分支名里有非法字符（空格、特殊符号）

**解决**：
```bash
# 用英文引号包住整个名字
git branch -m "old name with space" "new-name-no-space"
```

### 10.5 `merge conflict`（合并冲突）

**原因**：两个分支改了同一个文件的同一行

**解决步骤**：
```bash
# 1. 打开冲突文件，搜索 <<<<<<< 标记
# 2. 手动选择要保留的代码，删除冲突标记
# 3. 标记为已解决
git add 文件名
# 4. 完成合并
git commit -m "merge: 解决合并冲突"
```

### 10.6 `rejected non-fast-forward`

**原因**：远程有新的 commit，本地落后

**解决**：
```bash
# 先拉取再推送
git pull --rebase origin 分支名
git push origin 分支名
```

---

## 十一、长期养成的习惯

### 11.1 每日开工清单

```bash
# 1. 看当前状态
git status

# 2. 切到 main 拉最新
git checkout main
git pull origin main

# 3. 切回工作分支同步 main
git checkout feature/my-work
git merge main

# 4. 开始干活
```

### 11.2 Commit 前自检

- [ ] 这个 commit 是单一目的吗？
- [ ] 消息能说清楚"做了什么"和"为什么"吗？
- [ ] 同事/未来的我能看懂吗？
- [ ] 不相关的改动是否拆分成多个 commit？

### 11.3 命名规范清单

| 类型 | 规范 | 例子 |
|------|------|------|
| 分支名 | 短横线或下划线分隔 | `feature/add-pdf-export` |
| commit | Conventional Commits | `feat: 添加 PDF 导出` |
| 标签（版本） | 语义化版本 | `v1.2.0` |
| 文件 | 不要带空格和特殊符号 | `03_循环工作流.py` ✅ |

### 11.4 Git 别名（省时省力）

```bash
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.lg "log --oneline --graph --decorate -20"
```

之后可以：
```bash
git st       # 等价于 git status
git co main  # 等价于 git checkout main
git lg       # 美化的 log
```

---

## 十二、推荐学习资源

1. [Git 官方文档（中文）](https://git-scm.com/book/zh/v2) —— 最权威
2. [Learn Git Branching](https://learngitbranching.js.org/?locale=zh_CN) —— 交互式学习分支
3. [Conventional Commits](https://www.conventionalcommits.org/zh-hans/) —— commit 规范标准
4. [VS Code Git 文档](https://code.visualstudio.com/docs/sourcecontrol/overview) —— GUI 操作

---

## 附录：常用场景速查

| 场景 | 命令 |
|------|------|
| 撤销最后一次 commit（保留修改） | `git reset --soft HEAD~1` |
| 撤销最后一次 commit（不保留修改） | `git reset --hard HEAD~1` |
| 修改最后一次 commit 的消息 | `git commit --amend -m "新消息"` |
| 看某行代码是谁写的 | `git blame 文件名` |
| 临时保存当前工作 | `git stash` / `git stash pop` |
| 从某次 commit 拉取修改 | `git cherry-pick <commit-id>` |
| 强制推送（覆盖远程） | `git push --force-with-lease origin xxx` |
| 看远程仓库地址 | `git remote -v` |
| 切换远程协议 HTTPS→SSH | `git remote set-url origin git@github.com:...` |
| 全局配置代理 | `git config --global https.proxy http://127.0.0.1:7890` |

---

**文档版本**：v1.0
**适用人群**：从零开始学 Git 的开发者
**最后更新**：基于实际项目操作经验整理
