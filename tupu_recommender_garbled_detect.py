#!/usr/bin/python3
#-*-coding=utf8-*-

import requests
import time
import os,sys
from bs4 import BeautifulSoup
import DataFile
import time
import Mail
import Template
from ast import literal_eval
from itertools import chain


url_prefix = "http://tj01.tupu.hb.ted:28026"

get_word_loc = "http://10.143.54.80:81/vr_query_period/vr_query_garbled_tupu.txt"
word_file = "./word_tupurec"
word_list = DataFile.read_file_into_list("./word_tupurec")
result_file = './tupurec_garbled_result'
report_tmp_path = "mail_detail.html"
mail_to = "yinjingjing@sogou-inc.com"

f_res = open(result_file, 'w', encoding='utf8')

def log_info(str):
    time_str = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
    sys.stdout.write('[%s] [info] %s\n' % (time_str, str))
    sys.stdout.flush()
    
def utf8stdout(in_str):
    utf8stdout = open(1, 'w', encoding='utf-8', closefd=False) # fd 1 is stdout
    print(in_str, file=utf8stdout)

def get_response(queryString, queryFrom, isWaigou):
    payload = dict()
    payload['queryString'] = queryString.encode('utf16')
    payload['queryFrom'] = queryFrom.encode('utf16')
    payload['isWaigou'] = isWaigou.encode('utf16')
    try:
        response = requests.get(url_prefix, params = payload, timeout=10)
        utf8stdout(response.url)
        result = response.text
        return result
    except Exception as err:
        utf8stdout("[get_response]:%s" % err)


def get_att_name(query, xml, att_lst):
    if not xml:
        utf8stdout('%s: xml is empty' % query)
        return None
    res_list = []
    parsed_html = BeautifulSoup(xml, "html.parser")
    for data in parsed_html.find_all('element'):
        for att in att_lst:
            val = data.get(att)
            #print("%s:%s" % (att, val))
            res_list.append(val)
    return "".join(res_list)

def check_garbled(query, text):
    line = {"realname": "kgm", "text": text}
    headers = {"Conent-type":"application/x-www-form-urlencoded;charset=UTF-16LE"}
    garble = False
    #utf8stdout(text)
    # try:
    base_resp = requests.post("http://10.143.43.82:8887/gTextDetect", data=line, headers=headers, timeout=20)
    resp = base_resp.text
        
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
           
    # except Exception as err:
        # utf8stdout("[check_garbled]:%s" % err)

def get_word(url, word_file):

    try:
        res = requests.get(url)
        res.encoding = "utf-8"
        with open(word_file, 'w', encoding='utf8') as f:
            f.write(res.text)
    except Exception as err:
        utf8stdout('[get_word]: %s' % err)
    
        
def main():
    arr_lst = ['name', 'allname', 'year']           
    get_word(get_word_loc, word_file)
    
    index = 1
    report_content = ""
    mail_title = Template.html_h3_title("如下查询结果可能有乱码，请确认")
    mail_res = ""
    
    for word in word_list:    
        utf8stdout("process %d word" % index)    
        try:
            # ready get qa_text
            tmp_list = word.split()
            query = tmp_list[0]
            vrid = tmp_list[1]
            response = get_response(query, 'wap', '1')
          
            if not response:
                utf8stdout("source response is null. query:%s, vrid:%s" % (query, vrid))
                index = index + 1
                continue    
          
            extract_text = get_att_name(query, response, arr_lst)
            utf8stdout("extract_text:%s" % extract_text)            
            if not extract_text:
                utf8stdout("extract text is null. query:%s, vrid:%s" % (query, vrid)) 
                index = index + 1
                continue               
            
            garble, res = check_garbled(query, extract_text)               
            utf8stdout("query:%s, vrid:%s, gDetect-api result:%s, is_garble:%s" % (query, vrid, res, garble))
            if garble:
                f_res.write("index:%d, query:%s, vrid:%s\n" % (index, query, vrid))
                f_res.write("gDetect-api result:%s\n" % res)
                f_res.write("extract_text:%s\n" % extract_text)
                f_res.write('\n')
                    
            index = index + 1
            
        except Exception as err:
            utf8stdout(err)
            index = index + 1
            continue

    f_res.close()
    #当检测有乱码结果时才发邮件
    if os.path.getsize(result_file) > 0:
        report_content = mail_title + mail_res
        DataFile.write_full_file(report_tmp_path, report_content)
        Mail.sendMail("图谱推荐结果乱码检测", report_tmp_path, mail_to, attachment=result_file)
   
 
if __name__ == '__main__':
    main()

    


