#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RTT Assistant v1.2 介绍视频生成脚本 v2
为每个片段单独生成音频，确保画面与音频同步
"""

import asyncio
import os
import re
from pathlib import Path
from moviepy import *
import edge_tts
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# 配置
OUTPUT_DIR = Path("C:/Users/jerry/Desktop/rtt/video")
OUTPUT_DIR.mkdir(exist_ok=True)

# 4K分辨率
WIDTH = 3840
HEIGHT = 2160
FPS = 30

# Edge TTS 中文男声（大学生声音）
VOICE = "zh-CN-YunxiNeural"

# 脚本内容（每段单独处理）
SCRIPT_SECTIONS = [
    {
        "title": "RTT Assistant v1.2",
        "subtitle": "功能介绍",
        "content": "RTT Assistant是一款基于JLink RTT的MCU调试工具，通过SWD或JTAG接口实现PC与MCU的高效通信。"
    },
    {
        "title": "核心功能",
        "content": "支持RTT通信、连接配置、数据收发、日志记录和配置保存。可通过USB或TCP IP连接JLink，支持多种MCU型号。"
    },
    {
        "title": "对比JLink RTT Viewer",
        "content": "相比官方的JLink RTT Viewer，RTT Assistant有六大优势：时间戳显示、日志窗口、配置保存、数据导出、独立EXE、中文界面。"
    },
    {
        "title": "优势一：时间戳",
        "content": "精确记录数据收发时间，便于调试分析。这是JLink RTT Viewer没有的功能。"
    },
    {
        "title": "优势二：日志窗口",
        "content": "独立日志窗口，记录所有连接和通讯事件，支持类型过滤，问题排查更高效。"
    },
    {
        "title": "优势三：配置保存",
        "content": "自动保存设置，下次启动自动恢复，无需重复配置。"
    },
    {
        "title": "优势四：数据导出",
        "content": "一键导出接收数据到文件，方便分析和存档。"
    },
    {
        "title": "优势五：独立EXE",
        "content": "单EXE文件，无需安装Python环境，即开即用。"
    },
    {
        "title": "优势六：中文界面",
        "content": "全中文界面，操作简单直观，更适合国内开发者使用。"
    },
    {
        "title": "使用方法",
        "content": "双击EXE文件即可运行。配置连接参数后，即可进行数据收发。支持HEX和字符串显示模式。"
    },
    {
        "title": "系统要求",
        "content": "Windows系统，JLink软件V930以上，MCU需要已移植RTT代码。"
    },
    {
        "title": "总结",
        "content": "RTT Assistant，让RTT调试更简单高效。欢迎下载使用！"
    }
]


async def generate_section_audio(section, index):
    """为单个片段生成音频"""
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


def create_text_frame(title, content, subtitle, frame_num, total_frames):
    """创建带文字的画面帧"""
    img = Image.new('RGB', (WIDTH, HEIGHT), color='black')
    draw = ImageDraw.Draw(img)
    
    try:
        title_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 140)
        content_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 90)
        subtitle_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 100)
    except:
        title_font = ImageFont.load_default()
        content_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
    
    progress = frame_num / total_frames if total_frames > 0 else 0
    
    # 淡入淡出效果
    if frame_num < 15:
        alpha = frame_num / 15
    elif frame_num > total_frames - 15:
        alpha = (total_frames - frame_num) / 15
    else:
        alpha = 1.0
    
    # 绘制标题
    if title:
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (WIDTH - title_width) // 2
        title_y = HEIGHT // 4
        
        title_color = (int(255 * alpha), int(255 * alpha), int(255 * alpha))
        draw.text((title_x, title_y), title, fill=title_color, font=title_font)
    
    # 绘制副标题
    if subtitle:
        sub_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        sub_width = sub_bbox[2] - sub_bbox[0]
        sub_x = (WIDTH - sub_width) // 2
        sub_y = HEIGHT // 4 + 180
        
        sub_color = (int(180 * alpha), int(180 * alpha), int(180 * alpha))
        draw.text((sub_x, sub_y), subtitle, fill=sub_color, font=subtitle_font)
    
    # 绘制内容（打字机效果）
    if content:
        chars_to_show = int(len(content) * min(1.0, progress * 1.2))
        visible_content = content[:chars_to_show]
        
        lines = []
        words = visible_content
        max_chars_per_line = 30
        while words:
            if len(words) <= max_chars_per_line:
                lines.append(words)
                break
            else:
                lines.append(words[:max_chars_per_line])
                words = words[max_chars_per_line:]
        
        content_y = HEIGHT // 2
        for line in lines:
            line_bbox = draw.textbbox((0, 0), line, font=content_font)
            line_width = line_bbox[2] - line_bbox[0]
            line_x = (WIDTH - line_width) // 2
            content_color = (int(240 * alpha), int(240 * alpha), int(240 * alpha))
            draw.text((line_x, content_y), line, fill=content_color, font=content_font)
            content_y += 120
    
    return np.array(img)


async def main():
    """主函数"""
    print("=" * 50)
    print("RTT Assistant v1.2 介绍视频生成 v2")
    print("=" * 50)
    
    # 1. 为每个片段生成音频
    print("正在生成各片段音频...")
    audio_paths = []
    audio_durations = []
    
    for i, section in enumerate(SCRIPT_SECTIONS):
        audio_path = await generate_section_audio(section, i)
        duration = get_audio_duration(audio_path)
        audio_paths.append(audio_path)
        audio_durations.append(duration)
        print(f"  片段 {i+1}: {section.get('title')} - {duration:.1f}秒")
    
    # 2. 生成视频片段（时长匹配音频）
    print("\n正在生成视频片段...")
    video_clips = []
    audio_clips = []
    
    for i, section in enumerate(SCRIPT_SECTIONS):
        duration = audio_durations[i]
        total_frames = int(duration * FPS)
        
        print(f"  生成片段 {i+1}/{len(SCRIPT_SECTIONS)}: {section.get('title')} ({duration:.1f}秒)")
        
        def make_frame(t, title=section.get("title", ""), 
                      content=section.get("content", ""),
                      subtitle=section.get("subtitle", ""),
                      tf=total_frames):
            frame_num = int(t * FPS)
            return create_text_frame(title, content, subtitle, frame_num, tf)
        
        video_clip = VideoClip(make_frame, duration=duration)
        video_clip = video_clip.with_fps(FPS)
        
        audio_clip = AudioFileClip(str(audio_paths[i]))
        
        video_clips.append(video_clip)
        audio_clips.append(audio_clip)
    
    # 3. 合并所有片段
    print("\n合并视频和音频片段...")
    final_video = concatenate_videoclips(video_clips)
    final_audio = concatenate_audioclips(audio_clips)
    
    # 4. 合并视频和音频
    final = final_video.with_audio(final_audio)
    
    # 5. 导出视频
    output_path = OUTPUT_DIR / "RTT-Assistant-v1.2-介绍.mp4"
    print(f"\n正在导出视频到: {output_path}")
    print("这可能需要几分钟时间...")
    
    final.write_videofile(
        str(output_path),
        fps=FPS,
        codec='libx264',
        audio_codec='aac',
        bitrate='8000k',
        threads=4,
        preset='medium'
    )
    
    # 清理
    final.close()
    final_video.close()
    
    # 删除临时音频文件
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
