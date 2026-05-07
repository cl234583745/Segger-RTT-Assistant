#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2026 chenkaka
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
创建RTT Assistant图标
"""

from PIL import Image, ImageDraw

# 创建图标图像
def create_icon():
    # 创建256x256的图像
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 绘制背景圆形
    draw.ellipse([20, 20, size-20, size-20], fill=(41, 128, 185, 255))
    
    # 绘制内部圆形
    draw.ellipse([40, 40, size-40, size-40], fill=(52, 152, 219, 255))
    
    # 绘制"RTT"文字区域
    draw.rectangle([60, 90, size-60, 170], fill=(255, 255, 255, 255))
    
    # 绘制连接符号(两个箭头)
    # 左箭头
    draw.polygon([(70, 130), (100, 110), (100, 150)], fill=(41, 128, 185, 255))
    # 右箭头
    draw.polygon([(size-70, 130), (size-100, 110), (size-100, 150)], fill=(41, 128, 185, 255))
    
    # 绘制底部装饰线
    draw.rectangle([80, 190, size-80, 200], fill=(255, 255, 255, 255))
    draw.rectangle([80, 210, size-80, 220], fill=(255, 255, 255, 255))
    
    # 保存为ICO格式
    img.save('icon.ico', format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
    img.save('icon.png', format='PNG')
    
    print("图标创建成功!")
    print("- icon.ico (Windows图标)")
    print("- icon.png (PNG图标)")

if __name__ == '__main__':
    create_icon()
