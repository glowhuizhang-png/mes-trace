@echo off
cd /d D:\QUALITY
echo 正在启动轮胎质量看板...
start streamlit run app.py
if errorlevel 1 (
    echo 请确保已安装 streamlit: pip install streamlit
    pause
)