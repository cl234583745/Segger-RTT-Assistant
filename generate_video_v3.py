#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RTT Assistant v1.2 介绍视频生成脚本 v3
丰富动画效果 + 图片展示
"""

import asyncio
import os
import math
from pathlib import Path
from moviepy import *
import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

# 配置
OUTPUT_DIR = Path("C:/Users/jerry/Desktop/rtt/video")
PROJECT_DIR = Path("C:/Users/jerry/Desktop/rtt")
OUTPUT_DIR.mkdir(exist_ok=True)

# 1080p分辨率（更快渲染）
WIDTH = 1920
HEIGHT = 1080
FPS = 30

# Edge TTS 中文男声
VOICE = "zh-CN-YunxiNeural"

# 加载截图
def load_screenshot(filename):
    path = PROJECT_DIR / filename
    if path.exists():
        return Image.open(path).convert("RGBA")
    return None

SEGGER_SCREENSHOT = load_screenshot("ScreenShot_segger rtt.png")
RTT_ASSISTANT_SCREENSHOT = load_screenshot("ScreenShot_rtt assistant.png")

# 脚本内容
SCRIPT_SECTIONS = [
    {
        "title": "RTT Assistant v1.2",
        "subtitle": "功能介绍",
        "content": "RTT Assistant是一款基于JLink RTT的MCU调试工具，通过SWD或JTAG接口实现PC与MCU的高效通信。",
        "type": "intro"
    },
    {
        "title": "核心功能",
        "content": "支持RTT通信、连接配置、数据收发、日志记录和配置保存。可通过USB或TCP IP连接JLink，支持多种MCU型号。",
        "type": "features"
    },
    {
        "title": "对比JLink RTT Viewer",
        "content": "左图是官方JLink RTT Viewer，右图是RTT Assistant。我们来看看它们的功能对比。",
        "type": "compare",
        "show_screenshots": True
    },
    {
        "title": "优势一：时间戳",
        "content": "精确记录数据收发时间，便于调试分析。这是JLink RTT Viewer没有的功能。",
        "type": "advantage"
    },
    {
        "title": "优势二：日志窗口",
        "content": "独立日志窗口，记录所有连接和通讯事件，支持类型过滤，问题排查更高效。",
        "type": "advantage"
    },
    {
        "title": "优势三：配置保存",
        "content": "自动保存设置，下次启动自动恢复，无需重复配置。",
        "type": "advantage"
    },
    {
        "title": "优势四：数据导出",
        "content": "一键导出接收数据到文件，方便分析和存档。",
        "type": "advantage"
    },
    {
        "title": "优势五：独立EXE",
        "content": "单EXE文件，无需安装Python环境，即开即用。",
        "type": "advantage"
    },
    {
        "title": "优势六：中文界面",
        "content": "全中文界面，操作简单直观，更适合国内开发者使用。",
        "type": "advantage"
    },
    {
        "title": "使用方法",
        "content": "双击EXE文件即可运行。配置连接参数后，即可进行数据收发。支持HEX和字符串显示模式。",
        "type": "usage"
    },
    {
        "title": "系统要求",
        "content": "Windows系统，JLink软件V930以上，MCU需要已移植RTT代码。",
        "type": "requirements"
    },
    {
        "title": "总结",
        "content": "RTT Assistant，让RTT调试更简单高效。欢迎下载使用！",
        "type": "conclusion"
    }
]


def ease_out_cubic(t):
    """缓出动画曲线"""
    return 1 - pow(1 - t, 3)


def ease_in_out_cubic(t):
    """缓入缓出动画曲线"""
    if t < 0.5:
        return 4 * t * t * t
    else:
        return 1 - pow(-2 * t + 2, 3) / 2


def create_gradient_background():
    """创建渐变背景"""
    img = Image.new('RGB', (WIDTH, HEIGHT))
    
    # 深色渐变背景
    for y in range(HEIGHT):
        # 从深蓝到深黑渐变
        ratio = y / HEIGHT
        r = int(10 * (1 - ratio))
        g = int(20 * (1 - ratio))
        b = int(40 * (1 - ratio))
        
        for x in range(WIDTH):
            img.putpixel((x, y), (r, g, b))
    
    return img


def add_glow_effect(img, radius=10):
    """添加发光效果"""
    glow = img.filter(ImageFilter.GaussianBlur(radius))
    return Image.blend(img, glow, 0.3)


def create_animated_frame(title, content, subtitle, progress, show_screenshots=False):
    """创建带动画的画面帧"""
    
    # 创建背景
    bg = create_gradient_background()
    draw = ImageDraw.Draw(bg)
    
    # 加载字体（1080p适配）
    try:
        title_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 100)
        content_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 50)
        subtitle_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 60)
    except:
        title_font = ImageFont.load_default()
        content_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
    
    # === 标题动画 ===
    # 标题从上方滑入 + 缩放效果
    title_progress = ease_out_cubic(min(1, progress * 3))
    title_offset_y = int((1 - title_progress) * 200)  # 从上方滑入
    title_scale = 0.8 + 0.2 * title_progress  # 缩放效果
    
    if title and progress > 0:
        # 计算标题位置
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (WIDTH - title_width) // 2
        title_y = HEIGHT // 5 + title_offset_y
        
        # 绘制标题（带渐变透明度）
        alpha = int(255 * title_progress)
        title_color = (alpha, alpha, alpha)
        draw.text((title_x, title_y), title, fill=title_color, font=title_font)
        
        # 标题下划线动画
        if progress > 0.3:
            line_progress = ease_out_cubic(min(1, (progress - 0.3) * 3))
            line_width = int(title_width * line_progress)
            line_x1 = (WIDTH - line_width) // 2
            line_x2 = line_x1 + line_width
            line_y = title_y + 180
            draw.line([(line_x1, line_y), (line_x2, line_y)], fill=(100, 150, 255), width=6)
    
    # === 副标题动画 ===
    if subtitle and progress > 0.1:
        sub_progress = ease_out_cubic(min(1, (progress - 0.1) * 3))
        sub_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        sub_width = sub_bbox[2] - sub_bbox[0]
        sub_x = (WIDTH - sub_width) // 2
        sub_y = HEIGHT // 5 + 200
        
        alpha = int(200 * sub_progress)
        draw.text((sub_x, sub_y), subtitle, fill=(alpha, alpha, alpha), font=subtitle_font)
    
    # === 内容动画 ===
    if content and progress > 0.3:
        content_progress = ease_out_cubic(min(1, (progress - 0.3) * 2))
        
        # 分行显示
        lines = []
        words = content
        max_chars_per_line = 28
        while words:
            if len(words) <= max_chars_per_line:
                lines.append(words)
                break
            else:
                lines.append(words[:max_chars_per_line])
                words = words[max_chars_per_line:]
        
        content_y = HEIGHT // 2 - 50
        for i, line in enumerate(lines):
            # 每行依次淡入
            line_delay = i * 0.1
            line_progress = ease_out_cubic(min(1, max(0, (progress - 0.3 - line_delay) * 3)))
            
            if line_progress > 0:
                line_bbox = draw.textbbox((0, 0), line, font=content_font)
                line_width = line_bbox[2] - line_bbox[0]
                line_x = (WIDTH - line_width) // 2
                
                alpha = int(240 * line_progress)
                # 从下方微微上移
                offset_y = int((1 - line_progress) * 30)
                draw.text((line_x, content_y + offset_y), line, fill=(alpha, alpha, alpha), font=content_font)
            
            content_y += 110
    
    # === 截图展示 ===
    if show_screenshots and progress > 0.5:
        screenshot_progress = ease_out_cubic(min(1, (progress - 0.5) * 2))
        
        # 缩放因子
        scale = 0.4 * screenshot_progress
        
        # 左侧截图 (SEGGER RTT Viewer)
        if SEGGER_SCREENSHOT:
            ss_width = int(SEGGER_SCREENSHOT.width * scale)
            ss_height = int(SEGGER_SCREENSHOT.height * scale)
            if ss_width > 0 and ss_height > 0:
                resized = SEGGER_SCREENSHOT.resize((ss_width, ss_height), Image.Resampling.LANCZOS)
                # 添加边框
                border = 4
                bordered = Image.new('RGBA', (ss_width + border*2, ss_height + border*2), (100, 100, 100, 255))
                bordered.paste(resized, (border, border), resized if resized.mode == 'RGBA' else None)
                # 位置（左侧）
                x = WIDTH // 4 - ss_width // 2
                y = HEIGHT - ss_height - 150 + int((1 - screenshot_progress) * 100)
                if bordered.mode == 'RGBA':
                    bg.paste(bordered, (x, y), bordered)
                else:
                    bg.paste(bordered, (x, y))
                
                # 标签
                label = "JLink RTT Viewer"
                label_bbox = draw.textbbox((0, 0), label, font=content_font)
                label_w = label_bbox[2] - label_bbox[0]
                draw.text((WIDTH // 4 - label_w // 2, y - 60), label, 
                         fill=(180, 180, 180), font=content_font)
        
        # 右侧截图 (RTT Assistant)
        if RTT_ASSISTANT_SCREENSHOT:
            ss_width = int(RTT_ASSISTANT_SCREENSHOT.width * scale)
            ss_height = int(RTT_ASSISTANT_SCREENSHOT.height * scale)
            if ss_width > 0 and ss_height > 0:
                resized = RTT_ASSISTANT_SCREENSHOT.resize((ss_width, ss_height), Image.Resampling.LANCZOS)
                border = 4
                bordered = Image.new('RGBA', (ss_width + border*2, ss_height + border*2), (100, 150, 200, 255))
                bordered.paste(resized, (border, border), resized if resized.mode == 'RGBA' else None)
                x = WIDTH * 3 // 4 - ss_width // 2
                y = HEIGHT - ss_height - 150 + int((1 - screenshot_progress) * 100)
                if bordered.mode == 'RGBA':
                    bg.paste(bordered, (x, y), bordered)
                else:
                    bg.paste(bordered, (x, y))
                
                label = "RTT Assistant"
                label_bbox = draw.textbbox((0, 0), label, font=content_font)
                label_w = label_bbox[2] - label_bbox[0]
                draw.text((WIDTH * 3 // 4 - label_w // 2, y - 60), label, 
                         fill=(100, 200, 255), font=content_font)
    
    # === 装饰粒子效果（简化版）===
    if progress > 0 and progress < 1:
        num_particles = 8  # 减少粒子数量
        for i in range(num_particles):
            angle = (i / num_particles) * 2 * math.pi + progress * math.pi
            radius = 400 + 100 * math.sin(progress * 4 + i)  # 缩小半径
            px = WIDTH // 2 + int(radius * math.cos(angle))
            py = HEIGHT // 2 + int(radius * math.sin(angle))
            
            if 0 < px < WIDTH and 0 < py < HEIGHT:
                alpha = int(30 * math.sin(progress * 2 + i))
                if alpha > 0:
                    size = 2
                    draw.ellipse([(px-size, py-size), (px+size, py+size)], 
                                fill=(alpha//2, alpha, alpha*2))
    
    return np.array(bg)


async def generate_section_audio(section, index):
    """生成音频"""
    text = section.get("title", "") + "。" + section.get("content", "")
    audio_path = OUTPUT_DIR / f"audio_{index:02d}.mp3"
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(str(audio_path))
    return audio_path


def get_audio_duration(audio_path):
    """获取音频时长"""
    import subprocess
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


async def main():
    print("=" * 50)
    print("RTT Assistant v1.2 介绍视频生成 v3")
    print("丰富动画效果 + 图片展示")
    print("=" * 50)
    
    # 1. 生成音频
    print("\n正在生成各片段音频...")
    audio_paths = []
    audio_durations = []
    
    for i, section in enumerate(SCRIPT_SECTIONS):
        audio_path = await generate_section_audio(section, i)
        duration = get_audio_duration(audio_path)
        audio_paths.append(audio_path)
        audio_durations.append(duration)
        print(f"  片段 {i+1}: {section.get('title')} - {duration:.1f}秒")
    
    # 2. 生成视频片段
    print("\n正在生成视频片段...")
    video_clips = []
    audio_clips = []
    
    for i, section in enumerate(SCRIPT_SECTIONS):
        duration = audio_durations[i]
        
        print(f"  生成片段 {i+1}/{len(SCRIPT_SECTIONS)}: {section.get('title')} ({duration:.1f}秒)")
        
        def make_frame(t, title=section.get("title", ""), 
                      content=section.get("content", ""),
                      subtitle=section.get("subtitle", ""),
                      show_ss=section.get("show_screenshots", False),
                      dur=duration):
            progress = t / dur if dur > 0 else 0
            return create_animated_frame(title, content, subtitle, progress, show_ss)
        
        video_clip = VideoClip(make_frame, duration=duration)
        video_clip = video_clip.with_fps(FPS)
        
        audio_clip = AudioFileClip(str(audio_paths[i]))
        
        video_clips.append(video_clip)
        audio_clips.append(audio_clip)
    
    # 3. 合并
    print("\n合并视频和音频片段...")
    final_video = concatenate_videoclips(video_clips)
    final_audio = concatenate_audioclips(audio_clips)
    final = final_video.with_audio(final_audio)
    
    # 4. 导出
    output_path = OUTPUT_DIR / "RTT-Assistant-v1.2-介绍.mp4"
    print(f"\n正在导出视频到: {output_path}")
    print("这可能需要几分钟时间...")
    
    final.write_videofile(
        str(output_path),
        fps=FPS,
        codec='libx264',
        audio_codec='aac',
        bitrate='10000k',
        threads=4,
        preset='medium'
    )
    
    # 清理
    final.close()
    final_video.close()
    for audio_path in audio_paths:
        audio_path.unlink(missing_ok=True)
    
    print("\n" + "=" * 50)
    print("视频生成完成！")
    print(f"输出路径: {output_path}")
    print(f"分辨率: {WIDTH}x{HEIGHT} (4K)")
    print(f"时长: {final.duration:.1f}秒")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
