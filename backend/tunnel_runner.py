import subprocess
import re
import sys
import os
import time

def sync_tunnel_to_cloud(tunnel_url: str, root_dir: str):
    """Writes the active tunnel URL to live_tunnel.txt and pushes with [skip ci]."""
    try:
        live_file = os.path.join(root_dir, "live_tunnel.txt")
        with open(live_file, "w", encoding="utf-8") as f:
            f.write(tunnel_url.strip())
        
        print("\n[SYNC] Auto-syncing live tunnel URL to cloud...")
        subprocess.run(["git", "add", "live_tunnel.txt"], cwd=root_dir, capture_output=True, timeout=10)
        subprocess.run(
            ["git", "commit", "-m", f"chore(tunnel): sync live URL {tunnel_url} [skip ci]"],
            cwd=root_dir,
            capture_output=True,
            timeout=10
        )
        push_res = subprocess.run(["git", "push", "origin", "main"], cwd=root_dir, capture_output=True, text=True, timeout=20)
        if push_res.returncode == 0:
            print("[SYNC] ✅ Live URL synced! Anyone visiting https://course-pilot-eight.vercel.app connects automatically.")
        else:
            print(f"[SYNC] Warning: Git push exited with code {push_res.returncode}")
    except Exception as e:
        print(f"[SYNC] Sync error (non-fatal): {e}")

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cloudflared_exe = os.path.join(root_dir, "cloudflared.exe")

    if not os.path.exists(cloudflared_exe):
        print(f"[ERROR] cloudflared.exe was not found in: {root_dir}")
        input("Press Enter to exit...")
        sys.exit(1)

    print("=" * 70)
    print("           CoursePilot - Live Auto-Sync Cloudflare Tunnel")
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

                print("\n" + "=" * 70)
                print(" [SUCCESS] CoursePilot Cloudflare Tunnel is LIVE! (100% Free)")
                print("=" * 70)
                print(f"Backend Tunnel URL: {tunnel_url}\n")
                
                # Push to GitHub for 0-step auto-connection
                sync_tunnel_to_cloud(tunnel_url, root_dir)

                print("\n" + "-" * 70)
                print(" Share this clean link with anyone or open on your phone:")
                print(" 👉 https://course-pilot-eight.vercel.app")
                print("-" * 70)
                print("Keep this terminal window OPEN while CoursePilot is being used.")
                print("=" * 70 + "\n")
                sys.stdout.flush()

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
