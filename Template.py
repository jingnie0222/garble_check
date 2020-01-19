#fanghuizhi@sogou-inc.com
#HTML生成类python
import time,datetime,hashlib,os
#import DBHelper
import urllib
import json

#问题计数器
class Counter:
    def __init__(self, name):
        self.name = name
        self.error_dict = {}
        
    def get_counter_dict(self):
        return self.error_dict
        
    def add_counter(self, i_key):
        if not i_key in self.error_dict:
            self.error_dict[i_key] = 1
        else:
            self.error_dict[i_key] = self.error_dict[i_key] + 1
            
    def sub_counter(self, i_key):
        if i_key in self.error_dict:
            self.error_dict[i_key] = self.error_dict[i_key] - 1
            
    def output_default_html(self, table_head):
        tmp_data = []
        for k,v in self.error_dict.items():
            tmp_data.append([k,v])
        return html_table(self.tmp_data, table_head)

#故障现场，输入名称、报告路径、Html访问前端路径，自动拼接
class ReportScene:
    def __init__(self, name, local_report_dir, remote_report_dir, type = "default", url = "", comment = "", uuid = ""):
        self.local_report_dir = local_report_dir
        self.remote_report_dir = remote_report_dir
        self.md5_name = hashlib.md5(name.encode("utf-8")).hexdigest()
        if not os.path.exists(local_report_dir):
            os.makedirs(local_report_dir)
            
        self.checkpoints = []
        self.name = name
        self.type = type
        self.comment = comment
        self.url = url
        self.uuid = uuid
        
    def get_local_png_path(self):
        return "".join([self.local_report_dir, self.md5_name, ".png"])
        
    def get_local_html_path(self):
        return "".join([self.local_report_dir, self.md5_name, ".html"])
        
    def get_remote_png_path(self):
        return "".join([self.remote_report_dir, self.md5_name, ".png"])
        
    def get_remote_html_path(self):
        return "".join([self.remote_report_dir, self.md5_name, ".html"])
        
    #添加检查点，如果为True则产生reason summary的时候不返回，如果False则会返回reason。
    def add_checkpoint(self, assert_var, reason_content):
        self.checkpoints.append({"is_pass" : assert_var, "reason_content" : reason_content})
        
    def set_checkpoint(self, in_checkpoints):
        self.checkpoints = in_checkpoints
        
    def get_checkpoints_reason(self):
        return_data = []
        for row in self.checkpoints:
            if(not row["is_pass"]):
                return_data.append(row["reason_content"])
        #print ("got "+ str(len(return_data)) + " checkpoints...")
        return ",".join(return_data)
        
    #写入现场的html数据
    def write_report_content(self, content):
        with open(self.get_local_html_path(), "w+", encoding="utf-8") as wfp:
            wfp.write(content)
        return True
        
    def set_comment(self, comment):
        self.comment = comment
        
    def init_exists_db(self, db):
        self.db = db
        self.db_table_name = "special_check_scene"
        
    def init_db(self, config_file, config_key):
        self.db = DBHelper.init_db(config_file, config_key)
        self.db_table_name = "special_check_scene"
        
    #向DB里插入某个case，如果已经存在则进行更新
    def db_init_scene(self):
        if(self.db is None):
            return 0
        ins_id = 0
        fetch_rs = self.db.fetch_first("SELECT * FROM " + self.db_table_name + " WHERE type='" + self.type + "' AND query='" + self.name + "' LIMIT 1")
        if(fetch_rs is None):
            in_data = {"url": self.url, "type": self.type, "query": self.name, "comment": self.comment, "error_count": 1, "scene_url": self.get_remote_html_path(), "uuid": self.uuid}
            self.db_insert(in_data) #如果不存在插入新的记录
            ins_id = self.db.insert_id()
        else:
            self.db.add_value(self.db_table_name, "error_count", '1', 'scene_id=' + str(fetch_rs["scene_id"])) #有的话增加1条
            ins_id = fetch_rs["scene_id"]
        return ins_id
            
    def db_insert(self, in_data):
        if(self.db is None):
            return None
        #数据实例...
        #in_data = {"type": "wap_simi", "url": "http://m.sogou.com/web/searchList.jsp?keyword=mechinelearn", "comment": "新闻太旧"}
        self.db.insert(self.db_table_name, in_data)
        result_id = self.db.insert_id()
        return result_id
        
