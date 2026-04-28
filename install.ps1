# =============================================================================
# Hermes Web Chat 一键安装脚本 (Windows PowerShell)
# =============================================================================
# 用法：irm https://raw.githubusercontent.com/guoyu767344855/hermes-web-chat/main/install.ps1 | iex
# 或：.\install.ps1
# =============================================================================

# 设置 UTF-8 编码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 颜色定义
function Write-Info { Write-Host "[INFO] $($args -join ' ')" -ForegroundColor Cyan }
function Write-Success { Write-Host "[✓] $($args -join ' ')" -ForegroundColor Green }
function Write-Warn { Write-Host "[!] $($args -join ' ')" -ForegroundColor Yellow }
function Write-Error { Write-Host "[✗] $($args -join ' ')" -ForegroundColor Red }

# 打印横幅
function Print-Banner {
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║        💬 Hermes Web Chat 安装程序 (Windows)       ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
}

# 检查 Python
function Check-Python {
    Write-Info "检查 Python 环境..."
    
    # 尝试查找 Python
    $pythonCmd = $null
    
    # 检查 py launcher
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $pythonCmd = "py"
    }
    # 检查 python
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonCmd = "python"
    }
    # 检查 python3
    elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
        $pythonCmd = "python3"
    }
    
    if (-not $pythonCmd) {
        Write-Error "未找到 Python，请先安装 Python 3.9+"
        Write-Host ""
        Write-Host "安装指南:"
        Write-Host "  1. 访问 https://www.python.org/downloads/"
        Write-Host "  2. 下载 Python 3.9+ (勾选 'Add Python to PATH')"
        Write-Host "  3. 重新打开 PowerShell 运行此脚本"
        exit 1
    }
    
    $pythonVersion = & $pythonCmd --version 2>&1
    Write-Success "Python 版本：$pythonVersion"
    
    # 检查版本 >= 3.9
    $versionInfo = & $pythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    $versionParts = $versionInfo.Split('.')
    $major = [int]$versionParts[0]
    $minor = [int]$versionParts[1]
    
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 9)) {
        Write-Error "Python 版本过低，需要 3.9+ (当前：$versionInfo)"
        exit 1
    }
    
    return $pythonCmd
}

# 检查 pip
function Check-Pip {
    Write-Info "检查 pip..."
    
    if (-not (& $pythonCmd -m pip --version 2>$null)) {
        Write-Error "未找到 pip，请重新安装 Python 并确保勾选 pip"
        exit 1
    }
    
    Write-Success "pip 已安装"
}

# 设置目录
function Setup-Directories {
    Write-Info "创建目录结构..."
    
    # HERMES_HOME 目录
    $hermesHome = $env:HERMES_HOME
    if (-not $hermesHome) {
        $hermesHome = Join-Path $HOME ".Hermes"
    }
    
    # 创建必要目录
    $dirs = @(
        (Join-Path $hermesHome "plugins\hermes-web-chat"),
        (Join-Path $hermesHome "venvs\hermes-web-chat"),
        (Join-Path $hermesHome "bin"),
        (Join-Path $hermesHome "web-chat\uploads")
    )
    
    foreach ($dir in $dirs) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Force -Path $dir | Out-Null
        }
    }
    
    Write-Success "目录创建完成"
    
    return $hermesHome
}

# 创建虚拟环境
function Setup-Venv {
    param([string]$HermesHome)
    
    Write-Info "创建 Python 虚拟环境..."
    
    $venvDir = Join-Path $HermesHome "venvs\hermes-web-chat"
    
    # 如果虚拟环境已存在，先删除
    if (Test-Path $venvDir) {
        Write-Info "删除旧的虚拟环境..."
        Remove-Item -Recurse -Force $venvDir
    }
    
    # 创建新的虚拟环境
    & $pythonCmd -m venv $venvDir
    
    Write-Success "虚拟环境创建完成：$venvDir"
    
    return $venvDir
}

# 安装依赖
function Install-Dependencies {
    param([string]$VenvDir)
    
    Write-Info "安装 Python 依赖..."
    
    # 激活虚拟环境的 pip
    $pipPath = Join-Path $VenvDir "Scripts\pip.exe"
    
    # 升级 pip
    & $pipPath install --upgrade pip -q
    
    # 获取脚本所在目录
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $requirementsPath = Join-Path $scriptDir "requirements.txt"
    
    if (Test-Path $requirementsPath) {
        & $pipPath install -r $requirementsPath -q
    } else {
        & $pipPath install fastapi uvicorn python-multipart httpx -q
    }
    
    Write-Success "依赖安装完成"
}

