"""
HarvestGrid: Automated 1080p Studio Demo Video Recorder
Generates natural TTS narration (en-US-AndrewNeural), renders synchronized in-DOM subtitle HUD,
and captures full interactive workflow on live production web console using Playwright.
"""

import os
import sys
import time
import json
import asyncio
import subprocess
from playwright.async_api import async_playwright

AUDIO_DIR = "/Users/naveen/Documents/antigravity/peaceful-fermi/harvestgrid/demo/audio"
VIDEO_DIR = "/Users/naveen/Documents/antigravity/peaceful-fermi/harvestgrid/demo"
os.makedirs(AUDIO_DIR, exist_ok=True)

VOICE = "en-US-AndrewNeural"

SCENES = [
    {
        "id": "scene1",
        "text": "Over 40 percent of donated fresh agricultural produce spoils in transit before reaching community food pantries. Introducing HarvestGrid, an open-source perishable food rescue logistics and shelf-life estimation engine engineered for the Hack Away Hunger challenge.",
        "action": "intro"
    },
    {
        "id": "scene2",
        "text": "HarvestGrid embeds an Arrhenius thermal decay kinetics model using Q10 temperature quotients. It simulates real-time shelf-life loss during transit across berries, leafy greens, dairy, and orchard fruits, preventing cold-chain breaches before they occur.",
        "action": "thermal_model"
    },
    {
        "id": "scene3",
        "text": "Our constrained Vehicle Routing Problem solver matches surplus agricultural donors with the highest-urgency pantries, dynamically weighting CDC Social Vulnerability Indices, current inventory deficits, and active refrigerated cargo capacities.",
        "action": "vrp_routing"
    },
    {
        "id": "scene4",
        "text": "The cyberdeck console provides an interactive vector route map, live temperature simulation sliders, real-time pantry urgency ledgers, and one-click offline driver manifests. Complete with a 100 percent deterministic test suite running in zero seconds.",
        "action": "console_telemetry"
    },
    {
        "id": "scene5",
        "text": "HarvestGrid turns perishable food rescue from guesswork into predictable engineering, maximizing meals delivered and cutting carbon emissions across Iowa communities.",
        "action": "conclusion"
    }
]

def generate_tts():
    print("[+] Generating TTS audio segments via edge-tts...")
    for i, s in enumerate(SCENES):
        audio_path = os.path.join(AUDIO_DIR, f"{s['id']}.mp3")
        cmd = ["edge-tts", "--voice", VOICE, "--text", s["text"], "--write-media", audio_path]
        subprocess.run(cmd, check=True)
        
        probe = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", audio_path
        ], capture_output=True, text=True, check=True)
        duration = float(probe.stdout.strip())
        s["duration"] = duration
        s["audio_path"] = audio_path
        print(f"  └─ Scene {i+1} duration: {duration:.2f}s")
    
    concat_list_path = os.path.join(AUDIO_DIR, "concat_list.txt")
    with open(concat_list_path, "w") as f:
        for s in SCENES:
            f.write(f"file '{s['audio_path']}'\n")
            
    full_audio = os.path.join(VIDEO_DIR, "full_narration.mp3")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list_path, "-c", "copy", full_audio
    ], check=True)
    
    total_dur = sum(s["duration"] for s in SCENES)
    print(f"[✔] Combined Narration Audio: {full_audio} ({total_dur:.2f}s)")
    return total_dur

