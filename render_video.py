#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RTT Assistant v1.2 视频渲染脚本
使用已有音频，只渲染画面
"""

import math
from pathlib import Path
from moviepy import *
from PIL import Image, ImageDraw, ImageFont
import numpy as np

OUTPUT_DIR = Path("C:/Users/jerry/Desktop/rtt/video")
PROJECT_DIR = Path("C:/Users/jerry/Desktop/rtt")

WIDTH = 1920
HEIGHT = 1080
FPS = 30

# 加载截图
def load_screenshot(filename):
    path = PROJECT_DIR / filename
    if path.exists():
        return Image.open(path).convert("RGBA")
    return None

SEGGER_SCREENSHOT = load_screenshot("ScreenShot_segger rtt.png")
RTT_ASSISTANT_SCREENSHOT = load_screenshot("ScreenShot_rtt assistant.png")

SCRIPT_SECTIONS = [
    {"title": "RTT Assistant v1.2", "subtitle": "功能介绍", "content": "RTT Assistant是一款基于JLink RTT的MCU调试工具，通过SWD或JTAG接口实现PC与MCU的高效通信。"},
    {"title": "核心功能", "content": "支持RTT通信、连接配置、数据收发、日志记录和配置保存。可通过USB或TCP IP连接JLink，支持多种MCU型号。"},
    {"title": "对比JLink RTT Viewer", "content": "左图是官方JLink RTT Viewer，右图是RTT Assistant。我们来看看它们的功能对比。", "show_screenshots": True},
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


def ease_out_cubic(t):
    return 1 - pow(1 - t, 3)


def create_gradient_background():
    img = Image.new('RGB', (WIDTH, HEIGHT))
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(10 * (1 - ratio))
        g = int(20 * (1 - ratio))
        b = int(40 * (1 - ratio))
        for x in range(WIDTH):
            img.putpixel((x, y), (r, g, b))
    return img


def create_animated_frame(title, content, subtitle, progress, show_screenshots=False):
    bg = create_gradient_background()
    draw = ImageDraw.Draw(bg)
    
    try:
        title_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 100)
        content_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 50)
        subtitle_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 60)
    except:
        title_font = content_font = subtitle_font = ImageFont.load_default()
    
    # 标题动画
    title_progress = ease_out_cubic(min(1, progress * 3))
    title_offset_y = int((1 - title_progress) * 200)
    
    if title and progress > 0:
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (WIDTH - title_width) // 2
        title_y = HEIGHT // 5 + title_offset_y
        alpha = int(255 * title_progress)
        draw.text((title_x, title_y), title, fill=(alpha, alpha, alpha), font=title_font)
        
        if progress > 0.3:
            line_progress = ease_out_cubic(min(1, (progress - 0.3) * 3))
            line_width = int(title_width * line_progress)
            line_x1 = (WIDTH - line_width) // 2
            line_x2 = line_x1 + line_width
            line_y = title_y + 120
            draw.line([(line_x1, line_y), (line_x2, line_y)], fill=(100, 150, 255), width=4)
    
    # 副标题
    if subtitle and progress > 0.1:
        sub_progress = ease_out_cubic(min(1, (progress - 0.1) * 3))
        sub_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        sub_width = sub_bbox[2] - sub_bbox[0]
        sub_x = (WIDTH - sub_width) // 2
        sub_y = HEIGHT // 5 + 140
        alpha = int(200 * sub_progress)
        draw.text((sub_x, sub_y), subtitle, fill=(alpha, alpha, alpha), font=subtitle_font)
    
    # 内容
    if content and progress > 0.3:
        lines = []
        words = content
        max_chars = 28
        while words:
            if len(words) <= max_chars:
                lines.append(words)
                break
            lines.append(words[:max_chars])
            words = words[max_chars:]
        
        content_y = HEIGHT // 2 - 50
        for i, line in enumerate(lines):
            line_delay = i * 0.1
            line_progress = ease_out_cubic(min(1, max(0, (progress - 0.3 - line_delay) * 3)))
            if line_progress > 0:
                line_bbox = draw.textbbox((0, 0), line, font=content_font)
                line_width = line_bbox[2] - line_bbox[0]
                line_x = (WIDTH - line_width) // 2
                alpha = int(240 * line_progress)
                offset_y = int((1 - line_progress) * 30)
                draw.text((line_x, content_y + offset_y), line, fill=(alpha, alpha, alpha), font=content_font)
            content_y += 80
    
    # 截图展示
    if show_screenshots and progress > 0.5:
        ss_progress = ease_out_cubic(min(1, (progress - 0.5) * 2))
        scale = 0.35 * ss_progress
        
        if SEGGER_SCREENSHOT:
            ss_w = int(SEGGER_SCREENSHOT.width * scale)
            ss_h = int(SEGGER_SCREENSHOT.height * scale)
            if ss_w > 0 and ss_h > 0:
                resized = SEGGER_SCREENSHOT.resize((ss_w, ss_h), Image.Resampling.LANCZOS)
                border = 3
                bordered = Image.new('RGBA', (ss_w + border*2, ss_h + border*2), (100, 100, 100, 255))
                bordered.paste(resized, (border, border), resized)
                x = WIDTH // 4 - ss_w // 2
                y = HEIGHT - ss_h - 100 + int((1 - ss_progress) * 80)
                bg.paste(bordered, (x, y), bordered)
                label = "JLink RTT Viewer"
                label_bbox = draw.textbbox((0, 0), label, font=content_font)
                label_w = label_bbox[2] - label_bbox[0]
                draw.text((WIDTH // 4 - label_w // 2, y - 50), label, fill=(180, 180, 180), font=content_font)
        
        if RTT_ASSISTANT_SCREENSHOT:
            ss_w = int(RTT_ASSISTANT_SCREENSHOT.width * scale)
            ss_h = int(RTT_ASSISTANT_SCREENSHOT.height * scale)
            if ss_w > 0 and ss_h > 0:
                resized = RTT_ASSISTANT_SCREENSHOT.resize((ss_w, ss_h), Image.Resampling.LANCZOS)
                border = 3
                bordered = Image.new('RGBA', (ss_w + border*2, ss_h + border*2), (100, 150, 200, 255))
                bordered.paste(resized, (border, border), resized)
                x = WIDTH * 3 // 4 - ss_w // 2
                y = HEIGHT - ss_h - 100 + int((1 - ss_progress) * 80)
                bg.paste(bordered, (x, y), bordered)
                label = "RTT Assistant"
                label_bbox = draw.textbbox((0, 0), label, font=content_font)
                label_w = label_bbox[2] - label_bbox[0]
                draw.text((WIDTH * 3 // 4 - label_w // 2, y - 50), label, fill=(100, 200, 255), font=content_font)
    
    # 粒子效果
    if 0 < progress < 1:
        for i in range(8):
            angle = (i / 8) * 2 * math.pi + progress * math.pi
            radius = 300 + 80 * math.sin(progress * 4 + i)
            px = WIDTH // 2 + int(radius * math.cos(angle))
            py = HEIGHT // 2 + int(radius * math.sin(angle))
            if 0 < px < WIDTH and 0 < py < HEIGHT:
                alpha = int(30 * math.sin(progress * 2 + i))
                if alpha > 0:
                    draw.ellipse([(px-2, py-2), (px+2, py+2)], fill=(alpha//2, alpha, alpha*2))
    
    return np.array(bg)


def get_audio_duration(audio_path):
    import subprocess
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def main():
    print("=" * 50)
    print("RTT Assistant v1.2 视频渲染")
    print("使用已有音频文件")
    print("=" * 50)
    
    # 加载音频
    print("\n加载音频文件...")
    audio_paths = []
    audio_durations = []
    
    for i in range(12):
        audio_path = OUTPUT_DIR / f"audio_{i:02d}.mp3"
        if audio_path.exists() and audio_path.stat().st_size > 0:
            duration = get_audio_duration(audio_path)
            audio_paths.append(audio_path)
            audio_durations.append(duration)
            print(f"  片段 {i+1}: {duration:.1f}秒")
        else:
            print(f"  片段 {i+1}: 音频不存在!")
            return
    
    # 生成视频片段
    print("\n生成视频片段...")
    video_clips = []
    audio_clips = []
    
    for i, section in enumerate(SCRIPT_SECTIONS):
        duration = audio_durations[i]
        print(f"  片段 {i+1}/{len(SCRIPT_SECTIONS)}: {section['title']} ({duration:.1f}秒)")
        
        def make_frame(t, title=section.get("title", ""), 
                      content=section.get("content", ""),
                      subtitle=section.get("subtitle", ""),
                      show_ss=section.get("show_screenshots", False),
                      dur=duration):
            progress = t / dur if dur > 0 else 0
            return create_animated_frame(title, content, subtitle, progress, show_ss)
        
        video_clip = VideoClip(make_frame, duration=duration).with_fps(FPS)
        audio_clip = AudioFileClip(str(audio_paths[i]))
        video_clips.append(video_clip)
        audio_clips.append(audio_clip)
    
    # 合并
    print("\n合并视频和音频...")
    final_video = concatenate_videoclips(video_clips)
    final_audio = concatenate_audioclips(audio_clips)
    final = final_video.with_audio(final_audio)
    
    # 导出
    output_path = OUTPUT_DIR / "RTT-Assistant-v1.2-介绍.mp4"
    print(f"\n导出视频到: {output_path}")
    
    final.write_videofile(
        str(output_path),
        fps=FPS,
        codec='libx264',
        audio_codec='aac',
        bitrate='8000k',
        threads=4,
        preset='medium'
    )
    
    final.close()
    final_video.close()
    
    print("\n" + "=" * 50)
    print("视频生成完成！")
    print(f"输出: {output_path}")
    print(f"分辨率: {WIDTH}x{HEIGHT}")
    print(f"时长: {final.duration:.1f}秒")
    print("=" * 50)


if __name__ == "__main__":
    main()
