[CmdletBinding()]
param(
    [ValidateSet("ollama", "lmstudio", "mock")]
    [string]$Mode = "ollama",

    [string]$OllamaModel = "gemma4:e4b",

    [string]$LMStudioModel = "",

    [ValidateRange(1, 65535)]
    [int]$LMStudioPort = 1234,

    [string]$LMStudioGpu = "off",

    [ValidateRange(512, 131072)]
    [int]$LMStudioContextLength = 2048,

    [ValidateRange(1, 16)]
    [int]$LMStudioParallel = 1,

    [ValidateRange(1, 65535)]
    [int]$ApiPort = 8000,

    [ValidateRange(1, 65535)]
    [int]$FrontendPort = 8080,

    [switch]$NoBrowser,

    [switch]$SkipInstall,

    [switch]$InstallOffice,

    [switch]$Stop
)

$ErrorActionPreference = "Stop"

$utf8Output = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $utf8Output
$OutputEncoding = $utf8Output

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$AppDir = Join-Path $ProjectRoot "app"
$BackendDir = Join-Path $AppDir "backend"
$FrontendDir = Join-Path $AppDir "frontend"
$VenvDir = Join-Path $AppDir ".venv-windows"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$LogDir = Join-Path $BackendDir "logs\local_deploy"
$TempFrontend = $null
$ApiProcess = $null
$FrontendProcess = $null
$OllamaProcess = $null
$OllamaStartedByLauncher = $false
$LMStudioProcess = $null
$LMStudioCli = $null
$LMStudioServerStartedByLauncher = $false
$RequiredPythonVersion = "3.12"
$OllamaInstallerUrl = "https://ollama.com/download/OllamaSetup.exe"
$LMStudioInstallerUrl = "https://bionic-installers.lmstudio.ai/win32/x64/1.1.1-5/Bionic-1.1.1-5-x64.exe"
$LMStudioBaseUrl = "http://127.0.0.1:$LMStudioPort/v1"

function Write-Log([string]$Message) {
    Write-Host "[windows-native] $Message"
}

function Throw-DeploymentError([string]$Message) {
    throw $Message
}

function Format-Elapsed([datetime]$StartedAt) {
    $elapsed = (Get-Date) - $StartedAt
    return "{0:00}:{1:00}:{2:00}" -f `
        [int]$elapsed.TotalHours, `
        $elapsed.Minutes, `
        $elapsed.Seconds
}

function Write-OperationProgress(
    [string]$Activity,
    [datetime]$StartedAt,
    [string]$Status,
    [int]$PercentComplete = 0
) {
    $elapsedText = Format-Elapsed $StartedAt
    Write-Progress `
        -Activity $Activity `
        -Status "$Status；已用时 $elapsedText" `
        -PercentComplete ([Math]::Max(0, [Math]::Min(100, $PercentComplete)))
}

function Invoke-ProcessWithProgress(
    [string]$FilePath,
    [string[]]$Arguments,
    [string]$WorkingDirectory,
    [string]$Activity,
    [int]$TimeoutSeconds = 1800,
    [switch]$HideWindow
) {
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $FilePath
    $startInfo.WorkingDirectory = $WorkingDirectory
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $HideWindow.IsPresent
    $startInfo.Arguments = @(
        $Arguments | ForEach-Object {
            $argument = [string]$_
            if ($argument -match "[\s`"]") {
                '"' + $argument.Replace('"', '\"') + '"'
            }
            else {
                $argument
            }
        }
    ) -join " "

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    $startedAt = Get-Date
    $lastHeartbeat = $startedAt

    try {
        if (-not $process.Start()) {
            Throw-DeploymentError "无法启动进程：$FilePath"
        }

        Write-Log "$Activity：已开始。"
        while (-not $process.WaitForExit(1000)) {
            Write-OperationProgress `
                $Activity `
                $startedAt `
                "正在执行，请勿关闭窗口"

            $now = Get-Date
            if (($now - $lastHeartbeat).TotalSeconds -ge 10) {
                Write-Log "$Activity：仍在执行，已用时 $(Format-Elapsed $startedAt)。"
                $lastHeartbeat = $now
            }

            if (((Get-Date) - $startedAt).TotalSeconds -ge $TimeoutSeconds) {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
                Throw-DeploymentError `
                    "$Activity 超时（$TimeoutSeconds 秒），请查看日志或检查网络。"
            }
        }

        $process.WaitForExit()
        Write-Progress -Activity $Activity -Completed
        return $process.ExitCode
    }
    finally {
        if ($process) {
            $process.Dispose()
        }
    }
}

function Refresh-Path {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
}

