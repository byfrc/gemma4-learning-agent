from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path


class JavaRunnerError(ValueError):
    """Raised when a Java submission cannot be accepted or executed."""


class JavaToolchainError(RuntimeError):
    """Raised when javac or java is unavailable on the server."""


@dataclass(frozen=True)
class JavaExecutionResult:
    success: bool
    output: str
    error: str
    compile_output: str
    duration_ms: int
    timed_out: bool = False


_FORBIDDEN_PATTERNS = (
    (r"(?im)^\s*package\s+", "暂不支持 package 声明，请直接使用 Main 类。"),
    (
        r"\b(?:java\s*\.\s*(?:io|nio\s*\.\s*file|net|lang\s*\.\s*reflect))\b",
        "在线IDE 禁止访问文件、网络和反射 API。",
    ),
    (
        r"\b(?:ProcessBuilder|Runtime\s*\.\s*getRuntime|System\s*\.\s*exit|"
        r"Class\s*\.\s*forName|setAccessible|Unsafe|Socket|ServerSocket|"
        r"DatagramSocket|URLClassLoader|FileInputStream|FileOutputStream|"
        r"Files\s*\.\s*|Path\s*\.\s*)\b",
        "在线IDE 禁止启动进程、退出宿主服务或访问受限系统 API。",
    ),
)


def _resolve_executable(configured: str) -> str:
    configured = (configured or "").strip()
    if not configured:
        raise JavaToolchainError("Java 工具链配置为空。")

    configured_path = Path(configured)
    if configured_path.is_absolute():
        if configured_path.exists() and os.access(configured_path, os.X_OK):
            return str(configured_path)
        raise JavaToolchainError(f"找不到可执行文件：{configured}")

    resolved = shutil.which(configured)
    if not resolved:
        raise JavaToolchainError(
            f"服务器未找到 {configured}，请安装 JDK 并配置 JAVA_JAVAC/JAVA_RUNTIME。"
        )
    return resolved


