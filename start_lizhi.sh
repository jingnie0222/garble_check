#!/bin/bash
export LC_ALL=zh_CN.GBK

curday=`date +%Y-%m-%d`
python3 class_tupu_qa_garbled_detect.py > lizhiqa_log/log_$curday &