function Get-ExecutablePath([string[]]$Names) {
    foreach ($name in $Names) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command -and $command.Path) {
            return $command.Path
        }
    }

    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"),
        (Join-Path $env:ProgramFiles "Ollama\ollama.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Ollama\ollama.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Bionic\Bionic.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\LM Studio\LM Studio.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\LM Studio\lms.exe"),
        (Join-Path $env:USERPROFILE ".lmstudio\bin\lms.exe"),
        (Join-Path $env:ProgramFiles "LibreOffice\program\soffice.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "LibreOffice\program\soffice.exe")
    )

    foreach ($candidate in $candidates) {
        if ((Split-Path $candidate -Leaf) -in $Names -and
            (Test-Path -LiteralPath $candidate)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    return $null
}

function Get-PythonInfo([string]$RequiredVersion = $RequiredPythonVersion) {
    $pyPath = Get-ExecutablePath @("py.exe")
    if ($pyPath) {
        $selector = "-$RequiredVersion"
        $version = $null
        $exitCode = 1
        try {
            $version = (& $pyPath $selector "-c" "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')") 2>$null
            $exitCode = $LASTEXITCODE
        }
        catch {
            $version = $null
            $exitCode = 1
        }
        if ($exitCode -eq 0 -and $version -and $version.Trim() -eq $RequiredVersion) {
            return [pscustomobject]@{
                Path = $pyPath
                Arguments = @($selector)
                Version = $RequiredVersion
            }
        }
    }

    $pythonPath = Get-ExecutablePath @("python.exe")
    if ($pythonPath) {
        $version = $null
        $exitCode = 1
        try {
            $version = (& $pythonPath "-c" "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')") 2>$null
            $exitCode = $LASTEXITCODE
        }
        catch {
            $version = $null
            $exitCode = 1
        }
        if ($exitCode -eq 0 -and $version -and $version.Trim() -eq $RequiredVersion) {
            return [pscustomobject]@{
                Path = $pythonPath
                Arguments = @()
                Version = $RequiredVersion
            }
        }
    }

    return $null
}

function Invoke-Python([string]$PythonPath, [string[]]$PythonArguments) {
    $exitCode = Invoke-ProcessWithProgress `
        $PythonPath `
        $PythonArguments `
        $BackendDir `
        "Python：$($PythonArguments -join ' ')" `
        1800
    if ($exitCode -ne 0) {
        Throw-DeploymentError "Python 命令执行失败，退出码：$exitCode"
    }
}

function Install-WingetPackage(
    [string]$PackageId,
    [string]$DisplayName,
    [switch]$Force
) {
    $winget = Get-ExecutablePath @("winget.exe")
    if (-not $winget) {
        Throw-DeploymentError "未找到 winget，无法自动安装 $DisplayName。请先手动安装 $DisplayName，或安装 Windows App Installer。"
    }

    Write-Log "通过 winget 安装 $DisplayName。"
    $wingetArguments = @(
        "install",
        "--id", $PackageId,
        "--exact",
        "--accept-source-agreements",
        "--accept-package-agreements",
        "--locale", "en-US",
        "--silent",
        "--disable-interactivity",
        "--log", (Join-Path $LogDir ("winget-" + $PackageId + ".log"))
    )
    if ($Force) {
        $wingetArguments += "--force"
    }
    $wingetExitCode = Invoke-ProcessWithProgress `
        $winget `
        $wingetArguments `
        $ProjectRoot `
        "正在安装 $DisplayName" `
        1800
    if ($wingetExitCode -ne 0) {
        Throw-DeploymentError "$DisplayName 安装失败，winget 退出码：$wingetExitCode"
    }
    Refresh-Path
}

function Ensure-Python {
    $info = Get-PythonInfo
    if (-not $info) {
        if ($SkipInstall) {
            Throw-DeploymentError "未找到 Python $RequiredPythonVersion。请去掉 -SkipInstall，或手动安装 Python $RequiredPythonVersion。"
        }
        Install-WingetPackage "Python.Python.3.12" "Python $RequiredPythonVersion" -Force
        $info = Get-PythonInfo
    }

    if (-not $info) {
        Throw-DeploymentError "Python $RequiredPythonVersion 安装后仍无法找到可用解释器。请重新打开 PowerShell 后重试。"
    }

    if ($info.Version -ne $RequiredPythonVersion) {
        Throw-DeploymentError "当前 Python 版本为 $($info.Version)，项目部署需要 Python $RequiredPythonVersion。"
    }

    return $info
}

function Ensure-Java {
    $javac = Get-ExecutablePath @("javac.exe")
    $java = Get-ExecutablePath @("java.exe")
    if ($javac -and $java) {
        return @{
            Javac = $javac
            Java = $java
        }
    }

    if ($SkipInstall) {
        Throw-DeploymentError "未找到 JDK。请去掉 -SkipInstall，或手动安装 JDK 17 并将 javac.exe/java.exe 加入 PATH。"
    }

    Install-WingetPackage "Microsoft.OpenJDK.17" "Microsoft OpenJDK 17"
    $javac = Get-ExecutablePath @("javac.exe")
    $java = Get-ExecutablePath @("java.exe")
    if (-not $javac -or -not $java) {
        Throw-DeploymentError "JDK 安装后仍无法找到 javac.exe 或 java.exe。请重新打开 PowerShell 后重试。"
    }

    return @{
        Javac = $javac
        Java = $java
    }
}

function Ensure-Office {
    if (-not $InstallOffice) {
        return $null
    }

    $office = Get-ExecutablePath @("soffice.exe", "soffice")
    if (-not $office) {
        if ($SkipInstall) {
            Throw-DeploymentError "未找到 LibreOffice。请去掉 -SkipInstall，或手动安装 LibreOffice。"
        }
        Install-WingetPackage "TheDocumentFoundation.LibreOffice" "LibreOffice"
        $office = Get-ExecutablePath @("soffice.exe", "soffice")
    }

    if (-not $office) {
        Throw-DeploymentError "LibreOffice 安装后仍无法找到 soffice.exe。"
    }
    return $office
}

function Reset-PythonEnvironment {
    $appRoot = (Resolve-Path -LiteralPath $AppDir).Path.TrimEnd([char]92) +
        [System.IO.Path]::DirectorySeparatorChar
    $venvRoot = [System.IO.Path]::GetFullPath($VenvDir).TrimEnd([char]92)

    if (-not $venvRoot.StartsWith($appRoot, [StringComparison]::OrdinalIgnoreCase)) {
        Throw-DeploymentError "拒绝删除项目目录之外的 Python 虚拟环境：$venvRoot"
    }

    Write-Log "删除不兼容的 Python 虚拟环境：$VenvDir"
    Remove-Item -LiteralPath $VenvDir -Recurse -Force
}

function Ensure-PythonEnvironment($PythonInfo) {
    if (Test-Path -LiteralPath $VenvPython) {
        $venvVersion = (& $VenvPython "-c" "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')") 2>$null
        if ($LASTEXITCODE -ne 0 -or $venvVersion.Trim() -ne $PythonInfo.Version) {
            Reset-PythonEnvironment
        }
    }

    if (-not (Test-Path -LiteralPath $VenvPython)) {
        Write-Log "创建 Windows Python 虚拟环境：$VenvDir"
        Invoke-Python $PythonInfo.Path (@($PythonInfo.Arguments) + @("-m", "venv", "--copies", $VenvDir))
    }

    if (-not (Test-Path -LiteralPath $VenvPython)) {
        Throw-DeploymentError "Python 虚拟环境创建失败：$VenvPython"
    }

    if (-not $SkipInstall) {
        Write-Log "安装后端 Python 依赖，首次安装可能需要几分钟。"
        Invoke-Python $VenvPython @("-m", "pip", "install", "--upgrade", "pip")
        Invoke-Python $VenvPython @("-m", "pip", "install", "-r", (Join-Path $BackendDir "requirements.txt"))
    }

    & $VenvPython "-c" "import fastapi, httpx, sklearn, fitz, pptx" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Throw-DeploymentError "后端依赖不完整，请去掉 -SkipInstall 后重新启动。"
    }
}

function Test-PortInUse([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if ($async.AsyncWaitHandle.WaitOne(250) -and $client.Connected) {
            return $true
        }
        return $false
    }
    catch {
        return $false
    }
    finally {
        $client.Close()
    }
}

function Test-HttpReady([string]$Url) {
    try {
        $null = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3
        return $true
    }
    catch {
        return $false
    }
}