async def record_video():
    total_duration = generate_tts()
    
    raw_video_dir = os.path.join(VIDEO_DIR, "raw_capture")
    os.makedirs(raw_video_dir, exist_ok=True)
    
    print("[+] Launching Playwright browser for 1080p recording...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=raw_video_dir,
            record_video_size={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        
        target_url = "https://harvestgrid-nine.vercel.app"
        print(f"[+] Navigating to {target_url}...")
        await page.goto(target_url, wait_until="networkidle")
        await asyncio.sleep(1.0)
        
        # Inject Subtitle HUD
        await page.evaluate("""
            const hud = document.createElement('div');
            hud.id = 'hud-subtitle-box';
            hud.style.position = 'fixed';
            hud.style.bottom = '24px';
            hud.style.left = '50%';
            hud.style.transform = 'translateX(-50%)';
            hud.style.backgroundColor = 'rgba(9, 14, 17, 0.92)';
            hud.style.border = '1px solid rgba(16, 185, 129, 0.5)';
            hud.style.borderRadius = '14px';
            hud.style.padding = '12px 28px';
            hud.style.color = '#e2e8f0';
            hud.style.fontFamily = "'Plus Jakarta Sans', sans-serif";
            hud.style.fontSize = '17px';
            hud.style.fontWeight = '600';
            hud.style.letterSpacing = '0.01em';
            hud.style.textAlign = 'center';
            hud.style.maxWidth = '880px';
            hud.style.zIndex = '999999';
            hud.style.boxShadow = '0 10px 35px rgba(0,0,0,0.8), 0 0 20px rgba(16,185,129,0.3)';
            hud.style.pointerEvents = 'none';
            hud.style.backdropFilter = 'blur(10px)';
            hud.innerHTML = "<span style='color: #10b981;'>HARVESTGRID</span> • Perishable Food Rescue Logistics Engine";
            document.body.appendChild(hud);
        """)

        # Execute synchronized scenes
        for idx, scene in enumerate(SCENES):
            print(f"[+] Executing Scene {idx+1}: {scene['id']} ({scene['duration']:.2f}s)...")
            
            text_escaped = scene["text"].replace("'", "\\'").replace('"', '\\"')
            await page.evaluate(f"""
                document.getElementById('hud-subtitle-box').innerHTML = "{text_escaped}";
            """)
            
            dur = scene["duration"]
            
            if scene["action"] == "intro":
                await asyncio.sleep(dur * 0.3)
                await page.evaluate("window.scrollTo({top: 100, behavior: 'smooth'})")
                await asyncio.sleep(dur * 0.7)
                
            elif scene["action"] == "thermal_model":
                # Adjust temperature slider via dispatchEvent
                await page.evaluate("""
                    const slider = document.getElementById('temp-slider');
                    if (slider) {
                        slider.value = '32';
                        slider.dispatchEvent(new Event('input'));
                    }
                """)
                await asyncio.sleep(dur * 0.5)
                # Toggle reefer
                await page.evaluate("""
                    const reefer = document.getElementById('toggle-reefer');
                    if (reefer) {
                        reefer.checked = false;
                        reefer.dispatchEvent(new Event('change'));
                    }
                """)
                await asyncio.sleep(dur * 0.5)
                
            elif scene["action"] == "vrp_routing":
                # Optimize dispatch
                await page.click("#btn-dispatch")
                await asyncio.sleep(1.5)
                await page.click("#btn-step")
                await asyncio.sleep(dur - 2.0)
                
            elif scene["action"] == "console_telemetry":
                # Switch to Ames corridor
                await page.click("#btn-reg-ames")
                await asyncio.sleep(1.2)
                await page.click("#btn-dispatch")
                await asyncio.sleep(1.5)
                # Switch to Eastern corridor
                await page.click("#btn-reg-eastern")
                await asyncio.sleep(dur - 3.5)
                
            elif scene["action"] == "conclusion":
                await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
                await asyncio.sleep(dur)
        
        await asyncio.sleep(1.0)
        video_path = await page.video.path()
        await context.close()
        await browser.close()
        
    print(f"[✔] Raw Web Video captured at: {video_path}")
    
    final_output = os.path.join(VIDEO_DIR, "harvestgrid_demo.mp4")
    full_audio = os.path.join(VIDEO_DIR, "full_narration.mp3")
    
    print(f"[+] Merging 1080p video with AAC audio into {final_output}...")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", full_audio,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "slow",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        final_output
    ], check=True)
    
    print(f"[✔] FINAL 1080P DEMO VIDEO READY: {final_output}")

if __name__ == "__main__":
    asyncio.run(record_video())
