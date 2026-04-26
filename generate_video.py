#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RTT Assistant v1.2 介绍视频生成脚本
使用Edge TTS生成语音，MoviePy生成画面和合成视频
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

# 脚本内容（简化版，适合2-3分钟）
SCRIPT_SECTIONS = [
    {
        "title": "RTT Assistant v1.2",
        "subtitle": "功能介绍",
        "content": "RTT Assistant是一款基于JLink RTT的MCU调试工具，通过SWD或JTAG接口实现PC与MCU的高效通信。",
        "duration": 8
    },
    {
        "title": "核心功能",
        "content": "支持RTT通信、连接配置、数据收发、日志记录和配置保存。可通过USB或TCP IP连接JLink，支持多种MCU型号。",
        "duration": 10
    },
    {
        "title": "对比JLink RTT Viewer",
        "content": "相比官方的JLink RTT Viewer，RTT Assistant有六大优势：时间戳显示、日志窗口、配置保存、数据导出、独立EXE、中文界面。",
        "duration": 12
    },
    {
        "title": "优势一：时间戳",
        "content": "精确记录数据收发时间，便于调试分析。这是JLink RTT Viewer没有的功能。",
        "duration": 8
    },
    {
        "title": "优势二：日志窗口",
        "content": "独立日志窗口，记录所有连接和通讯事件，支持类型过滤，问题排查更高效。",
        "duration": 8
    },
    {
        "title": "优势三：配置保存",
        "content": "自动保存设置，下次启动自动恢复，无需重复配置。",
        "duration": 7
    },
    {
        "title": "优势四：数据导出",
        "content": "一键导出接收数据到文件，方便分析和存档。",
        "duration": 6
    },
    {
        "title": "优势五：独立EXE",
        "content": "单EXE文件，无需安装Python环境，即开即用。",
        "duration": 7
    },
    {
        "title": "优势六：中文界面",
        "content": "全中文界面，操作简单直观，更适合国内开发者使用。",
        "duration": 7
    },
    {
        "title": "使用方法",
        "content": "双击EXE文件即可运行。配置连接参数后，即可进行数据收发。支持HEX和字符串显示模式。",
        "duration": 10
    },
    {
        "title": "系统要求",
        "content": "Windows系统，JLink软件V930以上，MCU需要已移植RTT代码。",
        "duration": 7
    },
    {
        "title": "总结",
        "content": "RTT Assistant，让RTT调试更简单高效。欢迎下载使用！",
        "duration": 8
    }
]


async def generate_tts():
    """生成TTS音频"""
    print("正在生成TTS音频...")
    
    # 合并所有文本
    all_text = ""
    for section in SCRIPT_SECTIONS:
        all_text += section.get("title", "") + "。"
        all_text += section.get("content", "") + " "
    
    # 生成音频
    audio_path = OUTPUT_DIR / "audio.mp3"
    
    communicate = edge_tts.Communicate(all_text, VOICE)
    await communicate.save(str(audio_path))
    
    print(f"TTS音频已生成: {audio_path}")
    return audio_path


def create_text_frame(title, content, frame_num, total_frames):
    """创建带文字的画面帧"""
    # 创建黑色背景
    img = Image.new('RGB', (WIDTH, HEIGHT), color='black')
    draw = ImageDraw.Draw(img)
    
    # 尝试加载字体，失败则使用默认字体
    try:
        # 标题字体 - 大字体
        title_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 120)
        # 内容字体 - 中等字体
        content_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 80)
        # 副标题字体
        subtitle_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 90)
    except:
        title_font = ImageFont.load_default()
        content_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
    
    # 计算动画进度
    progress = frame_num / total_frames
    
    # 标题淡入效果
    if frame_num < 30:
        alpha = int(255 * (frame_num / 30))
    elif frame_num > total_frames - 30:
        alpha = int(255 * ((total_frames - frame_num) / 30))
    else:
        alpha = 255
    
    # 绘制标题
    if title:
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (WIDTH - title_width) // 2
        title_y = HEIGHT // 3 - 100
        
        draw.text((title_x, title_y), title, fill=(255, 255, 255), font=title_font)
    
    # 绘制副标题
    subtitle = SCRIPT_SECTIONS[0].get("subtitle", "")
    if subtitle and frame_num < 60:
        sub_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        sub_width = sub_bbox[2] - sub_bbox[0]
        sub_x = (WIDTH - sub_width) // 2
        sub_y = HEIGHT // 3 + 50
        draw.text((sub_x, sub_y), subtitle, fill=(200, 200, 200), font=subtitle_font)
    
    # 绘制内容（打字机效果）
    if content:
        # 计算显示的字符数
        chars_to_show = int(len(content) * min(1.0, progress * 1.5))
        visible_content = content[:chars_to_show]
        
        # 分行显示
        lines = []
        words = visible_content
        max_chars_per_line = 35
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
            draw.text((line_x, content_y), line, fill=(240, 240, 240), font=content_font)
            content_y += 100
    
    return np.array(img)


def generate_video():
    """生成视频"""
    print("正在生成视频...")
    
    # 生成每个section的视频片段
    clips = []
    
    for i, section in enumerate(SCRIPT_SECTIONS):
        print(f"生成片段 {i+1}/{len(SCRIPT_SECTIONS)}: {section.get('title', '')}")
        
        duration = section.get("duration", 8)
        total_frames = int(duration * FPS)
        
        # 创建视频片段
        def make_frame(t):
            frame_num = int(t * FPS)
            return create_text_frame(
                section.get("title", ""),
                section.get("content", ""),
                frame_num,
                total_frames
            )
        
        clip = VideoClip(make_frame, duration=duration)
        clip = clip.with_fps(FPS)
        clips.append(clip)
    
    # 合并所有片段
    print("合并视频片段...")
    final_video = concatenate_videoclips(clips)
    
    return final_video


def add_audio_to_video(video, audio_path):
    """添加音频到视频"""
    print("添加音频...")
    
    audio = AudioFileClip(str(audio_path))
    
    # 如果音频比视频长，裁剪音频
    if audio.duration > video.duration:
        audio = audio.subclipped(0, video.duration)
    # 如果视频比音频长，循环音频
    elif video.duration > audio.duration:
        # 保持音频原样，视频末尾静音
        pass
    
    final = video.with_audio(audio)
    return final


async def main():
    """主函数"""
    print("=" * 50)
    print("RTT Assistant v1.2 介绍视频生成")
    print("=" * 50)
    
    # 1. 生成TTS音频
    audio_path = await generate_tts()
    
    # 2. 生成视频画面
    video = generate_video()
    
    # 3. 添加音频
    final = add_audio_to_video(video, audio_path)
    
    # 4. 导出视频
    output_path = OUTPUT_DIR / "RTT-Assistant-v1.2-介绍.mp4"
    print(f"正在导出视频到: {output_path}")
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
    
    # 清理临时文件
    final.close()
    video.close()
    
    print("=" * 50)
    print(f"视频生成完成！")
    print(f"输出路径: {output_path}")
    print(f"分辨率: {WIDTH}x{HEIGHT} (4K)")
    print(f"时长: {final.duration:.1f}秒")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