function Wait-HttpReady(
    [string]$Url,
    [string]$Label,
    [int]$TimeoutSeconds,
    [System.Diagnostics.Process]$Process
) {
    $startedAt = Get-Date
    $lastHeartbeat = $startedAt
    Write-Log "$Label：等待服务就绪。"
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpReady $Url) {
            Write-Progress -Activity "$Label 启动" -Completed
            Write-Log "$Label：服务已就绪，耗时 $(Format-Elapsed $startedAt)。"
            return
        }
        if ($Process -and $Process.HasExited) {
            Throw-DeploymentError "$Label 已退出，退出码：$($Process.ExitCode)。请查看日志。"
        }

        Write-OperationProgress `
            "$Label 启动" `
            $startedAt `
            "正在等待 $Url"
        $now = Get-Date
        if (($now - $lastHeartbeat).TotalSeconds -ge 10) {
            Write-Log "$Label：仍未就绪，已用时 $(Format-Elapsed $startedAt)。"
            $lastHeartbeat = $now
        }
        Start-Sleep -Seconds 2
    }
    Write-Progress -Activity "$Label 启动" -Completed
    Throw-DeploymentError "$Label 启动超时：$Url。请查看日志。"
}

function Write-EnvironmentFile([hashtable]$Values) {
    foreach ($entry in $Values.GetEnumerator()) {
        Set-Item -Path ("Env:" + $entry.Key) -Value ([string]$entry.Value)
    }
}

function Start-LoggedProcess(
    [string]$FilePath,
    [string[]]$Arguments,
    [string]$WorkingDirectory,
    [string]$StdoutPath,
    [string]$StderrPath
) {
    $argumentList = @($Arguments)
    return Start-Process -FilePath $FilePath `
        -ArgumentList $argumentList `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $StdoutPath `
        -RedirectStandardError $StderrPath `
        -WindowStyle Hidden `
        -PassThru
}

