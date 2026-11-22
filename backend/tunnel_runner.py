import subprocess
import re
import sys
import os

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cloudflared_exe = os.path.join(root_dir, "cloudflared.exe")

    if not os.path.exists(cloudflared_exe):
        print(f"[ERROR] cloudflared.exe was not found in: {root_dir}")
        input("Press Enter to exit...")
        sys.exit(1)

    print("=" * 70)
    print("           CoursePilot - Cloudflare Public Tunnel")
    print("=" * 70)
    print("Starting tunnel for http://127.0.0.1:8000 ...")
    print("Connecting to Cloudflare global network...\n")

    proc = subprocess.Popen(
        [cloudflared_exe, "tunnel", "--url", "http://127.0.0.1:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace"
    )

    url_regex = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
    found_tunnel = False

    try:
        for line in iter(proc.stdout.readline, ""):
            match = url_regex.search(line)
            if match and not found_tunnel:
                tunnel_url = match.group(0)
                found_tunnel = True
                share_url = f"https://course-pilot-eight.vercel.app/?server={tunnel_url}"

                print("\n" + "=" * 70)
                print(" [SUCCESS] CoursePilot Cloudflare Tunnel is LIVE! (100% Free)")
                print("=" * 70)
                print(f"\n1. Direct Backend Tunnel:\n   {tunnel_url}\n")
                print("2. 1-Click Link for Friends / Mobile (Opens Vercel & auto-connects):")
                print(f"   👉 {share_url}\n")
                print("Keep this terminal window OPEN while you or your friends use CoursePilot.")
                print("=" * 70 + "\n")
                sys.stdout.flush()

                # Try copying share_url to clipboard on Windows
                try:
                    subprocess.run(
                        ["powershell", "-NoProfile", "-Command", f"Set-Clipboard -Value '{share_url}'"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=2
                    )
                    print("[INFO] Link copied to your clipboard! You can paste and send directly.\n")
                except Exception:
                    pass

            # Print relevant status messages
            line_str = line.strip()
            if any(k in line_str for k in ["Registered tunnel", "Connection", "Updated", "ERR"]):
                print(line_str)
                sys.stdout.flush()

    except KeyboardInterrupt:
        print("\nStopping tunnel...")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    main()
