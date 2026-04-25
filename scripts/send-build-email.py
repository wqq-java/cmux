#!/usr/bin/env python3
"""Send a build-status email for the cmux self-build pipeline.

Reads everything from environment variables (set by the workflow step):
  SMTP_USER, SMTP_PASS, TO_ADDR  - Gmail SMTP credentials
  JOB_STATUS                     - 'success' / 'failure' / 'cancelled'
  GHOSTTY_SHORT                  - short ghostty SHA tag
  RUN_URL                        - GitHub Actions run page URL
  ARTIFACT_URL                   - per-run artifact download URL (signed)
  REPO                           - "owner/repo" (for failure-mode link)
"""
import os
import smtplib
import ssl
import sys
from email.header import Header
from email.mime.text import MIMEText


def build_subject_and_body() -> tuple[str, str]:
    status = os.environ.get("JOB_STATUS", "unknown")
    sha = os.environ.get("GHOSTTY_SHORT", "?")
    run_url = os.environ.get("RUN_URL", "?")
    artifact_url = os.environ.get("ARTIFACT_URL", "")
    repo = os.environ.get("REPO", "")

    one_liner = (
        "cd ~/Downloads && osascript -e 'quit app \"cmux\"' 2>/dev/null; "
        "sleep 2; rm -rf /Applications/cmux.app && "
        "unzip -o cmux-selfbuild-arm64*.zip && "
        "mv cmux.app /Applications/ && "
        "xattr -dr com.apple.quarantine /Applications/cmux.app && "
        "open /Applications/cmux.app"
    )

    if status == "success":
        subject = f"✅ cmux 自编版就绪 · ghostty {sha}"
        lines = [
            "本次 cmux 自编版构建完成。",
            "",
            f"Ghostty SHA: {sha}",
            f"GitHub Actions Run: {run_url}",
            f"Artifact 直链 (登录 GitHub 后可点): {artifact_url}",
            "",
            "下载方式 (二选一):",
            "  A. 浏览器登录 wqq-java 后直接点上面 Artifact 直链",
            "  B. 打开 Run URL → 滚到底部 Artifacts 区 → 点 zip",
            "",
            "下载到 ~/Downloads/ 之后, 终端运行:",
            one_liner,
            "",
            "--",
            "本邮件由 GitHub Actions 自动发送 (workflow 调 Gmail SMTP)",
            "下次构建: 每周一 10:00 Asia/Shanghai (由 Claude Code routine 触发)",
        ]
    else:
        subject = "❌ cmux 自编版构建失败"
        lines = [
            f"本次 cmux 自编版构建失败 (job.status={status})。",
            "",
            f"Run URL (点开看哪一步挂了): {run_url}",
            f"Ghostty SHA: {sha}",
            "",
            "排查:",
            "  - 大概率是 manaflow upstream 刚合了破坏性改动",
            "  - 也可能 Xcode runner image 升级了 SDK 不兼容",
            "  - 等 1-2 天 manaflow 那边修了再手动重跑通常就好",
            "",
            f"立即重跑: https://github.com/{repo}/actions/workflows/my-build.yml",
        ]

    return subject, "\n".join(lines)


def main() -> int:
    subject, body = build_subject_and_body()
    smtp_user = os.environ["SMTP_USER"]
    smtp_pass = os.environ["SMTP_PASS"].replace(" ", "")
    to_addr = os.environ["TO_ADDR"]

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = smtp_user
    msg["To"] = to_addr

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as s:
            s.starttls(context=ctx)
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_user, [to_addr], msg.as_string())
        print(f"email sent OK -> {to_addr}: {subject}")
        return 0
    except Exception as e:
        print(f"email FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