function Write-PidFile([string]$Name, [int]$ProcessId) {
    Set-Content -LiteralPath (Join-Path $LogDir "$Name.pid") `
        -Value ([string]$ProcessId) -Encoding ASCII
}

function Get-ProcessCommandLine([int]$ProcessId) {
    try {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId"
        if ($process) {
            return [string]$process.CommandLine
        }
    }
    catch {
        return ""
    }
    return ""
}

function Stop-ManagedProcess([string]$Name, [string[]]$ExpectedTokens) {
    $pidPath = Join-Path $LogDir "$Name.pid"
    if (-not (Test-Path -LiteralPath $pidPath)) {
        return
    }

    $pidText = (Get-Content -LiteralPath $pidPath -Raw).Trim()
    $processId = 0
    if (-not [int]::TryParse($pidText, [ref]$processId) -or $processId -le 0) {
        Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
        return
    }

    $commandLine = Get-ProcessCommandLine $processId
    $isMatch = $true
    foreach ($token in $ExpectedTokens) {
        if ($commandLine -notlike "*$token*") {
            $isMatch = $false
            break
        }
    }

    if ($isMatch) {
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($process) {
            Write-Log "停止 $Name（PID $processId）。"
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        }
    }

    Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
}

function Stop-AllServices {
    Stop-ManagedProcess "frontend" @("http.server")
    Stop-ManagedProcess "api" @("uvicorn", "app.main:app")
    Stop-ManagedProcess "ollama-owned" @("ollama.exe", "serve")
    Stop-LMStudioServer
    Write-Log "已停止本项目由启动器创建的服务。"
}

function Prepare-Frontend {
    $TempFrontend = Join-Path $env:TEMP ("gemma4-learning-frontend-" + [Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $TempFrontend -Force | Out-Null
    Copy-Item -Path (Join-Path $FrontendDir "*") -Destination $TempFrontend -Recurse -Force

    $indexPath = Join-Path $TempFrontend "index.html"
    $marker = 'window.__API_BASE__ = "/api";'
    $text = Get-Content -LiteralPath $indexPath -Raw -Encoding UTF8
    if ($text.IndexOf($marker, [StringComparison]::Ordinal) -lt 0) {
        Throw-DeploymentError "前端 index.html 中没有找到 API 配置标记。"
    }
    $replacement = 'window.__API_BASE__ = "http://127.0.0.1:' +
        $ApiPort + '/api";'
    Set-Content -LiteralPath $indexPath `
        -Value $text.Replace($marker, $replacement) `
        -Encoding UTF8 -NoNewline

    return $TempFrontend
}

function Format-ByteSize([Int64]$Bytes) {
    if ($Bytes -ge 1GB) {
        return "{0:N1} GB" -f ($Bytes / 1GB)
    }
    if ($Bytes -ge 1MB) {
        return "{0:N1} MB" -f ($Bytes / 1MB)
    }
    if ($Bytes -ge 1KB) {
        return "{0:N1} KB" -f ($Bytes / 1KB)
    }
    return "$Bytes B"
}

function Download-FileWithProgress(
    [string]$Url,
    [string]$Destination,
    [string]$Label
) {
    $request = $null
    $response = $null
    $inputStream = $null
    $outputStream = $null

    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $startedAt = Get-Date
        $lastHeartbeat = $startedAt
        $request = [Net.HttpWebRequest]::Create($Url)
        $request.Method = "GET"
        $request.UserAgent = "Gemma4 Windows Local Deployment"
        $request.AllowAutoRedirect = $true
        $request.Timeout = 30000
        $request.ReadWriteTimeout = 30000

        $response = $request.GetResponse()
        $totalBytes = [Int64]$response.ContentLength
        $inputStream = $response.GetResponseStream()
        $outputStream = [IO.File]::Open(
            $Destination,
            [IO.FileMode]::Create,
            [IO.FileAccess]::Write,
            [IO.FileShare]::None
        )
        $buffer = New-Object byte[] (1024 * 1024)
        $downloadedBytes = [Int64]0

        while (($readBytes = $inputStream.Read(
            $buffer,
            0,
            $buffer.Length
        )) -gt 0) {
            $outputStream.Write($buffer, 0, $readBytes)
            $downloadedBytes += $readBytes

            $elapsedSeconds = [Math]::Max(
                0.1,
                ((Get-Date) - $startedAt).TotalSeconds
            )
            $bytesPerSecond = $downloadedBytes / $elapsedSeconds
            $speedText = "{0:N1} MB/s" -f ($bytesPerSecond / 1MB)
            if ($totalBytes -gt 0) {
                $percent = [int][Math]::Min(
                    100,
                    ($downloadedBytes * 100) / $totalBytes
                )
                $status = "{0} / {1}" -f `
                    (Format-ByteSize $downloadedBytes), `
                    (Format-ByteSize $totalBytes)
                $remainingSeconds = `
                    ($totalBytes - $downloadedBytes) / [Math]::Max(1, $bytesPerSecond)
                $status = "$status；$speedText；预计剩余 $([int]$remainingSeconds) 秒"
                Write-Progress `
                    -Activity $Label `
                    -Status $status `
                    -PercentComplete $percent
            }
            else {
                $status = "{0}；$speedText" -f `
                    (Format-ByteSize $downloadedBytes)
                Write-Progress `
                    -Activity $Label `
                    -Status $status `
                    -PercentComplete 0
            }

            $now = Get-Date
            if (($now - $lastHeartbeat).TotalSeconds -ge 10) {
                Write-Log "$Label：$status；已用时 $(Format-Elapsed $startedAt)。"
                $lastHeartbeat = $now
            }
        }

        if ($totalBytes -gt 0 -and $downloadedBytes -ne $totalBytes) {
            throw "下载未完成，收到 $downloadedBytes / $totalBytes 字节。"
        }
        Write-Log "$Label：下载完成，共 $(Format-ByteSize $downloadedBytes)。"
    }
    catch {
        Remove-Item -LiteralPath $Destination -Force -ErrorAction SilentlyContinue
        throw "下载文件失败：$($_.Exception.Message)"
    }
    finally {
        if ($outputStream) {
            $outputStream.Dispose()
        }
        if ($inputStream) {
            $inputStream.Dispose()
        }
        if ($response) {
            $response.Dispose()
        }
        if ($request) {
            $request = $null
        }
        Write-Progress -Activity $Label -Completed
    }
}

function Install-OllamaFromOfficialUrl {
    $downloadDir = Join-Path $env:TEMP (
        "gemma4-ollama-" + [Guid]::NewGuid().ToString("N")
    )
    $installerPath = Join-Path $downloadDir "OllamaSetup.exe"
    $installerLog = Join-Path $LogDir "ollama-installer.log"

    New-Item -ItemType Directory -Path $downloadDir -Force | Out-Null
    try {
        Write-Log "从官方地址下载 Ollama：$OllamaInstallerUrl"
        Download-FileWithProgress `
            $OllamaInstallerUrl `
            $installerPath `
            "正在下载 Ollama 安装包"

        Write-Log "Ollama 安装包下载完成，开始安装。"
        $installerArguments = @(
            "/VERYSILENT",
            "/NORESTART",
            "/SUPPRESSMSGBOXES",
            "/LOG=$installerLog"
        )
        $installerExitCode = Invoke-ProcessWithProgress `
            $installerPath `
            $installerArguments `
            $downloadDir `
            "正在安装 Ollama" `
            900 `
            -HideWindow

        if ($installerExitCode -ne 0) {
            Throw-DeploymentError `
                "Ollama 安装失败，安装程序退出码：$installerExitCode。"
        }
    }
    finally {
        if (Test-Path -LiteralPath $downloadDir) {
            Remove-Item `
                -LiteralPath $downloadDir `
                -Recurse `
                -Force `
                -ErrorAction SilentlyContinue
        }
    }
}

function Install-LMStudioFromOfficialUrl {
    $downloadDir = Join-Path $env:TEMP (
        "gemma4-lmstudio-" + [Guid]::NewGuid().ToString("N")
    )
    $installerPath = Join-Path $downloadDir "Bionic-1.1.1-5-x64.exe"
    $installerLog = Join-Path $LogDir "lmstudio-installer.log"

    New-Item -ItemType Directory -Path $downloadDir -Force | Out-Null
    try {
        Write-Log "从官方地址下载 LM Studio：$LMStudioInstallerUrl"
        Download-FileWithProgress `
            $LMStudioInstallerUrl `
            $installerPath `
            "正在下载 LM Studio 安装包"

        Write-Log "LM Studio 安装包下载完成，开始安装。"
        $installerArguments = @(
            "/S",
            "/LOG=$installerLog"
        )
        $installerExitCode = Invoke-ProcessWithProgress `
            $installerPath `
            $installerArguments `
            $downloadDir `
            "正在安装 LM Studio" `
            900 `
            -HideWindow

        if ($installerExitCode -ne 0) {
            Throw-DeploymentError `
                "LM Studio 安装失败，安装程序退出码：$installerExitCode。"
        }
    }
    finally {
        if (Test-Path -LiteralPath $downloadDir) {
            Remove-Item `
                -LiteralPath $downloadDir `
                -Recurse `
                -Force `
                -ErrorAction SilentlyContinue
        }
    }
}

function Ensure-Ollama {
    if ($Mode -ne "ollama") {
        return $null
    }

    $ollama = Get-ExecutablePath @("ollama.exe", "ollama")
    if (-not $ollama) {
        if ($SkipInstall) {
            Throw-DeploymentError "未找到 Ollama。请去掉 -SkipInstall，或手动安装 Ollama。"
        }
        Install-OllamaFromOfficialUrl
        Refresh-Path
        $ollama = Get-ExecutablePath @("ollama.exe", "ollama")
    }

    if (-not $ollama) {
        Throw-DeploymentError "Ollama 安装后仍无法找到 ollama.exe。请重新打开 PowerShell 后重试，或手动确认 Ollama 已安装。"
    }

    if (-not (Test-HttpReady "http://127.0.0.1:11434/api/tags")) {
        if (Test-PortInUse 11434) {
            Throw-DeploymentError "11434 端口已被占用，但不是可用的 Ollama 服务。"
        }

        Write-Log "启动 Windows Ollama 服务。"
        $env:OLLAMA_HOST = "127.0.0.1:11434"
        $script:OllamaProcess = Start-LoggedProcess `
            $ollama @("serve") $ProjectRoot `
            (Join-Path $LogDir "ollama.log") `
            (Join-Path $LogDir "ollama.error.log")
        $script:OllamaStartedByLauncher = $true
        Write-PidFile "ollama-owned" $script:OllamaProcess.Id
        Wait-HttpReady "http://127.0.0.1:11434/api/tags" "Ollama" 90 $script:OllamaProcess
    }
    else {
        Write-Log "检测到已有 Windows Ollama 服务，复用现有服务。"
    }

    if ([string]::IsNullOrWhiteSpace($OllamaModel)) {
        Throw-DeploymentError "Ollama 模型名称不能为空。"
    }

    $models = @(& $ollama list 2>$null)
    $modelFound = $models |
        Select-Object -Skip 1 |
        ForEach-Object { ($_ -split "\s+")[0] } |
        Where-Object { $_ -eq $OllamaModel }
    if (-not $modelFound) {
        Write-Log "本地没有模型 $OllamaModel，开始下载。"
        $pullExitCode = Invoke-ProcessWithProgress `
            $ollama `
            @("pull", $OllamaModel) `
            $ProjectRoot `
            "正在下载 Ollama 模型 $OllamaModel" `
            7200
        if ($pullExitCode -ne 0) {
            Throw-DeploymentError "Ollama 模型下载失败：$OllamaModel，退出码：$pullExitCode"
        }
    }

    return $ollama
}

function Invoke-LMStudioCli(
    [string]$CliPath,
    [string[]]$Arguments,
    [int]$TimeoutSeconds = 120
) {
    $output = @(Invoke-LMStudioCliCapture $CliPath $Arguments $TimeoutSeconds)
    $output | ForEach-Object { Write-Host ([string]$_) }
}

function Invoke-LMStudioCliCapture(
    [string]$CliPath,
    [string[]]$Arguments,
    [int]$TimeoutSeconds = 120
) {
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $CliPath
    $startInfo.WorkingDirectory = $ProjectRoot
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.Arguments = @(
        $Arguments | ForEach-Object {
            $argument = [string]$_
            if ($argument -match "[\s`"]") {
                '"' + $argument.Replace('"', '\"') + '"'
            }
            else {
                $argument
            }
        }
    ) -join " "

    $process = $null

    try {
        $process = New-Object System.Diagnostics.Process
        $process.StartInfo = $startInfo
        if (-not $process.Start()) {
            throw "无法启动 LM Studio 命令：$CliPath"
        }
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        $startedAt = Get-Date
        $lastHeartbeat = $startedAt
        $activity = "LM Studio 命令"
        $status = "正在执行：$($Arguments -join ' ')"
        Write-Log "$activity：已开始，$status。"

        while (-not $process.WaitForExit(1000)) {
            Write-OperationProgress $activity $startedAt $status
            $now = Get-Date
            if (($now - $lastHeartbeat).TotalSeconds -ge 10) {
                Write-Log "$activity：仍在执行，已用时 $(Format-Elapsed $startedAt)。"
                $lastHeartbeat = $now
            }

            if (((Get-Date) - $startedAt).TotalSeconds -ge $TimeoutSeconds) {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
                throw `
                    "LM Studio 命令执行超时（$TimeoutSeconds 秒）：$CliPath $($Arguments -join ' ')"
            }
        }

        $process.WaitForExit()
        Write-Progress -Activity $activity -Completed
        $output = @()
        $stdout = $stdoutTask.Result
        $stderr = $stderrTask.Result
        if (-not [string]::IsNullOrWhiteSpace($stdout)) {
            $output += @($stdout -split "`r?`n" | Where-Object { $_ -ne "" })
        }
        if (-not [string]::IsNullOrWhiteSpace($stderr)) {
            $output += @($stderr -split "`r?`n" | Where-Object { $_ -ne "" })
        }

        if ($process.ExitCode -ne 0) {
            $detail = ($output | Select-Object -Last 3) -join " "
            throw `
                "LM Studio 命令执行失败，退出码：$($process.ExitCode)。$detail"
        }

        return $output
    }
    finally {
        if ($process) {
            $process.Dispose()
        }
    }
}

