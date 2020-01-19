#!/usr/bin/python3
#-*-coding=utf8-*-

import requests
import time
import os,sys
from bs4 import BeautifulSoup
import DataFile
from urllib.parse import quote
import time
import Mail
import Template
from ast import literal_eval
from itertools import chain

MIN_TEXT_LENGTH = 5
url_prefix = "http://wap.sogou.com.inner/web/searchList.jsp?keyword="
get_word_loc = "http://10.143.54.80:81/vr_query_period/vr_query_garbled_lizhi.txt"
word_file = "./word_lizhiqa"
word_list = DataFile.read_file_into_list("./word_lizhiqa")
report_tmp_path = "mail_detail.html"
mail_to = "yinjingjing@sogou-inc.com"
result_file = 'lizhiqa_garbled_result'
f_res = open(result_file, 'w', encoding='utf8')

def log_info(str):
    time_str = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
    sys.stdout.write('[%s] [info] %s\n' % (time_str, str))
    sys.stdout.flush()
    
    
def utf8stdout(in_str):
    utf8stdout = open(1, 'w', encoding='utf-8', closefd=False) # fd 1 is stdout
    print(in_str, file=utf8stdout)

def get_response(query):
    url = url_prefix + quote(query)
    try:
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        return response.text
    except Exception as err:
        utf8stdout("[get_response]:%s" % err)


def get_qa_text(query, xml):
    if not xml:
        utf8stdout('%s: xml is empty' % query)
        return None
    res = ""
    parsed_html = BeautifulSoup(xml, "html.parser")
    temp = parsed_html.select(".vrResult")
    num = len(temp)
    #utf8stdout(temp[0])
    
    for i in range(num):
        if len(temp[i].text) < MIN_TEXT_LENGTH:
            continue
        else:             
            if 'class="icon-known' in str(temp[i]):
                #去除属性script,否则其text会被提取出来
                [s.extract() for s in temp[i]("script")] 
                [s.extract() for s in temp[i]("style")]
                res = temp[i].text.replace('\n', '')
                #utf8stdout(res)
                return res
    return res            


def check_garbled(query, text):
    line = {"realname": "kgm", "text": text}
    headers = {"Conent-type":"application/x-www-form-urlencoded;charset=UTF-16LE"}
    garble = False
    try:
        base_resp = requests.post("http://10.143.43.82:8887/gTextDetect", data=line, headers=headers, timeout=20)
        resp = base_resp.text
        #utf8stdout(resp)
        
        if resp is None:
            utf8stdout("[check_garbled]: gDetect-api result is null, query:%s" % query)
            return  None, None
            
        # transform label str into label list, easy to handle
        label_info = resp.split('array')[0][1:-2]
        label_list = literal_eval(label_info)
        label_list = list(chain(*label_list))
        label_list = list(set(label_list))

        if len(label_list ) > 1:
           garble = True
           return garble, resp
        
        if len(label_list ) == 1:
            if '__label__0' in label_list :
                return garble, resp
            else:
                garble = True
                return garble, resp
           
    except Exception as err:
        utf8stdout("[check_garbled]:%s" % err)

def get_word(url, word_file):

    try:
        res = requests.get(url)
        res.encoding = "utf-8"
        with open(word_file, 'w', encoding='utf8') as f:
            f.write(res.text)
    except Exception as err:
        utf8stdout('[get_word]: %s' % err)
        
def main():
    get_word(get_word_loc,  word_file)
    
    index = 1
    report_content = ""
    mail_title = Template.html_h3_title("附件结果可能有乱码，请确认")
    
    for word in word_list:    
        utf8stdout("process %d word" % index)    
        try:
            # ready get qa_text
            tmp_list = word.split()
            query = tmp_list[0]
            vrid = tmp_list[1]
            html = get_response(query)
            if not html:
                utf8stdout("source html is null. query:%s, vrid:%s" % (query, vrid))
                index = index + 1
                continue
            
            qa_text = get_qa_text(query, html)   
            if not qa_text:
                utf8stdout("qa text is null. query:%s, vrid:%s" % (query, vrid)) 
                index = index + 1
                continue                

            garble, res = check_garbled(query, qa_text)               
            utf8stdout("query:%s, vrid:%s, is_garble:%s" % (query, vrid, garble))
            utf8stdout("gDetect-api result:%s" % res)
            utf8stdout("qa_text:%s" % qa_text)
            if garble:
                f_res.write("index:%d, query:%s, vrid:%s\n" % (index, query, vrid))
                f_res.write("gDetect-api result:%s\n" % res)
                f_res.write("qa_text:%s\n" % qa_text)
                f_res.write('\n')

                    
            index = index + 1
            
        except Exception as err:
            utf8stdout(err)
            index = index + 1
            continue
    #当检测有乱码结果时才发邮件
    #if mail_res:  
        # utf8stdout("mail_res is not null, Send mail") 
    f_res.close()        
    report_content = mail_title
    DataFile.write_full_file(report_tmp_path, report_content)
    Mail.sendMail("立知问答结果乱码检测", report_tmp_path, mail_to, attachment=result_file)
   
 
if __name__ == '__main__':
    main()
    


