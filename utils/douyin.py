import os
import logging
import random
import time

import pandas as pd
import requests
# from ffmpy import FFmpeg
from moviepy.editor import *
from playwright.async_api import Playwright, async_playwright
from config import conigs
from logs import config_log
from utils.file import delete_all_files, get_file_md5
from utils.media import set_video_frame
from datetime import datetime

class douyin():
    def __init__(self):
        config_log()
        self.title = ""
        self.ids = ""
        self.video_path = ""
        self.video_ids = []
        self.page = 0
        self.path = os.path.abspath('')
        self.ua = {
            "web": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 "
                   "Safari/537.36",
            "app": "com.ss.android.ugc.aweme/110101 (Linux; U; Android 5.1.1; zh_CN; MI 9; Build/NMF26X; "
                   "Cronet/TTNetVersion:b4d74d15 2020-04-23 QuicVersion:0144d358 2020-03-24)"
        }
        if not os.path.exists(conigs.video_path):
            os.makedirs(conigs.video_path)
        if conigs.remove_video:
            delete_all_files(conigs.video_path)
            delete_all_files(os.path.join(self.path, "frames"))

    async def playwright_init(self, p: Playwright, headless=None):
        """
        初始化playwright
        """
        if headless is None:
            headless = False

        browser = await p.chromium.launch(headless=headless,
                                          chromium_sandbox=False,
                                          ignore_default_args=["--enable-automation"],
                                          channel="chrome"
                                          )
        return browser

    async def get_douyin_music(self):
        """
        获取抖音Top50音乐榜单
        :return:
        """
        url = f"https://api3-normal-c-hl.amemv.com/aweme/v1/chart/music/list/?request_tag_from=rn&chart_id=6853972723954146568" \
              f"&count=100&cursor=0&os_api=22&device_type=MI 9" \
              f"&ssmix=a&manifest_version_code=110101&dpi=240&uuid=262324373952550&app_name=aweme&version_name=11.1.0&ts={round(time.time())}" \
              f"&cpu_support64=false&app_type=normal&ac=wifi&host_abi=armeabi-v7a&update_version_code" \
              f"=11109900&channel=douyinw&_rticket={round(time.time() * 1000)}&device_platform=android&iid=157935741181076" \
              f"&version_code=110100&cdid=02a0dd0b-7ed3-4bb4-9238-21b38ee513b2&openudid=af450515be7790d1&device_id=3166182763934663" \
              f"&resolution=720*1280&os_version=5.1.1&language=zh&device_brand=Xiaomi&aid=1128&mcc_mnc=46007"

        res = requests.get(url, headers={"User-Agent": self.ua["app"]}).json()
        x = random.randint(0, len(res["music_list"]) - 1)
        music_list = res["music_list"][x]
        self.title = f"—来自：音乐榜单的第{(x + 1)}个音乐《{music_list['music_info']['title']}》"
        self.ids = music_list["music_info"]["id_str"]
        print("music_id:", self.ids)
        try:
            await self.get_filter()
        except Exception as e:
            logging.info("根据音乐ID获取视频失败", e)

    def get_web_userinfo(self, unique_id) -> str:
        """
        根据抖音号获取用户信息
        :param unique_id:
        :return:
        """
        url = "https://www.iesdouyin.com/web/api/v2/user/info/?unique_id={}".format(unique_id)
        res = requests.get(url, headers={"User-Agent": self.ua["web"]}).json()
        n = 0
        while True:
            n += 1
            try:
                nickname = res["user_info"]["nickname"]
                break
            except KeyError:
                print("获取用户昵称失败！")
            if n > 3:
                nickname = ''
                break
        return nickname

    async def get_douyin_music_video(self, p: Playwright, music_id=None):
        """
        根据音乐id获取音乐视频列表
        :return:
        """

        if music_id is None:
            music_id = self.ids if self.ids else "7315704709279550259"

        browser = await self.playwright_init(p, headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.add_init_script(path="stealth.min.js")
        await page.goto("https://www.douyin.com/music/" + music_id)

        pages = []
        for x in range(0, 40):
            pages.append(x * 10)

        self.page = random.choice(pages)

        url = (f"https://www.douyin.com/aweme/v1/web/music/aweme/?device_platform=webapp&aid=6383&channel"
               f"=channel_pc_web&count=12&cursor={self.page}&music_id={music_id}&pc_client_type=1&version_code=170400"
               f"&version_name=17.4.0&cookie_enabled=true&screen_width=1920&screen_height=1280&browser_language=zh-CN"
               f"&browser_platform=Win32&browser_name=Chrome&browser_version=123.0.0.0&browser_online=true"
               f"&engine_name=Blink&engine_version=123.0.0.0&os_name=Windows&os_version=10&cpu_core_num=32"
               f"&device_memory=8&platform=PC&downlink=10&effective_type=4g&round_trip_time=100"
               )

        res = await page.evaluate("""() => {
            function queryData(url) {
               var p = new Promise(function(resolve,reject) {
                   var e={
                           "url":"%s",
                           "method":"GET"
                         };
                    var h = new XMLHttpRequest;
                    h.responseType = "json";
                    h.open(e.method, e.url, true);
                    h.setRequestHeader("Accept","application/json, text/plain, */*");
                    h.setRequestHeader("Host","www.douyin.com"); 
                    h.setRequestHeader("Referer","https://www.douyin.com/music/%s"); 
                    h.setRequestHeader("User-Agent","Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36");   
                    h.onreadystatechange = function() {
                         if(h.readyState === 4 && h.status === 200) {
                              resolve(h.response);
                         } else {}
                    };
                    h.send(null);
                    });
                    return p;
                }
            var p1 = queryData();
            res = Promise.all([p1]).then(function(result){
                    return result
            })
            return res
        }""" % (url, music_id))

        try:
            res = res[0]

            verify_reason_values = []
            video_duration_values = []
            remove_custom_verify = []

            # 这里把要筛选的条件值加入到筛选列表当中
            for i in res["aweme_list"]:
                verify_reason_values.append(i["author"]["enterprise_verify_reason"])
                video_duration_values.append(i["video"]["duration"])
                remove_custom_verify.append(i["author"]["custom_verify"])

            verify_reason = {
                "verify_reason": verify_reason_values,
                "duration": video_duration_values,
                "custom_verify": remove_custom_verify
            }

            df = pd.DataFrame(verify_reason)
            if conigs.remove_enterprise and conigs.remove_images and conigs.remove_custom_verify:
                # 判断是否满足所有条件
                jd = df[(df['verify_reason'] == "") & (df['duration'] >= (conigs.duration * 1000)) & (
                        df['custom_verify'] == "")]
                # 判断是否有满足条件的数据
                if len(jd.index.values) > 0:
                    dd = jd.sample()
                    # print(dd.index.values)
                    index = dd.index.values[0]
                    video_list = res['aweme_list'][index]
                    return video_list
                else:
                    return "所有都条件不满足"
            else:
                index = random.randint(0, len(res['aweme_list']) - 1)
                video_list = res['aweme_list'][index]
                return video_list
        except Exception as e:
            logging.info(e)
            return "error"

    async def get_filter(self):
        """
        使用pands过滤数据
        :return:
        """
        for i in range(1, 5):
            async with async_playwright() as p:
                res = await self.get_douyin_music_video(p)
            if isinstance(res, dict):
                if conigs.remove_enterprise and conigs.remove_images and conigs.remove_custom_verify:
                    aweme_id = res['aweme_id']
                    with open(os.path.join(self.path, "video_id_list.txt"), encoding="utf-8", mode="r") as f:
                        self.video_ids = f.read().split(",")
                    if aweme_id not in self.video_ids:
                        self.video_ids.append(aweme_id)
                        break
                    else:
                        print(f"该视频:{aweme_id}已经发送过了本次不再发送")
                else:
                    break
            elif isinstance(res, str):
                print(res)
        if res == 'error': return
        aweme_id = res['aweme_id']
        uri = res["video"]["play_addr_h264"]["url_list"][0]
        nickname = res['author']['nickname']
        # print(json.dumps(video_list))
        print("url:", uri)
        print("nickname:", nickname)
        print("video_id:", aweme_id)

        # 获取自定义的视频标题
        page_index = 1 if self.page == 0 else round(self.page / 12 + 1)
        self.title += f"第{page_index}页@{nickname} 的作品"

        day = datetime.now().day
        if conigs.today:
            # video_title_list = video_title_list2 if day % 2 == 0 else video_title_list1
            if day % 2 == 0:
                conigs.title_random = False
                video_title_list = conigs.video_title_list2
            else:
                video_title_list = conigs.video_title_list1
        else:
            video_title_list = conigs.video_title_list1

        if not conigs.title_random:
            if len(video_title_list) > 5:
                print("错误，话题数不能大于5")
        desc = random.choice(video_title_list) if conigs.title_random else ''.join(
            video_title_list)

        nickname = ''
        for at in conigs.video_at:
            nickname += f"@{self.get_web_userinfo(at)} "
        desc += nickname + self.title
        headers = {"User-Agent": self.ua["web"], "Referer": uri}
        reb = requests.get(uri, headers=headers).content
        self.video_path = os.path.join(conigs.video_path, desc + ".mp4")
        with open(self.video_path, mode="wb") as f:
            f.write(reb)
            print("处理前md5：", get_file_md5(self.video_path))
            print("正在处理视频")
            # clip = VideoFileClip(self.video_path)
            # clip.subclip(10, 20)  # 剪切
            await set_video_frame(self.video_path)
            # self.video_path这个文件名不能改，上传就是上传这个
            self.video_path = os.path.join(conigs.video_path, desc + "3.mp4")
            # clip.write_videofile(self.video_path)  # 保存视频
            print("处理后md5：", get_file_md5(self.video_path))
            print("视频处理完毕")
            with open(os.path.join(self.path, "video_id_list.txt"), encoding="utf-8", mode="w") as f:
                f.write(",".join(self.video_ids)[1:])