function Get-LMStudioModelIds {
    try {
        $response = Invoke-RestMethod `
            -UseBasicParsing `
            -Uri "$LMStudioBaseUrl/models" `
            -TimeoutSec 5
        return @(
            $response.data |
                ForEach-Object { [string]$_.id } |
                Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
        )
    }
    catch {
        return @()
    }
}

function Get-LMStudioLocalModelIds([string]$CliPath) {
    if (-not $CliPath) {
        return @()
    }

    try {
        $jsonOutput = @(Invoke-LMStudioCliCapture $CliPath @("ls", "--json") 20)
        $jsonText = ($jsonOutput -join "`n").Trim()
        if ($jsonText) {
            $json = $jsonText | ConvertFrom-Json
            $items = @()
            if ($json -is [System.Array]) {
                $items = @($json)
            }
            elseif ($json.models) {
                $items = @($json.models)
            }
            elseif ($json.data) {
                $items = @($json.data)
            }
            else {
                $items = @($json)
            }

            $models = @()
            foreach ($item in $items) {
                foreach ($propertyName in @("modelKey", "key", "id", "identifier")) {
                    $property = $item.PSObject.Properties[$propertyName]
                    if ($property -and
                        $property.Value -is [string] -and
                        -not [string]::IsNullOrWhiteSpace($property.Value)) {
                        $models += $property.Value.Trim()
                        break
                    }
                }
            }
            if ($models.Count -gt 0) {
                return @($models | Select-Object -Unique)
            }
        }
    }
    catch {
        # Older lms versions may not support --json; use the text output below.
    }

    try {
        $textOutput = @(Invoke-LMStudioCliCapture $CliPath @("ls") 20)
        $models = @()
        foreach ($line in $textOutput) {
            $trimmed = ([string]$line).Trim()
            if (-not $trimmed -or
                $trimmed -match "^(?i:model|name|no models|loading|error)") {
                continue
            }
            if ($trimmed -match "^(?<model>\S+)(?:\s+|$)") {
                $models += $Matches["model"]
            }
        }
        return @($models | Select-Object -Unique)
    }
    catch {
        return @()
    }
}

function Get-LMStudioLoadedModelIds([string]$CliPath) {
    if (-not $CliPath) {
        return @()
    }

    try {
        $jsonOutput = @(Invoke-LMStudioCliCapture $CliPath @("ps", "--json") 20)
        $jsonText = ($jsonOutput -join "`n").Trim()
        if (-not $jsonText) {
            return @()
        }

        $json = $jsonText | ConvertFrom-Json
        $items = if ($json -is [System.Array]) {
            @($json)
        }
        elseif ($json.models) {
            @($json.models)
        }
        elseif ($json.data) {
            @($json.data)
        }
        else {
            @($json)
        }

        $models = @()
        foreach ($item in $items) {
            foreach ($propertyName in @(
                "identifier",
                "modelKey",
                "model",
                "id"
            )) {
                $property = $item.PSObject.Properties[$propertyName]
                if ($property -and
                    $property.Value -is [string] -and
                    -not [string]::IsNullOrWhiteSpace($property.Value)) {
                    $models += $property.Value.Trim()
                    break
                }
            }
        }
        return @($models | Select-Object -Unique)
    }
    catch {
        return @()
    }
}

function Wait-LMStudioModel(
    [string]$ModelId,
    [int]$TimeoutSeconds
) {
    $startedAt = Get-Date
    $lastHeartbeat = $startedAt
    Write-Log "LM Studio 模型：等待 '$ModelId' 加载完成。"
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $loadedModelIds = @(Get-LMStudioLoadedModelIds $script:LMStudioCli)
        if ($loadedModelIds -contains $ModelId) {
            Write-Progress -Activity "加载 LM Studio 模型" -Completed
            Write-Log "LM Studio 模型：'$ModelId' 已加载，耗时 $(Format-Elapsed $startedAt)。"
            return
        }

        Write-OperationProgress `
            "加载 LM Studio 模型" `
            $startedAt `
            "正在等待模型服务报告 '$ModelId'"
        $now = Get-Date
        if (($now - $lastHeartbeat).TotalSeconds -ge 10) {
            Write-Log "LM Studio 模型：仍在加载，已用时 $(Format-Elapsed $startedAt)。"
            $lastHeartbeat = $now
        }
        Start-Sleep -Seconds 2
    }
    Write-Progress -Activity "加载 LM Studio 模型" -Completed
    Throw-DeploymentError `
        "LM Studio 模型加载超时：$ModelId。请检查 LM Studio 窗口和日志。"
}

