#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RTT Assistant v1.2 视频渲染 - 快速切换版 v2
总时长约24秒，多场景快速切换，多种切换效果
"""

import subprocess
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
    img = Image.new('RGB', (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    try:
        title_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 130)
        subtitle_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 55)
    except:
        title_font = subtitle_font = ImageFont.load_default()
    
    if title:
        bbox = draw.textbbox((0, 0), title, font=title_font)
        w = bbox[2] - bbox[0]
        x = (WIDTH - w) // 2
        y = HEIGHT // 2 - 80
        draw.text((x, y), title, fill=(255, 255, 255), font=title_font)
        draw.line([(x, y + 140), (x + w, y + 140)], fill=(100, 180, 255), width=5)
    
    if subtitle:
        bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        w = bbox[2] - bbox[0]
        x = (WIDTH - w) // 2
        draw.text((x, HEIGHT // 2 + 100), subtitle, fill=(180, 180, 180), font=subtitle_font)
    
    return img

def create_feature_frame(title, content, bg_color=(0, 0, 0)):
    img = Image.new('RGB', (WIDTH, HEIGHT), bg_color)
    draw = ImageDraw.Draw(img)
    
    try:
        title_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 85)
        content_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 48)
    except:
        title_font = content_font = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), title, font=title_font)
    w = bbox[2] - bbox[0]
    x = (WIDTH - w) // 2
    draw.text((x, HEIGHT // 3 - 20), title, fill=(80, 200, 255), font=title_font)
    
    lines = []
    words = content
    max_chars = 26
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
        y += 65
    
    return img

def create_screenshot_frame(filename, label, scale=0.9):
    img = Image.new('RGB', (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    ss_path = PROJECT_DIR / filename
    if ss_path.exists():
        ss = Image.open(ss_path).convert("RGB")
        new_w = int(ss.width * scale)
        new_h = int(ss.height * scale)
        ss = ss.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        x = (WIDTH - new_w) // 2
        y = (HEIGHT - new_h) // 2
        img.paste(ss, (x, y))
        
        try:
            label_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 48)
        except:
            label_font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), label, font=label_font)
        lw = bbox[2] - bbox[0]
        draw.text((WIDTH // 2 - lw // 2, y - 55), label, fill=(255, 255, 255), font=label_font)
    
    return img

def create_compare_frame():
    img = Image.new('RGB', (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    try:
        label_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 42)
    except:
        label_font = ImageFont.load_default()
    
    for i, (filename, label, pos_x, color) in enumerate([
        ("ScreenShot_segger rtt.png", "JLink RTT Viewer", WIDTH // 4, (70, 70, 70)),
        ("ScreenShot_rtt assistant.png", "RTT Assistant", WIDTH * 3 // 4, (70, 120, 180))
    ]):
        ss_path = PROJECT_DIR / filename
        if ss_path.exists():
            ss = Image.open(ss_path).convert("RGB")
            scale = 0.78
            new_w = int(ss.width * scale)
            new_h = int(ss.height * scale)
            ss = ss.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            bordered = Image.new('RGB', (new_w + 10, new_h + 10), color)
            bordered.paste(ss, (5, 5))
            
            x = pos_x - new_w // 2
            y = HEIGHT // 2 - new_h // 2
            img.paste(bordered, (x, y))
            
            bbox = draw.textbbox((0, 0), label, font=label_font)
            lw = bbox[2] - bbox[0]
            draw.text((pos_x - lw // 2, y - 45), label, fill=(255, 255, 255), font=label_font)
    
    return img

def create_end_frame():
    img = Image.new('RGB', (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    try:
        title_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 110)
        sub_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 52)
    except:
        title_font = sub_font = ImageFont.load_default()
    
    text = "RTT Assistant v1.2"
    bbox = draw.textbbox((0, 0), text, font=title_font)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) // 2, HEIGHT // 2 - 90), text, fill=(80, 200, 255), font=title_font)
    
    text2 = "让RTT调试更简单高效"
    bbox = draw.textbbox((0, 0), text2, font=sub_font)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) // 2, HEIGHT // 2 + 70), text2, fill=(200, 200, 200), font=sub_font)
    
    return img

TRANSITION_TYPES = [
    "fade", "slideleft", "slideright", "slideup", "slidedown",
    "circleopen", "distance", "diagtl", "diagtr", "diagbl", "diagbr",
    "hlslice", "hrslice", "vuslice", "vdslice", "dissolve", "radial"
]

SCENES = [
    ("title", {"title": "RTT Assistant", "subtitle": "v1.2 功能介绍"}),
    ("screenshot", {"filename": "ScreenShot_rtt assistant.png", "label": "主界面"}),
    ("feature", {"title": "基于JLink RTT", "content": "高效的MCU调试通信工具"}),
    ("compare", {}),
    ("feature", {"title": "时间戳记录", "content": "精确记录数据收发时间"}),
    ("feature", {"title": "独立日志窗口", "content": "记录所有连接和通讯事件"}),
    ("feature", {"title": "配置自动保存", "content": "下次启动自动恢复"}),
    ("feature", {"title": "一键数据导出", "content": "方便分析和存档"}),
    ("feature", {"title": "独立EXE运行", "content": "无需安装Python环境"}),
    ("feature", {"title": "全中文界面", "content": "操作简单直观"}),
    ("feature", {"title": "使用方法", "content": "双击运行即可使用"}),
    ("feature", {"title": "系统要求", "content": "Windows + JLink V930+"}),
    ("end", {}),
]

def main():
    print("=" * 50)
    print("RTT Assistant v1.2 视频渲染（快速切换版 v2）")
    print("=" * 50)
    
    if not BGM_PATH.exists():
        print(f"错误: BGM文件不存在: {BGM_PATH}")
        return
    
    bgm_duration = get_audio_duration(BGM_PATH)
    print(f"背景音乐时长: {bgm_duration:.1f}秒")
    
    num_scenes = len(SCENES)
    scene_duration = bgm_duration / num_scenes
    print(f"场景数: {num_scenes}")
    print(f"每场景时长: {scene_duration:.2f}秒")
    
    print("\n生成场景帧...")
    segment_paths = []
    
    for i, (scene_type, params) in enumerate(SCENES):
        print(f"  场景 {i+1}/{num_scenes}: {scene_type}")
        
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
        
        segment_path = TEMP_DIR / f"segment_{i:03d}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(frame_path),
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-pix_fmt", "yuv420p",
            "-t", str(scene_duration),
            "-r", "30",
            str(segment_path)
        ]
        subprocess.run(cmd, capture_output=True)
        segment_paths.append(segment_path)
    
    print("\n合并场景（带切换效果）...")
    
    trans_duration = 0.25
    
    current = segment_paths[0]
    
    for i in range(1, len(segment_paths)):
        trans_type = TRANSITION_TYPES[(i - 1) % len(TRANSITION_TYPES)]
        next_video = segment_paths[i]
        output = TEMP_DIR / f"merged_{i:03d}.mp4"
        
        current_duration = get_audio_duration(current)
        offset = current_duration - trans_duration
        
        xfade_map = {
            "fade": "fade",
            "slideleft": "slideleft", 
            "slideright": "slideright",
            "slideup": "slideup",
            "slidedown": "slidedown",
            "circleopen": "circleopen",
            "distance": "distance",
            "diagtl": "diagtl",
            "diagtr": "diagtr",
            "diagbl": "diagbl",
            "diagbr": "diagbr",
            "hlslice": "hlslice",
            "hrslice": "hrslice",
            "vuslice": "vuslice",
            "vdslice": "vdslice",
            "dissolve": "dissolve",
            "radial": "radial"
        }
        
        trans = xfade_map.get(trans_type, "fade")
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(current),
            "-i", str(next_video),
            "-filter_complex",
            f"[0:v][1:v]xfade=transition={trans}:duration={trans_duration}:offset={offset:.2f}[vout]",
            "-map", "[vout]",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(output)
        ]
        
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode != 0:
            print(f"  切换{i}: {trans_type} 失败，简单拼接")
            concat_file = TEMP_DIR / f"concat_{i}.txt"
            with open(concat_file, "w") as f:
                f.write(f"file '{current.name}'\n")
                f.write(f"file '{next_video.name}'\n")
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                str(output)
            ]
            subprocess.run(cmd, capture_output=True)
        else:
            print(f"  切换{i}: {trans_type}")
        
        current = output
    
    merged_video = current
    
    print("添加背景音乐...")
    output_path = OUTPUT_DIR / "RTT-Assistant-v1.2-介绍.mp4"
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(merged_video),
        "-i", str(BGM_PATH),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-map", "0:v",
        "-map", "1:a",
        "-shortest",
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
    print(f"场景数: {num_scenes}")
    print(f"每场景: {scene_duration:.2f}秒")
    print("=" * 50)

if __name__ == "__main__":
    main()
