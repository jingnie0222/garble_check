import os
#数据文件类型的处理工具类

#写入到文件
def write_full_file(filepath, content, my_encoding="utf-8"):
    with open(filepath, "w+", encoding=my_encoding) as wfp:
        wfp.write(content)
    return True

#读取用\t分割的数据文件
def load_data_file(filepath, table_head, my_encoding = "utf-8"):
    ret_data = []
    with open(filepath, 'r', encoding=my_encoding) as fp:
        for line in fp:
            line = line.strip()
            data_dict_to_add = {}
            data_row = line.split("\t")
            row_index_count = 0
            for th in table_head:
                if(row_index_count >= len(data_row)):
                    break
                data_dict_to_add[th] = data_row[row_index_count]
                row_index_count = row_index_count + 1
            ret_data.append(data_dict_to_add)
    return ret_data

def read_file_intostr(filename, needstrip = False, my_encoding = "utf-8"):
    if(not os.path.exists(filename)):
        print ("cannot open " + filename + " ...", 3)
        return ""
    with open(filename, 'r', encoding=my_encoding) as myfile:
        if(needstrip):
            data = myfile.read().replace('\n', '')
        else:
            data = myfile.read()
    return data

def read_file_into_list(filename, needstrip = True, my_encoding = "utf-8", prefix = '', suffix = ''):
    readlist = []
    if(not os.path.exists(filename)):
        print ("cannot open " + filename + " ...", 3)
        return None
    with open(filename, 'r', encoding=my_encoding) as myfile:
        for line in myfile:
            if(needstrip):
                readlist.append(prefix + line.replace('\n', '') + suffix)
            else:
                readlist.append(prefix + line + suffix)
    return readlist