function Test-LMStudioChatCompletion([string]$ModelId) {
    $startedAt = Get-Date
    Write-Log "LM Studio 模型：执行生成自检。"

    $payload = @{
        model = $ModelId
        messages = @(
            @{
                role = "user"
                content = "Reply only with OK."
            }
        )
        temperature = 0.2
        max_tokens = 128
        stream = $false
    } | ConvertTo-Json -Depth 8

    try {
        Write-OperationProgress `
            "LM Studio 生成自检" `
            $startedAt `
            "正在调用 $LMStudioBaseUrl/chat/completions"

        $response = Invoke-WebRequest `
            -UseBasicParsing `
            -Uri "$LMStudioBaseUrl/chat/completions" `
            -Method Post `
            -ContentType "application/json; charset=utf-8" `
            -Body ([System.Text.Encoding]::UTF8.GetBytes($payload)) `
            -TimeoutSec 180

        $data = $response.Content | ConvertFrom-Json
        $message = $data.choices[0].message
        $content = if ($message.PSObject.Properties["content"]) {
            [string]$message.content
        }
        else {
            ""
        }
        $reasoning = if ($message.PSObject.Properties["reasoning_content"]) {
            [string]$message.reasoning_content
        }
        else {
            ""
        }

        $loadedModelIds = @(Get-LMStudioLoadedModelIds $script:LMStudioCli)
        if ($loadedModelIds -notcontains $ModelId) {
            Throw-DeploymentError `
                "LM Studio 生成自检后模型不再处于已加载状态，模型可能刚刚崩溃。"
        }

        Write-Progress -Activity "LM Studio 生成自检" -Completed
        if ([string]::IsNullOrWhiteSpace($content) -and
            -not [string]::IsNullOrWhiteSpace($reasoning)) {
            Write-Log "LM Studio 生成自检通过；模型返回了 reasoning_content，后端会继续等待正式回答内容。"
        }
        else {
            Write-Log "LM Studio 生成自检通过，耗时 $(Format-Elapsed $startedAt)。"
        }
    }
    catch {
        Write-Progress -Activity "LM Studio 生成自检" -Completed
        $detail = $_.Exception.Message
        $response = $_.Exception.Response
        if ($response) {
            try {
                $stream = $response.GetResponseStream()
                if ($stream) {
                    $reader = New-Object System.IO.StreamReader($stream)
                    $body = $reader.ReadToEnd()
                    if (-not [string]::IsNullOrWhiteSpace($body)) {
                        $detail = "$detail；响应内容：$body"
                    }
                }
            }
            catch {
            }
        }

        Throw-DeploymentError `
            "LM Studio 模型生成自检失败：$detail。日志中如果出现 Channel Error 或 model has crashed，通常是 LM Studio 推理后端、显卡驱动或 GPU/Vulkan 配置与当前 Gemma 模型不兼容。请先使用默认 CPU 模式，或升级 LM Studio 和显卡驱动后再尝试 -LMStudioGpu max。"
    }
}

function Unload-LMStudioModels([string]$CliPath) {
    if (-not $CliPath) {
        return
    }

    try {
        Write-Log "卸载 LM Studio 中已加载的模型，以应用当前加载参数。"
        Invoke-LMStudioCli $CliPath @("unload", "--all") 60
    }
    catch {
        Write-Log "卸载 LM Studio 已加载模型时出现提示：$($_.Exception.Message)"
    }
}

function Load-LMStudioModel(
    [string]$CliPath,
    [string]$ModelId
) {
    if (-not $CliPath) {
        Throw-DeploymentError `
            "未找到 lms 命令行工具，无法自动加载 LM Studio 模型 '$ModelId'。"
    }

    $loadArgs = @(
        "load",
        "--yes",
        "--gpu",
        $LMStudioGpu,
        "--context-length",
        [string]$LMStudioContextLength,
        "--parallel",
        [string]$LMStudioParallel,
        $ModelId
    )

    Write-Log "加载 LM Studio 模型：$ModelId（GPU=$LMStudioGpu，Context=$LMStudioContextLength，Parallel=$LMStudioParallel）"
    Invoke-LMStudioCli $CliPath $loadArgs 240
    Wait-LMStudioModel $ModelId 180
}

