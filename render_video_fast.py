#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RTT Assistant v1.2 视频渲染 - 快速切换版
使用背景音乐，多场景快速切换
"""

import subprocess
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path("C:/Users/jerry/Desktop/rtt/video")
PROJECT_DIR = Path("C:/Users/jerry/Desktop/rtt")
TEMP_DIR = OUTPUT_DIR / "temp"
BGM_PATH = Path("d:/Users/jerry/Documents/GitHub/rzn2l_2/26_rzn2l_rtt_print_address/video/public/bgm.mp3")

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

def create_title_frame(title, subtitle=""):
    img = Image.new('RGB', (WIDTH, HEIGHT), (10, 15, 25))
    draw = ImageDraw.Draw(img)
    
    try:
        title_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 120)
        subtitle_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 60)
    except:
        title_font = subtitle_font = ImageFont.load_default()
    
    if title:
        bbox = draw.textbbox((0, 0), title, font=title_font)
        w = bbox[2] - bbox[0]
        x = (WIDTH - w) // 2
        y = HEIGHT // 2 - 60
        draw.text((x, y), title, fill=(255, 255, 255), font=title_font)
        draw.line([(x, y + 130), (x + w, y + 130)], fill=(100, 150, 255), width=4)
    
    if subtitle:
        bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        w = bbox[2] - bbox[0]
        x = (WIDTH - w) // 2
        draw.text((x, HEIGHT // 2 + 100), subtitle, fill=(200, 200, 200), font=subtitle_font)
    
    return img

def create_feature_frame(title, content):
    img = Image.new('RGB', (WIDTH, HEIGHT), (15, 20, 35))
    draw = ImageDraw.Draw(img)
    
    try:
        title_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 80)
        content_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 50)
    except:
        title_font = content_font = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), title, font=title_font)
    w = bbox[2] - bbox[0]
    x = (WIDTH - w) // 2
    draw.text((x, HEIGHT // 4), title, fill=(100, 200, 255), font=title_font)
    
    lines = []
    words = content
    max_chars = 24
    while words:
        if len(words) <= max_chars:
            lines.append(words)
            break
        lines.append(words[:max_chars])
        words = words[max_chars:]
    
    y = HEIGHT // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=content_font)
        w = bbox[2] - bbox[0]
        x = (WIDTH - w) // 2
        draw.text((x, y), line, fill=(240, 240, 240), font=content_font)
        y += 70
    
    return img

def create_screenshot_frame(filename, label, bg_color=(10, 15, 25)):
    img = Image.new('RGB', (WIDTH, HEIGHT), bg_color)
    draw = ImageDraw.Draw(img)
    
    ss_path = PROJECT_DIR / filename
    if ss_path.exists():
        ss = Image.open(ss_path).convert("RGB")
        scale = min(WIDTH / ss.width * 0.85, HEIGHT / ss.height * 0.85)
        new_w = int(ss.width * scale)
        new_h = int(ss.height * scale)
        ss = ss.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        x = (WIDTH - new_w) // 2
        y = (HEIGHT - new_h) // 2
        img.paste(ss, (x, y))
        
        try:
            label_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 50)
        except:
            label_font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), label, font=label_font)
        lw = bbox[2] - bbox[0]
        draw.text((WIDTH // 2 - lw // 2, y - 60), label, fill=(255, 255, 255), font=label_font)
    
    return img

def create_compare_frame():
    img = Image.new('RGB', (WIDTH, HEIGHT), (10, 15, 25))
    draw = ImageDraw.Draw(img)
    
    try:
        label_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 45)
    except:
        label_font = ImageFont.load_default()
    
    for i, (filename, label, pos_x, color) in enumerate([
        ("ScreenShot_segger rtt.png", "JLink RTT Viewer", WIDTH // 4, (80, 80, 80)),
        ("ScreenShot_rtt assistant.png", "RTT Assistant", WIDTH * 3 // 4, (80, 130, 180))
    ]):
        ss_path = PROJECT_DIR / filename
        if ss_path.exists():
            ss = Image.open(ss_path).convert("RGB")
            scale = 0.48
            new_w = int(ss.width * scale)
            new_h = int(ss.height * scale)
            ss = ss.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            bordered = Image.new('RGB', (new_w + 8, new_h + 8), color)
            bordered.paste(ss, (4, 4))
            
            x = pos_x - new_w // 2
            y = HEIGHT // 2 - new_h // 2 + 30
            img.paste(bordered, (x, y))
            
            bbox = draw.textbbox((0, 0), label, font=label_font)
            lw = bbox[2] - bbox[0]
            draw.text((pos_x - lw // 2, y - 55), label, fill=(255, 255, 255), font=label_font)
    
    return img

def create_end_frame():
    img = Image.new('RGB', (WIDTH, HEIGHT), (10, 15, 25))
    draw = ImageDraw.Draw(img)
    
    try:
        title_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 100)
        sub_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 50)
    except:
        title_font = sub_font = ImageFont.load_default()
    
    text = "RTT Assistant v1.2"
    bbox = draw.textbbox((0, 0), text, font=title_font)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) // 2, HEIGHT // 2 - 80), text, fill=(100, 200, 255), font=title_font)
    
    text2 = "让RTT调试更简单高效"
    bbox = draw.textbbox((0, 0), text2, font=sub_font)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) // 2, HEIGHT // 2 + 60), text2, fill=(200, 200, 200), font=sub_font)
    
    return img

SCENES = [
    ("title", {"title": "RTT Assistant", "subtitle": "v1.2 功能介绍"}, 2.5),
    ("screenshot", {"filename": "ScreenShot_rtt assistant.png", "label": "RTT Assistant 主界面"}, 2.0),
    ("feature", {"title": "核心功能", "content": "基于JLink RTT的MCU调试工具"}, 1.5),
    ("screenshot", {"filename": "ScreenShot_segger rtt.png", "label": "JLink RTT Viewer"}, 1.8),
    ("compare", {}, 3.0),
    ("feature", {"title": "优势一：时间戳", "content": "精确记录数据收发时间"}, 1.5),
    ("screenshot", {"filename": "ScreenShot_rtt assistant.png", "label": "时间戳功能展示"}, 1.8),
    ("feature", {"title": "优势二：日志窗口", "content": "记录所有连接和通讯事件"}, 1.5),
    ("feature", {"title": "优势三：配置保存", "content": "自动保存，下次自动恢复"}, 1.5),
    ("screenshot", {"filename": "ScreenShot_rtt assistant.png", "label": "配置保存功能"}, 1.8),
    ("feature", {"title": "优势四：数据导出", "content": "一键导出接收数据"}, 1.5),
    ("feature", {"title": "优势五：独立EXE", "content": "无需安装Python环境"}, 1.5),
    ("feature", {"title": "优势六：中文界面", "content": "全中文操作界面"}, 1.5),
    ("screenshot", {"filename": "ScreenShot_rtt assistant.png", "label": "中文界面展示"}, 2.0),
    ("feature", {"title": "使用方法", "content": "双击运行，配置参数即可使用"}, 1.8),
    ("feature", {"title": "系统要求", "content": "Windows + JLink V930+"}, 1.5),
    ("compare", {}, 2.5),
    ("screenshot", {"filename": "ScreenShot_rtt assistant.png", "label": "RTT Assistant"}, 2.0),
    ("end", {}, 3.0),
]

TRANSITIONS = ["fade", "slideleft", "slideright", "slideup", "slidedown", "zoomin"]

def apply_transition(input1, input2, output, duration, trans_type):
    if trans_type == "fade":
        filter_complex = f"[0:v]format=pix_fmts=yuva420p[t0];[t0][1:v]blend=all_expr='A*(1-T/{duration})+B*(T/{duration})'[outv]"
    elif trans_type == "slideleft":
        filter_complex = f"[0:v]format=pix_fmts=yuva420p[t0];[t0][1:v]overlay=x='-(W*T/{duration})'[outv]"
    elif trans_type == "slideright":
        filter_complex = f"[0:v]format=pix_fmts=yuva420p[t0];[t0][1:v]overlay=x='W*(1-T/{duration})'[outv]"
    elif trans_type == "slideup":
        filter_complex = f"[0:v]format=pix_fmts=yuva420p[t0];[t0][1:v]overlay=y='-(H*T/{duration})'[outv]"
    elif trans_type == "slidedown":
        filter_complex = f"[0:v]format=pix_fmts=yuva420p[t0];[t0][1:v]overlay=y='H*(1-T/{duration})'[outv]"
    elif trans_type == "zoomin":
        filter_complex = f"[1:v]scale=w='W*T/{duration}':h='H*T/{duration}':eval=frame[t1];[0:v][t1]overlay=x='(W-w)/2':y='(H-h)/2'[outv]"
    else:
        filter_complex = f"[0:v][1:v]blend=all_expr='A*(1-T/{duration})+B*(T/{duration})'[outv]"
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input1),
        "-i", str(input2),
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-t", str(duration),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(output)
    ]
    
    subprocess.run(cmd, capture_output=True)

def main():
    print("=" * 50)
    print("RTT Assistant v1.2 视频渲染（快速切换版）")
    print("=" * 50)
    
    if not BGM_PATH.exists():
        print(f"错误: BGM文件不存在: {BGM_PATH}")
        return
    
    bgm_duration = get_audio_duration(BGM_PATH)
    print(f"背景音乐时长: {bgm_duration:.1f}秒")
    
    total_scene_duration = sum(scene[2] for scene in SCENES)
    print(f"场景总时长: {total_scene_duration:.1f}秒")
    
    print("\n生成场景帧...")
    frame_paths = []
    
    for i, (scene_type, params, duration) in enumerate(SCENES):
        print(f"  场景 {i+1}/{len(SCENES)}: {scene_type} ({duration:.1f}秒)")
        
        if scene_type == "title":
            img = create_title_frame(params["title"], params.get("subtitle", ""))
        elif scene_type == "feature":
            img = create_feature_frame(params["title"], params["content"])
        elif scene_type == "screenshot":
            img = create_screenshot_frame(params["filename"], params["label"])
        elif scene_type == "compare":
            img = create_compare_frame()
        elif scene_type == "end":
            img = create_end_frame()
        else:
            img = Image.new('RGB', (WIDTH, HEIGHT), (10, 15, 25))
        
        frame_path = TEMP_DIR / f"scene_{i:03d}.png"
        img.save(frame_path)
        frame_paths.append((frame_path, duration))
    
    print("\n生成视频片段...")
    segment_paths = []
    
    for i, (frame_path, duration) in enumerate(frame_paths):
        segment_path = TEMP_DIR / f"segment_{i:03d}.mp4"
        
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(frame_path),
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-pix_fmt", "yuv420p",
            "-t", str(duration),
            "-r", "30",
            str(segment_path)
        ]
        
        subprocess.run(cmd, capture_output=True)
        segment_paths.append(segment_path)
        print(f"  片段 {i+1}/{len(frame_paths)} 完成")
    
    print("\n合并视频片段...")
    concat_file = TEMP_DIR / "concat.txt"
    with open(concat_file, "w") as f:
        for seg_path in segment_paths:
            f.write(f"file '{seg_path.name}'\n")
    
    merged_video = TEMP_DIR / "merged.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(merged_video)
    ]
    subprocess.run(cmd, capture_output=True)
    
    print("添加背景音乐（循环）...")
    output_path = OUTPUT_DIR / "RTT-Assistant-v1.2-介绍.mp4"
    
    video_duration = get_audio_duration(merged_video)
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(merged_video),
        "-stream_loop", "-1",
        "-i", str(BGM_PATH),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-map", "0:v",
        "-map", "1:a",
        "-t", str(video_duration),
        str(output_path)
    ]
    subprocess.run(cmd, capture_output=True)
    
    import shutil
    shutil.rmtree(TEMP_DIR)
    
    final_duration = get_audio_duration(output_path)
    print("\n" + "=" * 50)
    print("视频生成完成！")
    print(f"输出: {output_path}")
    print(f"分辨率: {WIDTH}x{HEIGHT}")
    print(f"时长: {final_duration:.1f}秒")
    print(f"场景数: {len(SCENES)}")
    print("=" * 50)

if __name__ == "__main__":
    main()