#报告类
class ReportData:
    #name为报告名称， report_headinfo为报告数据的表头list
    def __init__(self, name, report_headinfo, print_interval = 0, print_excepted_count = 0):
        self.name = name
        self.report_headinfo = report_headinfo
        self.print_interval = print_interval #当大于0的时候，当add_data的时候，每间隔 print_interval 个数据就print一次报告
        self.print_excepted_count = print_excepted_count #预期抓取的数据总量
        self.set_start_time()
        #一些报告现场相关url的变量，用于保存文件，并在最终生成报告邮件里给用户点出
        self.fetch_count = 0 #总共抓取了多少数据，因为报告里只记录了错误数据，因此需要有这一个计数器
        self.error_count = 0 #手动错误计数器，大于0的时候则不统计error_data的行数
        self.error_data = []
        self.print_message = ''
        self.start_time = 0
        self.end_time = 0
        self.custom_error_count_mode = False
        self.scene_slot = [] #储存属于这个report的所有error scene。方便产生报告的时候再update一下scene对应的db表，把对应关系写进去.这样就可以从scene的列表打开

        print ("Report init.print_excepted_count:" + str(print_excepted_count) + ",print_interval:"+ str(print_interval))
        
    def add_fetch_count(self):
        self.fetch_count = self.fetch_count + 1
        if(self.print_interval > 0 and self.fetch_count % self.print_interval == 0):
            print ("".join(["[F2A Autotest]", self.print_message, "Process :" , str(self.fetch_count), '/', str(self.print_excepted_count)]))
            
    def add_error_count(self):
        self.error_count = self.error_count + 1
        
    def set_start_time(self):
        self.start_time = time.time()
        
    def set_end_time(self):
        self.end_time = time.time()
        
    def set_custom_error_count_mode(self):
        self.custom_error_count_mode = True
        
    #重新设置报告间隔
    def set_process_setting(self, print_interval, print_excepted_count):
        self.print_interval = print_interval
        self.print_excepted_count = print_excepted_count
        
    def set_process_message(self, in_message):
        self.print_message = in_message
        
    def add_data(self, data_row):
        self.error_data.append(data_row)
        
    def get_table_summary(self): #获取当前数据的表格形式统计报告HTML
        return "".join([html_h3_title(self.name), html_p_error_rate(self.get_error_count(), self.fetch_count), html_p_time(self.start_time, self.end_time), html_table(self.error_data, self.report_headinfo)])
        
    def get_fetch_count(self):
        return self.fetch_count
        
    def get_error_count(self):
        if(self.custom_error_count_mode):
            return self.error_count
        else:
            return len(self.error_data)
        
    def get_report_headinfo(self):
        return self.report_headinfo
        
    def add_scene_id(self, scene_id):
        if(not scene_id in self.scene_slot):
            self.scene_slot.append(str(scene_id))
            
    def get_scene_slot(self):
        return self.scene_slot
        
    def process_db(self, db, type, update_scene = True):
        db.insert("special_check_result", {"type" : type, "report_content" : self.get_table_summary(), "word_count" : self.get_fetch_count(), "error_count" : self.get_error_count()})
        summary_id = db.insert_id()
        print ("check summary id:" + str(summary_id))
        sc_slot = self.get_scene_slot()
        if(len(sc_slot) > 0 and update_scene):
            db.update("special_check_scene", {"summary_id": summary_id}, "".join(["scene_id IN (" + str(",".join(sc_slot)) + ")" ]))
        return True
        
#判断是否为中文字符，用来过滤掉vrfetch里url里直接含有中文的字符，减少误报。
def is_chinese(uchar):
    """判断一个unicode是否是汉字"""
    if uchar >= u'\u4e00' and uchar<=u'\u9fa5':
        return True
    else:
        return False
        
def is_chinese_str(in_string):
    for cchar in in_string:
        if(is_chinese(cchar)):
            return True
    return False
        
#将wap点出结果的href转化为真实url的方法
def convert_wap_to_real_url(get_url):
    if(get_url is None):
        return ""
    #如果没有 url 参数，直接返回原文
    if(not "url=" in get_url):
        return get_url
    real_url = ""
    try:
        real_url = get_url.split("url=")[1]
        if('&' in real_url):
            real_url = real_url.split("&")[0]
        real_url = urllib.parse.unquote(real_url)
    except Exception as e:
        print ("".join(["oops, error on convert:", get_url]))
        print (e)
        return ""
    return real_url
        
#读取json
def load_json(in_str):
    try:
        return json.loads(in_str)
    except Exception as e:
        return None
        
#根据条件，拿查询词制作最终访问url
def url_make_for_fetch(word, is_wap = True, custom_pre = '', debug = False):
    debug_append = ''
    if(debug):
        if(is_wap):
            debug_append = '&dbg=on'
        else:
            debug_append = '&wxc=on'
    
    #给个前置，支持访问线下环境
    if(custom_pre == ""):
        if(is_wap):
            custom_pre = "http://m.sogou.com.inner/web/searchList.jsp?keyword="
        else:
            custom_pre = "http://www.sogou.com.inner/web?ie=utf8&query="
    return "".join([custom_pre, urllib.parse.quote(word), debug_append])
                
def url_make_for_fetch_default(word, is_wap):
    return url_make_for_fetch(word, is_wap, custom_pre = '')
    
#转义html常用的代码html字符
def html_htmlspecialchars(in_str):
    return in_str.replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
        
def html_general_css():
    return '<style>.bx{border: 1px solid #cbcbcb;empty-cells: show;border-collapse: collapse;border-spacing: 0;width: 95%} .bx thead{background-color: #5F9EA0;color: #FFFFFF ;text-align: left;vertical-align: bottom;} .bx td{border:#CCC solid 1px;} .tip {font-weight:700}</style>'

