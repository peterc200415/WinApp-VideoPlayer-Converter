# 解決 GitHub 中文亂碼問題

## 問題說明

在 Windows PowerShell 中使用 Git 提交中文訊息時，可能會出現編碼問題，導致 GitHub 上顯示亂碼。

## 根本原因

1. **PowerShell 預設編碼**: Windows PowerShell 預設使用系統編碼（通常是 Big5 或 GBK），而不是 UTF-8
2. **Git 提交編碼**: 如果提交時使用的編碼不正確，提交訊息會被損壞
3. **終端顯示**: 即使 Git 正確儲存了 UTF-8，PowerShell 也可能無法正確顯示

## 已完成的配置

已設置以下 Git 配置：

```bash
git config --global core.quotepath false
git config --global i18n.commitencoding utf-8
git config --global i18n.logoutputencoding utf-8
git config --local core.quotepath false
git config --local i18n.commitencoding utf-8
git config --local i18n.logoutputencoding utf-8
```

## 解決方案

### 方法 1: 使用 Git Bash（推薦）

Git Bash 預設使用 UTF-8 編碼，可以正確處理中文：

```bash
# 在 Git Bash 中執行
git commit -m "初始提交: 專案重構完成"
```

### 方法 2: 設置 PowerShell 編碼

在 PowerShell 中執行以下命令：

```powershell
# 設置控制台編碼為 UTF-8
chcp 65001
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 設置環境變數
$env:LANG = 'en_US.UTF-8'
$env:LC_ALL = 'en_US.UTF-8'

# 然後執行 Git 命令
git commit -m "初始提交: 專案重構完成"
```

### 方法 3: 使用檔案作為提交訊息

創建一個 UTF-8 編碼的文字檔案：

```powershell
# 創建提交訊息檔案（使用 UTF-8 編碼）
"初始提交: 專案重構完成" | Out-File -Encoding UTF8 commit_msg.txt

# 使用檔案作為提交訊息
git commit -F commit_msg.txt
```

### 方法 4: 修正已損壞的提交

如果提交已經損壞，可以使用以下方法修正：

```bash
# 使用 git rebase 重寫提交歷史
git rebase -i HEAD~n  # n 是要修正的提交數量

# 在編輯器中將 'pick' 改為 'reword'，然後保存
# Git 會提示您輸入新的提交訊息（使用正確的 UTF-8 編碼）

# 或者使用 git commit --amend
git commit --amend -m "新的提交訊息"
```

## 驗證編碼

### 檢查 Git 配置

```bash
git config --list | findstr encoding
```

應該看到：
```
i18n.commitencoding=utf-8
i18n.logoutputencoding=utf-8
```

### 檢查提交訊息編碼

```bash
# 查看提交訊息的原始內容
git show HEAD --format="%B" --no-patch | Format-Hex

# 如果顯示正確的 UTF-8 字節（如 E4 B8 AD 代表"中"），則編碼正確
```

## 注意事項

1. **GitHub 顯示**: GitHub 網頁端會自動使用 UTF-8 編碼顯示，如果提交時使用了正確的 UTF-8 編碼，GitHub 上應該能正常顯示。

2. **終端顯示**: PowerShell 終端可能無法正確顯示 UTF-8 編碼的中文，但這不影響 Git 的實際儲存。可以在 GitHub 網頁上驗證。

3. **強制推送**: 修正提交歷史後，需要使用 `git push -f` 強制推送，這會覆蓋遠程倉庫的歷史。

4. **備份**: 在重寫提交歷史前，建議先備份倉庫或創建分支。

## 推薦工作流程

1. **使用 Git Bash**: 對於包含中文的提交，建議使用 Git Bash 而不是 PowerShell
2. **設置 PowerShell 配置**: 如果必須使用 PowerShell，將編碼設置添加到 PowerShell 配置檔
3. **驗證**: 每次提交後，在 GitHub 網頁上驗證中文是否正確顯示

## 參考資料

- [Git 官方文件 - 編碼配置](https://git-scm.com/book/zh-tw/v2/Customizing-Git-Git-Configuration)
- [PowerShell 編碼設置](https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_character_encoding)
