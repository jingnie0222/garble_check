#!/usr/bin/python3
#-*-coding=utf8-*-

import requests
import time
import os,sys
from bs4 import BeautifulSoup
import DataFile
from urllib.parse import quote
from io import BytesIO
from PIL import Image
import base64
import subprocess
import demjson
import time
import Mail
import Template

url_prefix = "http://wap.sogou.com.inner/web/searchList.jsp?keyword="

get_word_loc = "http://10.143.54.80:81/vr_query_period/vr_query_garbled.txt"
word_file = "./word_top"
word_list = DataFile.read_file_into_list("./word_top")

pic_dir_prefix = "/search/odin/nginx/html/wap/tupu_garbled_pic/pic"


report_tmp_path = "mail_detail.html"
mail_to = "yinjingjing@sogou-inc.com"

def log_info(str):
    time_str = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
    sys.stdout.write('[%s] [info] %s\n' % (time_str, str))
    sys.stdout.flush()
    
def utf8stdout(in_str):
    utf8stdout = open(1, 'w', encoding='utf-8', closefd=False) # fd 1 is stdout
    print(in_str, file=utf8stdout)


def pil_base64(image_path):
    """
	image->base64	"""
    image = Image.open(image_path)
    img_buffer = BytesIO()
    image.save(img_buffer, format='PNG')
    byte_data = img_buffer.getvalue()
    base64_str = base64.b64encode(byte_data)
    return base64_str
    

def check_garbled(query, pic):
    line = {"realname": "kgm", "pic": '[{}]'.format(pil_base64(pic))}
    headers = {"Conent-type":"application/x-www-form-urlencoded;charset=UTF-16LE"}
    garble = False
    try:
        base_resp = requests.post("http://10.143.43.82:8888/gDetect-api", data=line, headers=headers, timeout=20)
        resp = base_resp.text
        #print(resp)
        res_dict = demjson.decode(resp)
        #print(res_dict[0][0][4])

        if resp is None:
            utf8stdout("[check_garbled]: gDetect-api result is null,query:%s" % query)
            return  None,None

        if len(res_dict[0]) == 0:
            return garble, resp

        if float(res_dict[0][0][4]) <= 0.8:
            return garble, resp
            
        if float(res_dict[0][0][4]) > 0.8:
            garble = True
            return garble, resp
            
    except Exception as err:
        print("[check_garbled]:%s" % err)

def get_word(url, word_file):

    try:
        res = requests.get(url)
        res.encoding = "utf-8"
        with open(word_file, 'w', encoding='utf8') as f:
            f.write(res.text)
    except Exception as err:
        print('[get_word]: %s' % err)
                    

def gen_pic_dir(result_dir_prefix):
    try:
        now = time.strftime("%Y%m%d%H%M%S", time.localtime())
        dir_name = result_dir_prefix+"_"+now
        os.mkdir(dir_name)
    except FileExistsError:
        log_error('[gen_result_dir] Dir exists: %s. remove dir, mkdir again' % (dir_name))
        shutil.rmtree(dir_name)
        os.mkdir(dir_name)
    nginx_dir = "http://10.144.96.65/tupu_garbled_pic/pic_" + now
        
    return dir_name, nginx_dir
 
 
def main():
    pic_dir, nginx_dir = gen_pic_dir(pic_dir_prefix)
    get_word(get_word_loc,  word_file)
    
    index = 1
    report_content = ""
    mail_title = Template.html_h3_title("如下查询结果可能有乱码，请确认")
    mail_title = Template.html_h3_title("本次运行的截图目录为：%s" % nginx_dir)
    mail_res = ""
    
    for word in word_list:    
        print("process %d word" % index)    
        try:
            # ready screenshot
            tmp_list = word.split()
            query = tmp_list[0]
            vrid = tmp_list[1]
            _craw_url = url_prefix + quote(query)
            vrstr='div.vrResult[id*="sogou_vr_' + vrid + '"],div.vrResult[id*="sogou_vr_kmap_' + vrid+ '"]'
            vrstr=quote(vrstr)
            picname = pic_dir + "/" + "_".join([str(index), quote(query), vrid+".png"])
            nodejs_scrpit='spec-selector.js'
            path = '/search/odin/yinjingjing/python/garbled_detector/'

            
            child = subprocess.Popen(['/bin/node', nodejs_scrpit, \
                                      '-t', 'android', '-m', 'css', \
                                      '-k', vrstr, '-n', picname, \
                                      '-u', quote(_craw_url)], shell=False, \
                                      cwd = path, stdout=subprocess.PIPE)
            nodejs_res = child.stdout.read()
            if nodejs_res != b'0\n':
                utf8stdout("pupppeter ERROR. query:%s, vrid:%s, error:%s"% (query, vrid, nodejs_res))
                continue
            else:
                garble, res = check_garbled(query, picname)
                utf8stdout("query:%s, vrid:%s, gDetect-api result:%s, is_garble:%s" % (query, vrid, res, garble))
                if garble:
                    mail_info = "index:%d, query:%s, vrid:%s, gDetect-api result:%s" % (index, query, vrid, res)
                    mail_res += "<p>" + mail_info + "</p>\n"
                
            child.wait()
                    
            index = index + 1
            
        except Exception as err:
            print(err)
            index = index + 1
            continue
    #当检测有乱码结果时才发邮件
    #if mail_res:  
        # utf8stdout("mail_res is not null, Send mail")   
    report_content = mail_title + mail_res
    DataFile.write_full_file(report_tmp_path, report_content)
    Mail.sendMail("立知&图谱结果乱码检测", report_tmp_path, mail_to)

   
 
if __name__ == '__main__':
    main()
    


