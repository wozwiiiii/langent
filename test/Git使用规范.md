# Git 使用规范（SOP 标准操作流程）

> 本文档是 Git 完整使用手册的"操作规范版本"，目标是形成**可复用的标准流程**。
> 每次开发新功能、修复 bug、维护项目时，按本规范执行即可。

---

## 一、规范目标

| 目标 | 衡量标准 |
|------|---------|
| 代码历史清晰可追溯 | 每个 commit 只做一件事，消息规范 |
| 主分支永远可运行 | main 不接收未测试的代码 |
| 开发过程可回滚 | 任意中间状态可恢复 |
| 协作无歧义 | 分支命名、commit 格式、合并流程统一 |

---

## 二、四大核心原则

### 原则 1：Main 永远神圣不可侵犯

- main 分支**只能接受经过验证的代码**
- 任何修改**先在 feature 分支进行**
- main 上的 commit **只能是 merge commit 或修复 commit**

### 原则 2：Commit 原子化

- **一个 commit 只做一件事**
- 改一个 bug = 一个 commit
- 加一个功能 = 一个 commit（或一组连贯的 commit）
- 严禁出现"杂货铺 commit"：一个 commit 里又有 bug 修复又有 UI 调整

### 原则 3：及时推送

- 当天的工作**当天 push 到远程**
- 防止本地数据丢失（电脑坏了、误删 .git 目录等）
- 便于多设备同步

### 原则 4：定期同步 main

- 每次准备 push 前**先拉 main 同步**
- 避免本地和远程 main 差距过大
- 减少最终合并的冲突

---

## 三、分支管理规范

### 3.1 分支类型与命名

| 类型 | 命名格式 | 用途 | 生命周期 |
|------|---------|------|---------|
| 主分支 | `main` | 稳定可运行版本 | 永久 |
| 功能分支 | `feature/<scope>-<name>` | 开发新功能 | 合并后删除 |
| 修复分支 | `fix/<scope>-<name>` | 修复 bug | 合并后删除 |
| 重构分支 | `refactor/<scope>-<name>` | 重构代码 | 合并后删除 |
| 文档分支 | `docs/<scope>-<name>` | 文档更新 | 合并后删除 |
| 实验分支 | `experiment/<name>` | 探索性代码 | 完成后删除或归档 |

**scope 示例**：
- 模块名：`auth`、`api`、`ui`、`db`
- 功能名：`login`、`export-pdf`、`optimize-node`

**name 规范**：
- ✅ 推荐：`feature/api-add-pdf-export`、`fix/ui-typo-button`
- ❌ 不推荐：`feature/test`、`feature/xxx`、`feature/最终版`

### 3.2 分支生命周期示例

```
main:           A---B---E---H
                   \       \
feature/login:    C---D     \
                           \
fix/typo:                   F---G
                                 \
                                  ↓ 合并后删除
main:           A---B---E---H---I (merge commit)
```

### 3.3 分支保护规则

在 GitHub 仓库 Settings → Branches → Add rule 配置：
- ✅ Branch name pattern: `main`
- ✅ Require a pull request before merging
- ✅ Do not allow force pushes
- ✅ Do not allow deletions

---

## 四、Commit 规范

### 4.1 格式

```
<type>(<scope>): <subject>             ← 必填，首行 ≤ 50 字

<body>                                 ← 可选，解释 why
                                       72 字符换行
<footer>                               ← 可选，关联 issue
```

### 4.2 Type 类型

