import os
import hashlib

def delete_all_files(folder_path):
    # 获取文件夹中所有文件的列表
    file_list = os.listdir(folder_path)
    for file_name in file_list:
        file_path = os.path.join(folder_path, file_name)
        # 判断是否为文件
        if os.path.isfile(file_path):
            # 删除文件
            os.remove(file_path)


def get_file_md5(file_path):
    """
    取文件md5
    :param file_path:
    :return:
    """
    with open(file_path, 'rb') as file:
        content = file.read()
    md5_obj = hashlib.md5()
    md5_obj.update(content)
    return md5_obj.hexdigest()

def find_file(find_path, file_type) -> list:
    """
    寻找文件
    :param find_path: 子路径
    :param file_type: 文件类型
    :return:
    """
    path = os.path.join(os.path.abspath(""), find_path)
    if not os.path.exists(path):
        os.makedirs(path)
    data_list = []
    for root, dirs, files in os.walk(path):
        if root != path:
            break
        for file in files:
            file_path = os.path.join(root, file)
            if file_path.find(file_type) != -1:
                data_list.append(file_path)
    return data_list