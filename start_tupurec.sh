#!/bin/bash
export LC_ALL=zh_CN.GBK

curday=`date +%Y-%m-%d`
python3 tupu_recommender_garbled_detect.py > tupurec_log/log_$curday &