| Type | 含义 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(api): 添加 PDF 导出接口` |
| `fix` | Bug 修复 | `fix(ui): 修复按钮点击无响应` |
| `docs` | 文档 | `docs: 更新 README 安装步骤` |
| `style` | 格式调整 | `style: 统一缩进为 4 空格` |
| `refactor` | 重构 | `refactor(db): 优化查询性能` |
| `test` | 测试 | `test: 添加登录模块单元测试` |
| `chore` | 杂项 | `chore: 升级依赖到 v2.0` |
| `perf` | 性能 | `perf: 缓存优化提速 30%` |

### 4.3 规范对照表

| 场景 | 错误 | 正确 |
|------|------|------|
| 加新功能 | `update code` | `feat(api): 添加用户注册接口` |
| 修 bug | `fix bug` | `fix(ui): 修复登录按钮无响应` |
| 改格式 | `format` | `style: 统一代码缩进` |
| 升级依赖 | `pip install` | `chore: 升级 requests 到 2.31.0` |
| 写测试 | `test` | `test(auth): 添加登录模块单元测试` |
| 改文档 | `readme` | `docs: 更新安装说明` |

### 4.4 拆分 Commit 的实战示范

**反例**（一个 commit 做了 3 件事）：
```
feat: 添加了 PDF 导出功能，顺便修了一个 bug，改了 README
```

**正例**（拆成 3 个 commit）：
```
feat(export): 实现 PDF 导出核心逻辑
fix(ui): 修复导出按钮在 Chrome 下不显示
docs: 更新 README 添加导出功能说明
```

---

## 五、完整工作流 SOP

### SOP-1：项目初始化（仅首次）

```bash
# 1. 在 GitHub 创建仓库（不勾选 Initialize with README）
# 2. 本地初始化
cd 项目目录
git init
git add .
git commit -m "feat: 初始化项目"
git branch -M main
git remote add origin <仓库地址>
git push -u origin main

# 3. 配置 Git（全局，一次性）
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
```

### SOP-2：日常开发循环（每次写新功能）

```bash
# ===== 阶段 1：开工准备 =====
# 1. 确认当前状态干净
git status

# 2. 切到 main 并拉取最新
git checkout main
git pull origin main

# 3. 创建功能分支
git checkout -b feature/<scope>-<功能名>
# 推送到远程（可选，建议推，便于备份）
git push -u origin feature/<scope>-<功能名>


# ===== 阶段 2：开发中 =====
# 4. 写代码...

# 5. 阶段性提交（一个逻辑单元完成就提交）
git add <文件>
git commit -m "feat(<scope>): <具体做了什么>"

# 6. 每天工作结束前推送
git push origin feature/<scope>-<功能名>


# ===== 阶段 3：完成开发 =====
# 7. 准备合并前再同步 main
git checkout main
git pull origin main
git checkout feature/<scope>-<功能名>
git merge main
# 解决冲突（如有）

# 8. 推送最终版本
git push origin feature/<scope>-<功能名>


# ===== 阶段 4：合并到 main =====
# 9A. 走 PR 流程（推荐）
# 浏览器：GitHub → 提 PR → review → merge

# 9B. 本地直接 merge
git checkout main
git merge --no-ff feature/<scope>-<功能名> -m "merge: <功能名>"
git push origin main


# ===== 阶段 5：清理 =====
# 10. 删除已合并的 feature 分支
git branch -d feature/<scope>-<功能名>
git push origin --delete feature/<scope>-<功能名>
```

### SOP-3：紧急 Bug 修复

```bash
# 1. 立即创建 hotfix 分支
git checkout main
git pull origin main
git checkout -b fix/<紧急问题描述>

# 2. 修复 + 提交
# 改代码
git add .
git commit -m "fix: <具体修复内容>"

# 3. 立即合并到 main
git checkout main
git merge --no-ff fix/<紧急问题描述> -m "hotfix: <紧急问题>"
git push origin main

# 4. 同时合并到正在开发的 feature 分支（如有）
git checkout feature/xxx
git merge fix/<紧急问题描述>
git push origin feature/xxx

# 5. 清理
git branch -d fix/<紧急问题描述>
```

### SOP-4：撤销错误操作

```bash
# 撤销工作区修改
git checkout -- <文件名>

# 撤销已 add 但未 commit
git restore --staged <文件名>

# 撤销最后一次 commit（保留修改）
git reset --soft HEAD~1

# 撤销最后一次 commit（丢弃修改）⚠️ 危险
git reset --hard HEAD~1

# 撤销已 push 的 commit（生成反向 commit）
git revert HEAD
git push origin main

