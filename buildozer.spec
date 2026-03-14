[app]

# 应用基本信息
title = Spider Solitaire
package.name = spidersolitaire
package.domain = org.spidertoy

# 源代码目录
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf

# 版本
version = 1.0.0

# 应用依赖
requirements = python3,kivy==2.3.1

# 支持的屏幕方向 (portrait, landscape)
orientation = portrait

# 全屏
fullscreen = 1

# Android 特定配置
# 目标 Android API (Mate 40 支持 Android 10+)
android.api = 33
android.minapi = 24
android.ndk = 25b
android.sdk = 33

# 架构 (Mate 40 是 ARM64)
android.archs = arm64-v8a

# 权限：外部存储读写（用于历史记录备份，防止重装丢失）
android.permissions = WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# 应用图标和启动画面（暂用默认）
# icon.filename = %(source.dir)s/assets/icon.png
# presplash.filename = %(source.dir)s/assets/presplash.png

# 设置应用为竖屏启动，但允许旋转
android.manifest.orientation = unspecified

# 不使用 Android 的 gradle 依赖
android.gradle_dependencies =

# 排除不需要的文件
source.exclude_dirs = tests,spider_env,.git,__pycache__
source.exclude_patterns = *.pyc,*.pyo,*.spec,*.md

# Log 设置
log_level = 2

# Buildozer 设置
warn_on_root = 1

[buildozer]
log_level = 2
warn_on_root = 1
