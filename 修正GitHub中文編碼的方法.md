# 修正 GitHub 中文編碼的方法

## 問題

提交訊息中的中文在 GitHub 上顯示為亂碼（如 `docs: ???? Git ????????`）。

## 根本原因

提交時使用的編碼不正確，導致中文字符被損壞（在 Git 對象中儲存為 `?` 字符，即 `3F`）。

## 解決方法

### 使用 `git commit-tree` 重寫提交

當提交訊息已經損壞時，需要使用 `git commit-tree` 創建新的提交對象來替換損壞的提交：

```powershell
# 1. 設置環境變數（指定作者和日期）
$env:GIT_AUTHOR_NAME='peterc20'
$env:GIT_AUTHOR_EMAIL='peterc20@example.com'
$env:GIT_COMMITTER_NAME='peterc20'
$env:GIT_COMMITTER_EMAIL='peterc20@example.com'
$env:GIT_AUTHOR_DATE='2026-01-18T21:06:33+08:00'
$env:GIT_COMMITTER_DATE='2026-01-18T21:06:33+08:00'

# 2. 創建提交訊息檔案（使用 UTF-8 編碼）
"初始提交: 專案重構完成 - 模組化架構、硬體加速自動偵測、現代化UI" | Out-File -Encoding UTF8 commit_msg_utf8.txt

# 3. 獲取當前的 tree 對象
$tree = git write-tree

# 4. 使用 commit-tree 創建新的提交對象
$newCommit = git commit-tree $tree -F commit_msg_utf8.txt

# 5. 更新分支引用
git update-ref refs/heads/main $newCommit

# 6. 強制推送到 GitHub
git push -f origin main
```

### 驗證修正

```powershell
# 檢查提交訊息
git log --oneline -1
git show HEAD --format="%B" --no-patch

# 應該顯示正確的中文，而不是亂碼
```

## 預防措施

### 1. 使用 Git Bash（推薦）

Git Bash 預設使用 UTF-8 編碼，可以正確處理中文：

```bash
# 在 Git Bash 中執行
git commit -m "初始提交: 專案重構完成"
```

### 2. 設置 PowerShell 編碼

在 PowerShell 中執行提交前，設置編碼：

```powershell
# 設置控制台編碼
chcp 65001
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 設置環境變數
$env:LANG = 'en_US.UTF-8'
$env:LC_ALL = 'en_US.UTF-8'
```

### 3. 使用檔案作為提交訊息

創建 UTF-8 編碼的文字檔案：

```powershell
# 創建提交訊息檔案
"初始提交: 專案重構完成" | Out-File -Encoding UTF8 msg.txt

# 使用檔案作為提交訊息
git commit -F msg.txt
```

### 4. 設置 Git 配置

確保 Git 使用 UTF-8 編碼：

```bash
git config --global core.quotepath false
git config --global i18n.commitencoding utf-8
git config --global i18n.logoutputencoding utf-8
```

## 注意事項

1. **強制推送**: 使用 `git push -f` 會覆蓋遠程倉庫的歷史，請確保沒有其他人正在使用此倉庫。

2. **備份**: 在重寫提交歷史前，建議先備份倉庫或創建分支。

3. **驗證**: 修正後，在 GitHub 網頁上驗證中文是否正確顯示。

## 已修正的提交

- **提交 ID**: `9faca30`
- **原始提交**: `4bc5460` (損壞的提交)
- **修正後的訊息**: "初始提交: 專案重構完成 - 模組化架構、硬體加速自動偵測、現代化UI"

## 參考資料

- [Git commit-tree 文件](https://git-scm.com/docs/git-commit-tree)
- [Git 編碼配置](https://git-scm.com/book/zh-tw/v2/Customizing-Git-Git-Configuration)