# 放弃整个分支，强制回到 main
git checkout main
git branch -D feature/失败分支
```

---

## 六、每日检查清单

### 开工检查

- [ ] `git status` 工作区干净
- [ ] 已在正确的 feature 分支上
- [ ] 开工前已 `git pull` 同步 main

### 提交检查

- [ ] 一个 commit 只做一件事
- [ ] commit 消息符合 Conventional Commits
- [ ] 没有遗留的调试代码（print、console.log）
- [ ] 没有提交大文件（> 5MB 的文件单独讨论）

### 收工检查

- [ ] 当天工作已 commit
- [ ] 当天工作已 push 到远程
- [ ] 没有未完成的"半成品"留在工作区

### 每周检查

- [ ] main 分支保持稳定
- [ ] 已合并的 feature 分支已删除
- [ ] 远程没有"孤儿"分支
- [ ] Issue / TODO 有更新

---

## 七、特殊情况处理 SOP

### 7.1 不小心把敏感信息 commit 了

```bash
# 1. 立即撤销该 commit
git reset --hard HEAD~1

# 2. 修改文件，移除敏感信息
# 3. 重新 commit
# 4. ⚠️ 如果已经 push：
#    - 必须修改密码/密钥
#    - 用 git filter-branch 或 BFG 清理历史
#    - 或直接作废这个仓库，新建一个
```

### 7.2 commit 写错了消息

```bash
# 修改最后一次 commit
git commit --amend -m "新消息"

# 修改历史某次 commit（会改写 hash）
git rebase -i HEAD~3
# 把要改的那行从 pick 改为 reword
```

### 7.3 推送被拒绝

```bash
# 错误：rejected - non-fast-forward
# 原因：远程有新的 commit

# 解决：先拉取再推送
git pull --rebase origin main
git push origin main
```

### 7.4 合并后想撤销

```bash
# 撤销最近一次 merge（保留修改在工作区）
git reset --soft HEAD~1

# 撤销并丢弃修改
git reset --hard HEAD~1

# 生成反向 commit（更安全，推荐）
git revert -m 1 <merge-commit-hash>
```

---

## 八、违规行为与后果

| 违规行为 | 后果（个人版 = 影响） |
|---------|---------------------|
| 在 main 上直接 commit | main 可能被破坏，影响所有协作者 |
| 一个 commit 改 3 件事 | 历史不可读，回滚困难 |
| commit 消息写"update"、"fix" | 自己都看不懂，未来无法追溯 |
| 不 push 累积一周 | 中途电脑坏 = 一周工作全丢 |
| 长期不删 feature 分支 | 分支爆炸，main 历史噪音 |

---

## 九、配置模板（一次配置永久生效）

### 9.1 Git 全局配置

```bash
# 身份
git config --global user.name "你的名字"
git config --global user.email "你的邮箱@example.com"

# 行为
git config --global init.defaultBranch main
git config --global core.quotepath false
git config --global core.autocrlf true
git config --global pull.rebase true

# 别名
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.lg "log --oneline --graph --decorate -20"
```

### 9.2 .gitignore 模板（Python 项目）

```gitignore
# Python
__pycache__/
*.py[cod]
*.so
*.egg-info/
.venv/
venv/
.pytest_cache/
.mypy_cache/

# IDE
.vscode/
.idea/
*.swp

# 数据
*.db
*.faiss
*.pkl
.env
.env.local

# 临时文件
*.log
*.tmp
.DS_Store
Thumbs.db
```

---

## 十、规范速记卡（贴墙上看）

```
┌──────────────────────────────────────────────┐
│           Git 使用规范（速记卡）              │
│                                              │
│  1. 任何修改先建分支                          │
│  2. 一个 commit 只做一件事                    │
│  3. 消息格式：type(scope): subject           │
│  4. 当天工作当天 push                         │
│  5. 合并前先同步 main                         │
│  6. 合并后删除 feature 分支                   │
│  7. main 永远只接受 merge commit              │
│                                              │
│  必背命令：                                  │
│  git status       看状态                      │
│  git add .        暂存                        │
│  git commit -m "" 提交                        │
│  git push         推送                        │
│  git checkout -b  建分支                      │
│  git merge        合并                        │
└──────────────────────────────────────────────┘
```

---

**文档版本**：v1.0
**适用场景**：个人 / 团队（2-5 人）
**与完整手册关系**：本文档是手册的"操作规范"版，强调 SOP 流程
**最后更新**：基于实际项目操作经验整理
