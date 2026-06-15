# Git 大文件清理脚本
# 用于解决 Git 仓库超过 100MB 限制的问题

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Git 大文件清理工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查是否已安装 Git LFS
$hasGitLFS = git lfs version 2>$null

if ($hasGitLFS) {
    Write-Host "[✓] 检测到 Git LFS 已安装" -ForegroundColor Green
} else {
    Write-Host "[!] Git LFS 未安装，是否安装？(推荐)" -ForegroundColor Yellow
    Write-Host "    安装命令: git lfs install" -ForegroundColor Gray
    Write-Host ""
}

# 列出当前跟踪的大文件
Write-Host "`n[1] 当前被跟踪的大文件:" -ForegroundColor Yellow
Write-Host "----------------------------------------"
git ls-files | Where-Object {
    $_ -match '\.(faiss|pt|onnx|pth|bin|safetensors|h5|ckpt|faiss|index\.faiss)$'
} | ForEach-Object {
    $size = (Get-Item $_).Length / 1MB
    Write-Host "  $($size.ToString('F2')) MB - $_" -ForegroundColor $(if ($size -gt 100) { "Red" } else { "White" })
}

Write-Host ""

# 计算仓库总大小
$totalSize = 0
git ls-files | Where-Object {
    $_ -match '\.(faiss|pt|onnx|pth|bin|safetensors|h5|ckpt|faiss|index\.faiss)$'
} | ForEach-Object {
    $totalSize += (Get-Item $_).Length
}
Write-Host "大文件总大小: $(($totalSize / 1MB).ToString('F2')) MB" -ForegroundColor Red

Write-Host ""
Write-Host "[2] 清理选项:" -ForegroundColor Yellow
Write-Host "----------------------------------------"
Write-Host "  A) 使用 Git LFS 管理大文件 (推荐)"
Write-Host "     - 安装 Git LFS 并配置"
Write-Host "     - 将大文件迁移到 LFS"
Write-Host "     - 仓库仍保留版本控制功能"
Write-Host ""
Write-Host "  B) 直接移除大文件 (不推荐)"
Write-Host "     - 仅从 Git 移除，不删除本地文件"
Write-Host "     - 无法在仓库中版本控制大文件"
Write-Host ""

$choice = Read-Host "请选择 (A/B) 或按 Enter 退出"

switch ($choice.ToUpper()) {
    "A" {
        Write-Host "`n[开始 Git LFS 配置...]" -ForegroundColor Green

        # 初始化 Git LFS
        if (-not $hasGitLFS) {
            Write-Host "安装 Git LFS..."
            git lfs install
        }

        # 创建 .gitattributes 如果不存在
        $gitattributesPath = ".gitattributes"
        if (-not (Test-Path $gitattributesPath)) {
            New-Item -ItemType File -Path $gitattributesPath | Out-Null
        }

        # 添加大文件类型到 LFS
        @"
*.pt filter=lfs diff=lfs merge=lfs -crlf
*.onnx filter=lfs diff=lfs merge=lfs -crlf
*.pth filter=lfs diff=lfs merge=lfs -crlf
*.bin filter=lfs diff=lfs merge=lfs -crlf
*.safetensors filter=lfs diff=lfs merge=lfs -crlf
*.h5 filter=lfs diff=lfs merge=lfs -crlf
*.ckpt filter=lfs diff=lfs merge=lfs -crlf
*.faiss filter=lfs diff=lfs merge=lfs -crlf
*.index filter=lfs diff=lfs merge=lfs -crlf
*.pkl filter=lfs diff=lfs merge=lfs -crlf
*.wav filter=lfs diff=lfs merge=lfs -crlf
*.mp3 filter=lfs diff=lfs merge=lfs -crlf
*.ogg filter=lfs diff=lfs merge=lfs -crlf
*.m4a filter=lfs diff=lfs merge=lfs -crlf
voice_qa_api/models/ filter=lfs
AI\ CRM/storage/ filter=lfs
AI\ CRM/uploads/ filter=lfs
"@ | Add-Content -Path $gitattributesPath

        Write-Host "LFS 跟踪配置已添加到 .gitattributes" -ForegroundColor Green

        # 迁移现有文件到 LFS
        Write-Host "`n迁移现有大文件到 Git LFS..."
        git lfs migrate import --include="voice_qa_api/models/SenseVoiceSmall/,*.pt,*.onnx,*.faiss,*.pkl"

        Write-Host "`n[✓] Git LFS 配置完成!" -ForegroundColor Green
        Write-Host "`n请执行以下命令完成提交:" -ForegroundColor Yellow
        Write-Host "  git add .gitattributes" -ForegroundColor Cyan
        Write-Host "  git commit -m 'chore: 使用 Git LFS 管理大文件'" -ForegroundColor Cyan
        Write-Host "  git push origin main" -ForegroundColor Cyan
    }

    "B" {
        Write-Host "`n[开始清理大文件...]" -ForegroundColor Yellow

        # 从 Git 移除但不删除本地文件
        $filesToRemove = @(
            "voice_qa_api/models/SenseVoiceSmall/model.pt"
        )

        foreach ($file in $filesToRemove) {
            if (Test-Path $file) {
                Write-Host "移除: $file"
                git rm --cached $file
            }
        }

        Write-Host "`n[✓] 大文件已从 Git 移除 (本地文件保留)" -ForegroundColor Green
        Write-Host "`n请执行以下命令完成提交:" -ForegroundColor Yellow
        Write-Host "  git add -A" -ForegroundColor Cyan
        Write-Host "  git commit -m 'chore: 移除大文件，节省仓库空间'" -ForegroundColor Cyan
        Write-Host "  git push origin main" -ForegroundColor Cyan
    }

    default {
        Write-Host "`n操作已取消" -ForegroundColor Red
    }
}

Write-Host "`n按任意键退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
