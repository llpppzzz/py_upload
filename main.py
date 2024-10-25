import asyncio
import os

from utils.file import find_file
import utils.upload_douyin as upload_douyin

def run():
    cookie_list = find_file("cookie", "json")
    x = 0
    for cookie_path in cookie_list:
        x += 1
        cookie_name: str = os.path.basename(cookie_path)
        print("正在使用[%s]发布作品，当前账号排序[%s]" % (cookie_name.split("_")[1][:-5], str(x)))
        app = upload_douyin(60, cookie_path)
        asyncio.run(app.main())


if __name__ == '__main__':
    run()
    # print("任务开始运行")
    # scheduler = BlockingScheduler(timezone='Asia/Shanghai')
    # scheduler.add_job(run, 'interval', minutes=120, misfire_grace_time=900)
    # scheduler.start()