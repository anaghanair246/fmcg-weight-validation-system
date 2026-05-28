#!/bin/bash
echo "Releasing webcam locks..."
fuser -k /dev/video0 /dev/video1 2>/dev/null
sleep 0.5
echo "Starting Streamlit..."
streamlit run app.py
