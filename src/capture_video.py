#!/usr/bin/env python3
"""
Frame-step the vertical capture page in headless Chromium and stitch to an MP4
for Instagram / TikTok.

  ./venv/bin/python src/capture_video.py [--seconds 20] [--fps 30] [--out docs/leba-48h-clip.mp4]

Requires: playwright (+ chromium), ffmpeg on PATH.
The map view is fixed, so tiles load once up front -> deterministic capture.
"""

import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP_HTML = os.path.join(ROOT, "docs", "leba-48h-capture.html")
W, H = 1080, 1920


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=20.0, help="clip length")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "leba-48h-clip.mp4"))
    ap.add_argument("--hold", type=float, default=1.2, help="seconds to hold on the final frame")
    args = ap.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found on PATH")
    if not os.path.exists(CAP_HTML):
        sys.exit(f"missing {CAP_HTML} — run src/generate_leba48_capture.py first")

    from playwright.sync_api import sync_playwright

    frames_dir = os.path.join(ROOT, "docs", "_frames")
    if os.path.exists(frames_dir):
        shutil.rmtree(frames_dir)
    os.makedirs(frames_dir)

    n_frames = int(args.seconds * args.fps)
    hold_frames = int(args.hold * args.fps)
    print(f"Rendering {n_frames} frames (+{hold_frames} hold) at {W}x{H}...")

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb", "--hide-scrollbars"])
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        page.goto("file://" + CAP_HTML)
        # wait for CAP + tiles
        page.wait_for_function("window.CAP && window.CAP.T0 !== undefined", timeout=30000)
        try:
            page.wait_for_function("window.CAP.ready === true", timeout=20000)
        except Exception:
            print("  (tile 'load' not signalled — continuing after grace period)")
        page.wait_for_timeout(2500)  # let all tiles settle

        T0 = page.evaluate("window.CAP.T0")
        SPAN = page.evaluate("window.CAP.SPAN")

        for i in range(n_frames):
            f = i / (n_frames - 1)
            t = T0 + f * SPAN
            page.evaluate("(t) => window.CAP.renderAt(t)", t)
            # follow-camera moves each frame -> wait for newly requested tiles
            try:
                page.wait_for_function("window.CAP.tilesPending() === 0", timeout=6000)
            except Exception:
                pass
            page.wait_for_timeout(30)  # let canvas/DOM paint
            page.screenshot(path=os.path.join(frames_dir, f"f{i:05d}.png"))
            if i % 30 == 0:
                print(f"  frame {i}/{n_frames}")

        # hold just past the finish so the winner headline (both boats in) shows
        page.evaluate("(t) => window.CAP.renderAt(t)", T0 + SPAN + 120)
        try:
            page.wait_for_function("window.CAP.tilesPending() === 0", timeout=6000)
        except Exception:
            pass
        page.wait_for_timeout(50)
        for k in range(hold_frames):
            page.screenshot(path=os.path.join(frames_dir, f"f{n_frames + k:05d}.png"))

        browser.close()

    print("Encoding with ffmpeg...")
    cmd = [
        "ffmpeg", "-y", "-framerate", str(args.fps),
        "-i", os.path.join(frames_dir, "f%05d.png"),
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        args.out,
    ]
    subprocess.run(cmd, check=True)
    shutil.rmtree(frames_dir)
    size = os.path.getsize(args.out) / 1024 / 1024
    print(f"\nDone -> {args.out}  ({size:.1f} MB, {W}x{H}, {args.fps}fps)")


if __name__ == "__main__":
    main()
