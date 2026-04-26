#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RTT Assistant v1.2 视频渲染脚本 - 简化版
使用静态图片拼接，渲染速度快
"""

import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

OUTPUT_DIR = Path("C:/Users/jerry/Desktop/rtt/video")
PROJECT_DIR = Path("C:/Users/jerry/Desktop/rtt")
TEMP_DIR = OUTPUT_DIR / "temp"

WIDTH = 1920
HEIGHT = 1080

TEMP_DIR.mkdir(exist_ok=True)

def get_audio_duration(audio_path):
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())

def create_frame(title, content, subtitle="", show_screenshots=False):
    img = Image.new('RGB', (WIDTH, HEIGHT), (10, 15, 25))
    draw = ImageDraw.Draw(img)
    
    try:
        title_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 90)
        content_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 48)
        subtitle_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 55)
    except:
        title_font = content_font = subtitle_font = ImageFont.load_default()
    
    if title:
        bbox = draw.textbbox((0, 0), title, font=title_font)
        w = bbox[2] - bbox[0]
        x = (WIDTH - w) // 2
        y = HEIGHT // 5
        draw.text((x, y), title, fill=(255, 255, 255), font=title_font)
        draw.line([(x, y + 110), (x + w, y + 110)], fill=(100, 150, 255), width=3)
    
    if subtitle:
        bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        w = bbox[2] - bbox[0]
        x = (WIDTH - w) // 2
        draw.text((x, HEIGHT // 5 + 130), subtitle, fill=(200, 200, 200), font=subtitle_font)
    
    if content:
        lines = []
        words = content
        max_chars = 28
        while words:
            if len(words) <= max_chars:
                lines.append(words)
                break
            lines.append(words[:max_chars])
            words = words[max_chars:]
        
        y = HEIGHT // 2 - 30
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=content_font)
            w = bbox[2] - bbox[0]
            x = (WIDTH - w) // 2
            draw.text((x, y), line, fill=(240, 240, 240), font=content_font)
            y += 75
    
    if show_screenshots:
        top_y = HEIGHT // 4 - 30
        
        for i, (filename, label, color) in enumerate([
            ("ScreenShot_segger rtt.png", "JLink RTT Viewer", (100, 100, 100)),
            ("ScreenShot_rtt assistant.png", "RTT Assistant", (100, 150, 200))
        ]):
            ss_path = PROJECT_DIR / filename
            if ss_path.exists():
                ss = Image.open(ss_path).convert("RGB")
                scale = 0.95
                new_w = int(ss.width * scale)
                new_h = int(ss.height * scale)
                ss = ss.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                bordered = Image.new('RGB', (new_w + 12, new_h + 12), color)
                bordered.paste(ss, (6, 6))
                
                if i == 0:
                    x = WIDTH // 4 - new_w // 2
                else:
                    x = WIDTH * 3 // 4 - new_w // 2
                y = HEIGHT // 2 - new_h // 2 + 50
                img.paste(bordered, (x, y))
                
                label_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 60) if Path("C:/Windows/Fonts/msyh.ttc").exists() else content_font
                bbox = draw.textbbox((0, 0), label, font=label_font)
                lw = bbox[2] - bbox[0]
                pos_x = WIDTH // 4 if i == 0 else WIDTH * 3 // 4
                draw.text((pos_x - lw // 2, y - 70), label, fill=(255, 255, 255), font=label_font)
    
    return img

SCRIPT_SECTIONS = [
    {"title": "RTT Assistant v1.2", "subtitle": "功能介绍", "content": "RTT Assistant是一款基于JLink RTT的MCU调试工具，通过SWD或JTAG接口实现PC与MCU的高效通信。"},
    {"title": "核心功能", "content": "支持RTT通信、连接配置、数据收发、日志记录和配置保存。可通过USB或TCP IP连接JLink，支持多种MCU型号。"},
    {"title": "对比JLink RTT Viewer", "content": "左边是官方工具，右边是RTT Assistant。", "show_screenshots": True},
    {"title": "优势一：时间戳", "content": "精确记录数据收发时间，便于调试分析。这是JLink RTT Viewer没有的功能。"},
    {"title": "优势二：日志窗口", "content": "独立日志窗口，记录所有连接和通讯事件，支持类型过滤，问题排查更高效。"},
    {"title": "优势三：配置保存", "content": "自动保存设置，下次启动自动恢复，无需重复配置。"},
    {"title": "优势四：数据导出", "content": "一键导出接收数据到文件，方便分析和存档。"},
    {"title": "优势五：独立EXE", "content": "单EXE文件，无需安装Python环境，即开即用。"},
    {"title": "优势六：中文界面", "content": "全中文界面，操作简单直观，更适合国内开发者使用。"},
    {"title": "使用方法", "content": "双击EXE文件即可运行。配置连接参数后，即可进行数据收发。支持HEX和字符串显示模式。"},
    {"title": "系统要求", "content": "Windows系统，JLink软件V930以上，MCU需要已移植RTT代码。"},
    {"title": "总结", "content": "RTT Assistant，让RTT调试更简单高效。欢迎下载使用！"}
]

def main():
    print("=" * 50)
    print("RTT Assistant v1.2 视频渲染（简化版）")
    print("=" * 50)
    
    segments = []
    
    for i, section in enumerate(SCRIPT_SECTIONS):
        audio_path = OUTPUT_DIR / f"audio_{i:02d}.mp3"
        if not audio_path.exists():
            print(f"错误: 音频文件 {audio_path} 不存在")
            return
        
        duration = get_audio_duration(audio_path)
        print(f"处理片段 {i+1}/{len(SCRIPT_SECTIONS)}: {section['title']} ({duration:.1f}秒)")
        
        frame = create_frame(
            section.get("title", ""),
            section.get("content", ""),
            section.get("subtitle", ""),
            section.get("show_screenshots", False)
        )
        
        frame_path = TEMP_DIR / f"frame_{i:02d}.png"
        frame.save(frame_path)
        
        segments.append({
            "frame": frame_path,
            "audio": audio_path,
            "duration": duration
        })
    
    print("\n合并视频片段...")
    
    concat_file = TEMP_DIR / "concat.txt"
    with open(concat_file, "w") as f:
        for i, seg in enumerate(segments):
            segment_path = TEMP_DIR / f"segment_{i:02d}.mp4"
            
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", str(seg["frame"]),
                "-i", str(seg["audio"]),
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-shortest",
                "-t", str(seg["duration"]),
                str(segment_path)
            ]
            
            subprocess.run(cmd, capture_output=True)
            f.write(f"file '{segment_path.name}'\n")
    
    output_path = OUTPUT_DIR / "RTT-Assistant-v1.2-介绍.mp4"
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output_path)
    ]
    
    print("生成最终视频...")
    subprocess.run(cmd, capture_output=True)
    
    import shutil
    shutil.rmtree(TEMP_DIR)
    
    total_duration = sum(s["duration"] for s in segments)
    print("\n" + "=" * 50)
    print("视频生成完成！")
    print(f"输出: {output_path}")
    print(f"分辨率: {WIDTH}x{HEIGHT}")
    print(f"时长: {total_duration:.1f}秒")
    print("=" * 50)

if __name__ == "__main__":
    main()