function Resolve-LMStudioModel([string]$CliPath) {
    $loadedModelIds = @(Get-LMStudioLoadedModelIds $CliPath)
    $requestedModel = if ($null -eq $LMStudioModel) {
        ""
    }
    else {
        $LMStudioModel.Trim()
    }

    if ($requestedModel) {
        if ($loadedModelIds -contains $requestedModel) {
            return $requestedModel
        }

        $localModelIds = @(Get-LMStudioLocalModelIds $CliPath)
        if ($localModelIds.Count -gt 0 -and
            $localModelIds -notcontains $requestedModel) {
            $available = $localModelIds -join ", "
            Throw-DeploymentError `
                "LM Studio 中没有找到模型 '$requestedModel'。当前已下载模型：$available"
        }
        Load-LMStudioModel $CliPath $requestedModel
        return $requestedModel
    }

    $gemmaModels = @(
        $loadedModelIds | Where-Object { $_ -match "(?i)gemma" }
    )
    if ($gemmaModels.Count -eq 1) {
        return $gemmaModels[0]
    }
    if ($gemmaModels.Count -gt 1) {
        Throw-DeploymentError `
            "检测到多个 Gemma 模型，请使用 -LMStudioModel 指定其中一个：$($gemmaModels -join ', ')"
    }

    $localModelIds = @(Get-LMStudioLocalModelIds $CliPath)
    $localGemmaModels = @(
        $localModelIds | Where-Object { $_ -match "(?i)gemma" }
    )
    if ($localGemmaModels.Count -eq 1) {
        Load-LMStudioModel $CliPath $localGemmaModels[0]
        return $localGemmaModels[0]
    }
    if ($localGemmaModels.Count -gt 1) {
        Throw-DeploymentError `
            "检测到多个已下载的 Gemma 模型，请使用 -LMStudioModel 指定其中一个：$($localGemmaModels -join ', ')"
    }
    if ($localModelIds.Count -eq 1) {
        Load-LMStudioModel $CliPath $localModelIds[0]
        return $localModelIds[0]
    }
    if ($loadedModelIds.Count -eq 0 -and $localModelIds.Count -eq 0) {
        Throw-DeploymentError `
            "LM Studio 服务已启动，但没有检测到模型。请先在 LM Studio 中下载或导入 Gemma 模型，然后重试。"
    }

    Throw-DeploymentError `
        "未自动选择 Gemma 模型。请使用 -LMStudioModel 指定模型 ID。已加载：$($loadedModelIds -join ', ')；已下载：$($localModelIds -join ', ')"
}

function Stop-LMStudioServer {
    $flagPath = Join-Path $LogDir "lmstudio-owned.flag"
    if (-not $script:LMStudioServerStartedByLauncher -and
        -not (Test-Path -LiteralPath $flagPath)) {
        return
    }

    $cli = $script:LMStudioCli
    if (-not $cli) {
        $cli = Get-ExecutablePath @("lms.exe", "lms.cmd", "lms")
    }
    if ($cli) {
        Write-Log "停止本项目启动的 LM Studio 本地服务。"
        try {
            Invoke-LMStudioCli $cli @("server", "stop") 30
        }
        catch {
            Write-Log "停止 LM Studio 本地服务时出现提示：$($_.Exception.Message)"
        }
    }

    Remove-Item -LiteralPath $flagPath -Force -ErrorAction SilentlyContinue
    $script:LMStudioServerStartedByLauncher = $false
}

function Ensure-LMStudio {
    if ($Mode -ne "lmstudio") {
        return $null
    }

    $appPath = Get-ExecutablePath @(
        "Bionic.exe",
        "LM Studio.exe",
        "LM-Studio.exe",
        "lmstudio.exe"
    )
    if (-not $appPath) {
        if ($SkipInstall) {
            Throw-DeploymentError `
                "未找到 LM Studio。请去掉 -SkipInstall，或手动安装 LM Studio。"
        }
        Install-LMStudioFromOfficialUrl
        Refresh-Path
        $appPath = Get-ExecutablePath @(
            "Bionic.exe",
            "LM Studio.exe",
            "LM-Studio.exe",
            "lmstudio.exe"
        )
    }

    if (-not $appPath) {
        Throw-DeploymentError `
            "LM Studio 安装后仍无法找到 Bionic.exe 或 LM Studio.exe。请重新打开 PowerShell 后重试。"
    }

    $serverUrl = "$LMStudioBaseUrl/models"
    $cliPath = Get-ExecutablePath @("lms.exe", "lms.cmd", "lms")

    if (-not (Test-HttpReady $serverUrl)) {
        if (Test-PortInUse $LMStudioPort) {
            Throw-DeploymentError `
                "LM Studio 端口 $LMStudioPort 已被占用，但不是可用的 LM Studio 服务。"
        }

        Write-Log "启动 LM Studio 应用，以初始化本地服务工具。"
        $script:LMStudioProcess = Start-Process `
            -FilePath $appPath `
            -WorkingDirectory (Split-Path -Parent $appPath) `
            -PassThru

        $appStartedAt = Get-Date
        $lastHeartbeat = $appStartedAt
        Write-Log "LM Studio 应用已启动，等待 lms 命令行工具就绪。"
        $deadline = (Get-Date).AddSeconds(60)
        while (-not $cliPath -and (Get-Date) -lt $deadline) {
            Write-OperationProgress `
                "初始化 LM Studio" `
                $appStartedAt `
                "正在等待 lms 命令行工具"
            $now = Get-Date
            if (($now - $lastHeartbeat).TotalSeconds -ge 10) {
                Write-Log "初始化 LM Studio：仍在等待 lms，已用时 $(Format-Elapsed $appStartedAt)。"
                $lastHeartbeat = $now
            }
            Start-Sleep -Seconds 2
            Refresh-Path
            $cliPath = Get-ExecutablePath @("lms.exe", "lms.cmd", "lms")
        }
        Write-Progress -Activity "初始化 LM Studio" -Completed

        if (-not $cliPath) {
            Throw-DeploymentError `
                "未找到 LM Studio 命令行工具 lms。请先启动一次 LM Studio，确认本地服务功能可用后重试。"
        }

        Write-Log "初始化 LM Studio 本地 daemon。"
        try {
            Invoke-LMStudioCli $cliPath @("daemon", "up") 60
        }
        catch {
            Write-Log "LM Studio daemon 初始化未成功，将继续尝试启动本地 API：$($_.Exception.Message)"
        }

        Write-Log "启动 LM Studio 本地 API：$LMStudioBaseUrl"
        Invoke-LMStudioCli $cliPath @(
            "server",
            "start",
            "--port",
            [string]$LMStudioPort
        ) 90
        $script:LMStudioCli = $cliPath
        $script:LMStudioServerStartedByLauncher = $true
        Set-Content `
            -LiteralPath (Join-Path $LogDir "lmstudio-owned.flag") `
            -Value ([string]$LMStudioPort) `
            -Encoding ASCII
        Wait-HttpReady $serverUrl "LM Studio" 90 $null
    }
    else {
        Write-Log "检测到已有 LM Studio 本地服务，复用现有服务。"
        if (-not $cliPath) {
            $cliPath = Get-ExecutablePath @("lms.exe", "lms.cmd", "lms")
        }
    }

    $script:LMStudioCli = $cliPath
    Unload-LMStudioModels $cliPath
    $modelId = Resolve-LMStudioModel $cliPath
    Test-LMStudioChatCompletion $modelId
    Write-Log "LM Studio 当前模型：$modelId"

    return [pscustomobject]@{
        AppPath = $appPath
        CliPath = $cliPath
        BaseUrl = $LMStudioBaseUrl
        Model = $modelId
    }
}

function Set-RuntimeEnvironment($JavaInfo, [string]$OfficePath, $LMStudioInfo) {
    $runtimeProvider = $Mode
    $values = @{
        APP_NAME = "Gemma4 Private Learning Agent API"
        API_HOST = "127.0.0.1"
        API_PORT = $ApiPort
        CORS_ORIGINS = "http://localhost:$FrontendPort,http://127.0.0.1:$FrontendPort"
        MODEL_PROVIDER = $runtimeProvider
        OLLAMA_BASE_URL = "http://127.0.0.1:11434"
        OLLAMA_MODEL = $OllamaModel
        KNOWLEDGE_DIR = (Join-Path $BackendDir "data\knowledge")
        SUBJECT_BASE_DIR = (Join-Path $BackendDir "data\subjects")
        RAG_INDEX_PATH = (Join-Path $BackendDir "data\hybrid_rag.joblib")
        CHAT_LOG_PATH = (Join-Path $BackendDir "data\qa_history.jsonl")
        FEEDBACK_LOG_PATH = (Join-Path $BackendDir "data\feedback.jsonl")
        CONVERSATION_DB_PATH = (Join-Path $BackendDir "data\learning_agent.db")
        JAVA_RUN_ENABLED = "true"
        JAVA_JAVAC = $JavaInfo.Javac
        JAVA_RUNTIME = $JavaInfo.Java
    }

    if ($Mode -eq "lmstudio") {
        if (-not $LMStudioInfo) {
            Throw-DeploymentError "LM Studio 服务信息初始化失败。"
        }
        $values["MODEL_PROVIDER"] = "openai_compatible"
        $values["VLLM_BASE_URL"] = $LMStudioInfo.BaseUrl
        $values["VLLM_API_KEY"] = "EMPTY"
        $values["VLLM_MODEL"] = $LMStudioInfo.Model
        $values["LMSTUDIO_BASE_URL"] = $LMStudioInfo.BaseUrl
        $values["LMSTUDIO_MODEL"] = $LMStudioInfo.Model
    }

    if ($OfficePath) {
        $values["OFFICE_CONVERTER"] = $OfficePath
    }
    Write-EnvironmentFile $values
}

