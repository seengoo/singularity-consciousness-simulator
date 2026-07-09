@echo off
chcp 65001 >nul
title 奇点模拟器 v2.0 - 意识构架实验

echo ==================================================
echo   奇点模拟器 v2.0
echo   意识构架实验 — 从"一点"开始
echo ==================================================
echo.
echo 可用参数:
echo   interactive [世界类型] [种子]  - 交互模式
echo   batch       [次数] [世界类型]   - 批量模式
echo   compare     [次数]             - 对比所有世界类型
echo.
echo 世界类型: random, cluster, gradient, ring
echo.
echo 示例:
echo   启动模拟器.bat interactive gradient
echo   启动模拟器.bat batch 50 cluster
echo.

set /p CMD=输入命令 (直接回车=交互模式):

if "%CMD%"=="" (
    python singularity_sim.py interactive
) else (
    python singularity_sim.py %CMD%
)

echo.
echo 按任意键退出...
pause >nul
