#!/bin/bash
echo "Starting Streamlit Frontend..."
export PYTHONPATH="${PYTHONPATH}:/home/site/wwwroot"
python -m streamlit run main.py --server.address 0.0.0.0 --server.headless true