def html_h3_title(content):
    return "".join(["<h3>", content, "</h3>"])
    
def html_p(content):
    return "".join(["<p>", content, "</p>"])

def html_p_spe(content):
    return "".join(['<p style="font-family:verdana;font-size:90%;color:green">', content, "</p>"])
    
#获得图片img
def html_img(img_url):
    return "".join(['<img src="', img_url, '" title=""/>'])
    
#用来报告里添加注释，标示原始抓取数据来源
def html_p_data_source(content):
    return "".join(["<p>原始抓取数据来源：", content, "</p>"])
    
#把时间戳转化为目录名称
def html_timestamp_dirable(in_timestamp):
    return datetime.datetime.fromtimestamp(in_timestamp).strftime('%Y-%m-%d-%H-%M-%S')
    
#把时间戳转化为可读的形式
def html_timestamp_readable(in_timestamp):
    return datetime.datetime.fromtimestamp(in_timestamp).strftime('%Y-%m-%d %H:%M:%S')
    
#把时间戳转化为可读的形式，只有YMD
def html_timestamp_ymd_readable(in_timestamp):
    return datetime.datetime.fromtimestamp(in_timestamp).strftime('%Y-%m-%d')
    
#生成起始时间和最终输出
def html_p_time(start_time, end_time):
    return "".join(["<p>开始时间：<span>", html_timestamp_readable(start_time), "</span> 结束时间：<span>", html_timestamp_readable(end_time), "</span></p>", "<p>耗时：", str(end_time - start_time), "（秒）</p>"])

#生成错误比例    
def html_calc_error_rate(bad_result, total_result):
    if(bad_result is None or (total_result is None)):
        return '-0.00%' #对异常输入做容错
    if(total_result == 0):
        return '-0.00%' #对异常输入做容错
    return "".join([str((bad_result / total_result) * 100 )[0:4], '%'])
    
#生成错误比例的文字
def html_p_error_rate(bad_result, total_result):
    if(total_result == 0):
        return '-0.00%'
    return "".join([ '<p>抓取发现错误率：', str(bad_result), '/',str(total_result), '(', html_calc_error_rate(bad_result, total_result), ')', '</p>'])
    
#生成html的table格式
def html_table(data, table_head = [], table_class="bx", dict_keys = []):        
    return_data = ["".join(['<table class="' , table_class , '">'])]
    return_data.append("<thead><tr>")
    if(len(table_head) > 0):
        return_data.append('<td>')
        return_data.append("</td><td>".join(table_head))
        return_data.append('</td>')
    return_data.append("</tr></thead>\n<tbody>")
    if(len(data) > 0):
        for row in data:
            if(isinstance(row, dict)): #支持对dict型的按指定key转换
                inst_data_row = []
                for s_key in dict_keys:
                    inst_data_row.append(str(data.get(s_key, ""))) #这里做str的处理，省得传入int的时候失败
                row = inst_data_row
            return_data.append('<tr><td>')
            return_data.append("</td><td>".join(row))
            return_data.append("</td></tr>\n")
    return_data.append("</tbody></table>")
    return "".join(return_data)
    
def html_a_link(link, content):
    return "".join(['<a href="', link, '" target="_blank">', content, '<br />', '</a>'])

def double_dict_to_html_table(data, word_count, table_head = [], dict_keys = []):
    return_data = []
    return_data.append("<table border=\"2\">")
    return_data.append("<tr>")
    if(len(table_head) > 0):   #处理表格头部信息
        return_data.append('<th>')
        return_data.append("</th><th>".join(table_head))
        return_data.append('</th></tr>')

    if(len(data) > 0):
        for row in data:
            return_data.append('<tr><td>')
            return_data.append(row)

            inst_data_row = []
            for s_key in dict_keys:
                value = data[row].get(s_key, "")
                percent = format((value/word_count)*100, '.2f')
                inst_data_row.append(str(value) + "(" + percent + "%)") #这里做str的处理，省得传入int的时候失败
            row = inst_data_row
            return_data.append('</td><td>')
            return_data.append("</td><td>".join(row))
            return_data.append("</td></tr>\n")
    return "".join(return_data) + "</table>"

def single_dict_to_html_table(data, table_head = [], dict_keys = []):
    return_data = []
    return_data.append("<table border=\"2\">")
    return_data.append("<tr>")
    if(len(table_head) > 0):   #处理表格头部信息
        return_data.append('<th>')
        return_data.append("</th><th>".join(table_head))
        return_data.append('</th></tr>')

    return_data.append('<tr><td>')
    inst_data_row = []
    if(len(data) > 0):
        for s_key in dict_keys:
            inst_data_row.append(str(data.get(s_key, "")))
        return_data.append("</td><td>".join(inst_data_row))
        return_data.append("</td></tr>\n")

    return "".join(return_data) + "</table>"