def _decode_output(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.decode("utf-8", errors="replace")


def _validate_source(code: str, max_code_bytes: int) -> None:
    if not code.strip():
        raise JavaRunnerError("请输入 Java 代码。")
    if len(code.encode("utf-8")) > max_code_bytes:
        raise JavaRunnerError(
            f"代码不能超过 {max_code_bytes // 1024} KB。"
        )

    if not re.search(r"\bclass\s+Main\b", code):
        raise JavaRunnerError("代码必须包含名为 Main 的类。")

    public_classes = re.findall(
        r"\bpublic\s+(?:final\s+|abstract\s+)?class\s+([A-Za-z_$][\w$]*)",
        code,
    )
    if any(name != "Main" for name in public_classes):
        raise JavaRunnerError("公开类必须命名为 Main。")

    for pattern, message in _FORBIDDEN_PATTERNS:
        if re.search(pattern, code):
            raise JavaRunnerError(message)


def _resource_limited_command(
    command: list[str],
    cpu_seconds: int,
) -> list[str]:
    # Avoid Popen(preexec_fn=...) because the API executes this code in a worker thread.
    prlimit = shutil.which("prlimit")
    if not prlimit:
        return command

    return [
        prlimit,
        f"--cpu={cpu_seconds + 1}",
        "--nofile=64",
        "--nproc=64",
        "--",
        *command,
    ]


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return

    try:
        os.killpg(process.pid, signal.SIGKILL)
        return
    except (AttributeError, OSError):
        pass

    try:
        process.kill()
    except OSError:
        pass


def _read_limited(
    stream,
    buffer: list[bytes],
    output_limit: int,
    output_exceeded: threading.Event,
    process: subprocess.Popen[bytes],
) -> None:
    total = 0
    try:
        while True:
            chunk = stream.read(8192)
            if not chunk:
                return
            total += len(chunk)
            if total <= output_limit:
                buffer.append(chunk)
            elif not output_exceeded.is_set():
                output_exceeded.set()
                _terminate_process(process)
    finally:
        stream.close()


def _run_process(
    command: list[str],
    cwd: Path,
    stdin_text: str,
    timeout_seconds: int,
    output_limit: int,
) -> tuple[str, str, bool, bool]:
    command = _resource_limited_command(command, timeout_seconds)
    environment = {
        "HOME": str(cwd),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": os.getenv("PATH", "/usr/bin:/bin"),
        "TMPDIR": str(cwd),
    }
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )

    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []
    output_exceeded = threading.Event()
    stdout_thread = threading.Thread(
        target=_read_limited,
        args=(
            process.stdout,
            stdout_chunks,
            output_limit,
            output_exceeded,
            process,
        ),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_read_limited,
        args=(
            process.stderr,
            stderr_chunks,
            output_limit,
            output_exceeded,
            process,
        ),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()

    try:
        if process.stdin is not None:
            process.stdin.write(stdin_text.encode("utf-8"))
            process.stdin.close()
        process.wait(timeout=timeout_seconds)
        timed_out = False
    except (BrokenPipeError, OSError):
        timed_out = False
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            _terminate_process(process)
            process.wait()
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_process(process)
        process.wait()

    stdout_thread.join(timeout=2)
    stderr_thread.join(timeout=2)

    return (
        _decode_output(b"".join(stdout_chunks)),
        _decode_output(b"".join(stderr_chunks)),
        timed_out,
        output_exceeded.is_set(),
    )


def _compile_source(
    javac: str,
    source_path: Path,
    workdir: Path,
    timeout_seconds: int,
    output_limit: int,
) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [
                javac,
                "-encoding",
                "UTF-8",
                "-J-Xmx128m",
                "-d",
                str(workdir),
                str(source_path),
            ],
            cwd=str(workdir),
            env={
                "HOME": str(workdir),
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "PATH": os.getenv("PATH", "/usr/bin:/bin"),
                "TMPDIR": str(workdir),
            },
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return False, (
            "Java 编译超时，请检查是否存在过于复杂的代码。"
            f"\n{_decode_output(exc.stderr)}"
        )
    except OSError as exc:
        raise JavaToolchainError(f"无法启动 javac：{exc}") from exc

    compile_output = "\n".join(
        part
        for part in (
            _decode_output(result.stdout),
            _decode_output(result.stderr),
        )
        if part.strip()
    )
    if len(compile_output.encode("utf-8")) > output_limit:
        compile_output = compile_output[:output_limit]
        compile_output += "\n编译输出超过限制，已截断。"

    return result.returncode == 0, compile_output


def run_java_code(
    code: str,
    stdin: str,
    *,
    javac_command: str = "javac",
    java_command: str = "java",
    timeout_seconds: int = 5,
    compile_timeout_seconds: int = 10,
    max_code_bytes: int = 32 * 1024,
    max_stdin_bytes: int = 8 * 1024,
    max_output_bytes: int = 256 * 1024,
) -> JavaExecutionResult:
    _validate_source(code, max_code_bytes)
    if len(stdin.encode("utf-8")) > max_stdin_bytes:
        raise JavaRunnerError(
            f"标准输入不能超过 {max_stdin_bytes // 1024} KB。"
        )

    javac = _resolve_executable(javac_command)
    java = _resolve_executable(java_command)
    started_at = time.monotonic()

    with tempfile.TemporaryDirectory(prefix="gemma4-java-") as directory:
        workdir = Path(directory)
        source_path = workdir / "Main.java"
        source_path.write_text(code, encoding="utf-8")

        compiled, compile_output = _compile_source(
            javac,
            source_path,
            workdir,
            compile_timeout_seconds,
            max_output_bytes,
        )
        if not compiled:
            return JavaExecutionResult(
                success=False,
                output="",
                error="编译失败。",
                compile_output=compile_output,
                duration_ms=int((time.monotonic() - started_at) * 1000),
            )

        output, error, timed_out, output_exceeded = _run_process(
            [
                java,
                "-Xmx128m",
                "-Xss256k",
                "-Dfile.encoding=UTF-8",
                "-Djava.io.tmpdir=" + str(workdir),
                "-cp",
                str(workdir),
                "Main",
            ],
            workdir,
            stdin,
            timeout_seconds,
            max_output_bytes,
        )

    if timed_out:
        error = (
            f"程序运行超过 {timeout_seconds} 秒，已自动终止。"
            + (f"\n{error}" if error.strip() else "")
        )
    elif output_exceeded:
        error = (
            f"程序输出超过 {max_output_bytes // 1024} KB，已自动终止。"
            + (f"\n{error}" if error.strip() else "")
        )

    return JavaExecutionResult(
        success=not timed_out and not output_exceeded and not error.strip(),
        output=output,
        error=error,
        compile_output="",
        duration_ms=int((time.monotonic() - started_at) * 1000),
        timed_out=timed_out,
    )