# 安装/更新代码
function Install-Code {
    param([string]$HermesHome)
    
    Write-Info "安装代码..."
    
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $targetDir = Join-Path $HermesHome "plugins\hermes-web-chat"
    
    # 如果是从 git 克隆的目录运行，复制文件
    if ((Test-Path (Join-Path $scriptDir "hermes_chat.py")) -and ($scriptDir -ne $targetDir)) {
        Write-Info "复制文件到目标目录..."
        Copy-Item -Path "$scriptDir\*" -Destination $targetDir -Recurse -Force
        Write-Success "代码已复制到：$targetDir"
    } else {
        # 检查是否是 git 仓库
        if (Test-Path "$targetDir\.git") {
            Write-Info "更新现有安装..."
            Push-Location $targetDir
            git pull origin main 2>$null
            if ($LASTEXITCODE -ne 0) {
                Write-Warn "git pull 失败，继续使用现有代码"
            }
            Pop-Location
        } else {
            # 尝试克隆仓库
            Write-Info "克隆仓库..."
            if (Get-Command git -ErrorAction SilentlyContinue) {
                git clone https://github.com/guoyu767344855/hermes-web-chat.git $targetDir 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "代码已克隆到：$targetDir"
                } else {
                    Write-Warn "克隆失败，使用当前目录"
                }
            } else {
                Write-Warn "未找到 git，使用当前目录"
            }
        }
    }
}

# 创建启动脚本
function Create-Launcher {
    param([string]$HermesHome, [string]$VenvDir)
    
    Write-Info "创建启动脚本..."
    
    $launcherPath = Join-Path $HermesHome "bin\hermes-web-chat.ps1"
    $pythonPath = Join-Path $VenvDir "Scripts\python.exe"
    $scriptPath = Join-Path $HermesHome "plugins\hermes-web-chat\hermes_chat.py"
    
    $launcherContent = @"
# Hermes Web Chat 启动脚本 (PowerShell)

`$HERMES_HOME = if (`$env:HERMES_HOME) { `$env:HERMES_HOME } else { `$HOME + '\.Hermes' }
`$PYTHON = "`$HERMES_HOME\venvs\hermes-web-chat\Scripts\python.exe"
`$SCRIPT = "`$HERMES_HOME\plugins\hermes-web-chat\hermes_chat.py"

# 检查虚拟环境
if (-not (Test-Path `$PYTHON)) {
    Write-Error "错误：虚拟环境不存在，请重新运行安装脚本"
    exit 1
}

# 检查主程序
if (-not (Test-Path `$SCRIPT)) {
    Write-Error "错误：主程序不存在，请重新运行安装脚本"
    exit 1
}

# 启动服务
& `$PYTHON `$SCRIPT `$args
"@
    
    Set-Content -Path $launcherPath -Value $launcherContent -Encoding UTF8
    
    Write-Success "启动脚本已创建：$launcherPath"
    
    # 创建批处理包装器
    $batPath = Join-Path $HermesHome "bin\hermes-web-chat.bat"
    $batContent = @"
@echo off
set HERMES_HOME=%USERPROFILE%\.Hermes
"%HERMES_HOME%\venvs\hermes-web-chat\Scripts\python.exe" "%HERMES_HOME%\plugins\hermes-web-chat\hermes_chat.py" %*
"@
    Set-Content -Path $batPath -Value $batContent
    
    Write-Success "批处理启动器已创建：$batPath"
}

# 添加到 PATH
function Add-ToPath {
    param([string]$HermesHome)
    
    $binPath = Join-Path $HermesHome "bin"
    
    # 检查是否已在 PATH 中
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($currentPath -notlike "*$binPath*") {
        Write-Info "将 $binPath 添加到用户 PATH..."
        $newPath = "$currentPath;$binPath"
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        Write-Info "已添加到用户 PATH，请重新打开 PowerShell 使更改生效"
    }
}

# 打印完成信息
function Print-Completion {
    param([string]$HermesHome)
    
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║           ✅ 安装完成！                            ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  📍 安装位置：$HermesHome\plugins\hermes-web-chat"
    Write-Host "  🐍 虚拟环境：$HermesHome\venvs\hermes-web-chat"
    Write-Host "  🚀 启动命令：hermes-web-chat"
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  使用方法:"
    Write-Host ""
    Write-Host "    # 启动服务"
    Write-Host "    hermes-web-chat"
    Write-Host ""
    Write-Host "    # 自定义端口"
    Write-Host "    hermes-web-chat --port 9000"
    Write-Host ""
    Write-Host "    # 后台运行"
    Write-Host "    Start-Process hermes-web-chat -WindowStyle Hidden"
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  访问地址：http://localhost:8888"
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
    
    # 检查 PATH
    $binPath = Join-Path $HermesHome "bin"
    if ($env:Path -notlike "*$binPath*") {
        Write-Host "[提示] 运行以下命令使 hermes-web-chat 立即可用:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  `$env:Path += `";$binPath`""
        Write-Host ""
    }
}

# 主函数
function Main {
    Print-Banner
    $pythonCmd = Check-Python
    Check-Pip
    $hermesHome = Setup-Directories
    $venvDir = Setup-Venv -HermesHome $hermesHome
    Install-Dependencies -VenvDir $venvDir
    Install-Code -HermesHome $hermesHome
    Create-Launcher -HermesHome $hermesHome -VenvDir $venvDir
    Add-ToPath -HermesHome $hermesHome
    Print-Completion -HermesHome $hermesHome
}

# 运行
Main