function Start-ApplicationServices {
    param(
        [string]$PythonPath,
        [string]$FrontendPath
    )

    $apiLog = Join-Path $LogDir "api.log"
    $apiErrorLog = Join-Path $LogDir "api.error.log"
    $frontendLog = Join-Path $LogDir "frontend.log"
    $frontendErrorLog = Join-Path $LogDir "frontend.error.log"

    Write-Log "启动 FastAPI。"
    $script:ApiProcess = Start-LoggedProcess `
        $PythonPath @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", [string]$ApiPort) `
        $BackendDir $apiLog $apiErrorLog
    Write-PidFile "api" $ApiProcess.Id
    Wait-HttpReady "http://127.0.0.1:$ApiPort/api/healthz" "FastAPI" 120 $ApiProcess

    Write-Log "启动前端。"
    $script:FrontendProcess = Start-LoggedProcess `
        $PythonPath @("-m", "http.server", [string]$FrontendPort, "--bind", "127.0.0.1") `
        $FrontendPath $frontendLog $frontendErrorLog
    Write-PidFile "frontend" $FrontendProcess.Id
    Wait-HttpReady "http://127.0.0.1:$FrontendPort/" "前端" 30 $FrontendProcess
}

function Open-Browser {
    if ($NoBrowser) {
        return
    }
    Start-Process "http://127.0.0.1:$FrontendPort"
}

function Remove-TemporaryFrontend {
    if ($script:TempFrontend -and (Test-Path -LiteralPath $script:TempFrontend)) {
        Remove-Item -LiteralPath $script:TempFrontend -Recurse -Force -ErrorAction SilentlyContinue
        $script:TempFrontend = $null
    }
}

function Cleanup-StartedServices {
    if ($script:FrontendProcess -and -not $script:FrontendProcess.HasExited) {
        Stop-Process -Id $script:FrontendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    if ($script:ApiProcess -and -not $script:ApiProcess.HasExited) {
        Stop-Process -Id $script:ApiProcess.Id -Force -ErrorAction SilentlyContinue
    }
    if ($script:OllamaStartedByLauncher -and
        $script:OllamaProcess -and
        -not $script:OllamaProcess.HasExited) {
        Stop-Process -Id $script:OllamaProcess.Id -Force -ErrorAction SilentlyContinue
    }

    Remove-Item -LiteralPath (Join-Path $LogDir "frontend.pid") -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $LogDir "api.pid") -Force -ErrorAction SilentlyContinue
    if ($script:OllamaStartedByLauncher) {
        Remove-Item -LiteralPath (Join-Path $LogDir "ollama-owned.pid") -Force -ErrorAction SilentlyContinue
    }
    Stop-LMStudioServer
    Remove-TemporaryFrontend
}

function Main {
    if (-not (Test-Path -LiteralPath $BackendDir) -or
        -not (Test-Path -LiteralPath $FrontendDir)) {
        Throw-DeploymentError "项目目录结构不完整：$ProjectRoot"
    }

    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

    if ($Stop) {
        Stop-AllServices
        return
    }

    if ($ApiPort -eq $FrontendPort) {
        Throw-DeploymentError "FastAPI 和前端不能使用相同端口。"
    }
    if ($Mode -eq "lmstudio" -and
        ($ApiPort -eq $LMStudioPort -or $FrontendPort -eq $LMStudioPort)) {
        Throw-DeploymentError "LM Studio、FastAPI 和前端不能使用相同端口。"
    }

    Stop-AllServices
    if (Test-PortInUse $ApiPort) {
        Throw-DeploymentError "FastAPI 端口 $ApiPort 已被占用。"
    }
    if (Test-PortInUse $FrontendPort) {
        Throw-DeploymentError "前端端口 $FrontendPort 已被占用。"
    }

    try {
        $pythonInfo = Ensure-Python
        $javaInfo = Ensure-Java
        $officePath = Ensure-Office
        Ensure-PythonEnvironment $pythonInfo
        $lmStudioInfo = $null
        if ($Mode -eq "ollama") {
            $null = Ensure-Ollama
        }
        elseif ($Mode -eq "lmstudio") {
            $lmStudioInfo = Ensure-LMStudio
        }

        Set-RuntimeEnvironment $javaInfo $officePath $lmStudioInfo

        $script:TempFrontend = Prepare-Frontend
        Start-ApplicationServices $VenvPython $script:TempFrontend
        Open-Browser

        $apiLog = Join-Path $LogDir "api.log"
        $frontendLog = Join-Path $LogDir "frontend.log"

        Write-Log "Windows 原生本地部署已完成。"
        Write-Log "学习平台：http://127.0.0.1:$FrontendPort"
        Write-Log "FastAPI：http://127.0.0.1:$ApiPort/api/healthz"
        if ($Mode -eq "ollama") {
            Write-Log "Ollama：http://127.0.0.1:11434"
            Write-Log "模型：$OllamaModel"
        }
        elseif ($Mode -eq "lmstudio") {
            Write-Log "LM Studio API：$($lmStudioInfo.BaseUrl)"
            Write-Log "模型：$($lmStudioInfo.Model)"
        }
        else {
            Write-Log "当前为 Mock 模式，不调用真实模型。"
        }
        Write-Log "日志目录：$LogDir"
        Write-Log "按 Ctrl+C 停止本次启动的服务。"

        while ($true) {
            if ($ApiProcess.HasExited) {
                Throw-DeploymentError "FastAPI 已退出，请查看 $apiLog。"
            }
            if ($FrontendProcess.HasExited) {
                Throw-DeploymentError "前端服务已退出，请查看 $frontendLog。"
            }
            Start-Sleep -Seconds 2
        }
    }
    finally {
        Cleanup-StartedServices
    }
}

try {
    Main
}
catch {
    Write-Host ""
    Write-Host "Windows 原生部署失败：$($_.Exception.Message)" -ForegroundColor Red
    Write-Host "请查看 $LogDir 下的日志。" -ForegroundColor Yellow
    exit 1
}
