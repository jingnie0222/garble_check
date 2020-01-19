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

class Node(object):
    def __init__(self, query, vrid):
        self.query = query
        self.vrid = vrid
        self.url = ""
        self.html = ""
        self.qa_text = ""
        self.garble = False
        self.garble_res = ""
        self.output_dict = dict()
        
    def gen_url(self):
        self.url = url_prefix + quote(self.query)
                       
    def get_response(self):
        try:
            response = requests.get(self.url, timeout=10)
            response.encoding = 'utf-8'
            self.html = response.text
        except Exception as err:
            utf8stdout("[get_response]:%s" % err)
            
    def get_qa_text(self):
        if not self.html:
            utf8stdout('%s: html is empty' % self.query)
            
        parsed_html = BeautifulSoup(self.html, "html.parser")
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
                    self.qa_text = temp[i].text.replace('\n', '')
    
    
    def check_garbled(self):
        line = {"realname": "kgm", "text": self.qa_text}
        headers = {"Conent-type":"application/x-www-form-urlencoded;charset=UTF-16LE"}
        try:
            base_resp = requests.post("http://10.143.43.82:8887/gTextDetect", data=line, headers=headers, timeout=20)
            self.garble_res = base_resp.text
            #utf8stdout(resp)
            
            if self.garble_res is None:
                utf8stdout("[check_garbled]: gDetect-api result is null, query:%s" % query)
                return 
                
            # transform label str into label list, easy to handle
            label_info = self.garble_res.split('array')[0][1:-2]
            label_list = literal_eval(label_info)
            label_list = list(chain(*label_list))
            label_list = list(set(label_list))

            if len(label_list ) > 1:
                self.garble = True               
            
            if len(label_list ) == 1 and '__label__0' not in label_list:
                self.garble = True
               
        except Exception as err:
            utf8stdout("[check_garbled]:%s" % err)
            
    
    def output_garble(self):
        if self.garble:
            self.output_dict['query'] = self.query
            self.output_dict['vrid'] = self.vrid
            self.output_dict['qa_text'] = self.qa_text
            self.output_dict['garble_res'] = self.garble_res
            
        return self.output_dict


    
def get_word(url, word_file):
    try:
        res = requests.get(url)
        res.encoding = "utf-8"
        with open(word_file, 'w', encoding='utf8') as f:
            f.write(res.text)
    except Exception as err:
        utf8stdout('[get_word]: %s' % err)

def utf8stdout(in_str):
    utf8stdout = open(1, 'w', encoding='utf-8', closefd=False) # fd 1 is stdout
    print(in_str, file=utf8stdout)
        
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
            
            node = Node(query, vrid)
            node.gen_url()
            node.get_response()
            if not node.html:
                utf8stdout("source html is null. query:%s, vrid:%s" % (query, vrid))
                index = index + 1
                continue
                
            node.get_qa_text()
            if not node.qa_text:
                utf8stdout("qa text is null. query:%s, vrid:%s" % (query, vrid)) 
                index = index + 1
                continue  
                
            node.check_garbled()
            node_res = node.output_garble()
            
            if node_res:
                f_res.write("index:%d, query:%s, vrid:%s\n" % (index, query, vrid))
                f_res.write("gDetect-api result:%s\n" % node.garble_res)
                f_res.write("qa_text:%s\n" % node.qa_text)
                f_res.write('\n')
            
            index = index + 1
            
        except Exception as err:
            utf8stdout(err)
            index = index + 1
            continue

    f_res.close() 
    
    #当检测有乱码时才发送邮件
    if os.path.getsize(result_file) > 0:
        report_content = mail_title
        DataFile.write_full_file(report_tmp_path, report_content)
        Mail.sendMail("立知问答结果乱码检测", report_tmp_path, mail_to, attachment=result_file)


if __name__ == '__main__':
    main()

