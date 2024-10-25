import os
import logging
import random
import re
import time
import utils.douyin as douyin

# from ffmpy import FFmpeg
from moviepy.editor import *
from playwright.async_api import Playwright, async_playwright

from config import conigs
from utils.file import delete_all_files
from datetime import datetime

class upload_douyin(douyin):
    def __init__(self, timeout: int, cookie_file: str):
        super(upload_douyin, self).__init__()
        """
        初始化
        :param timeout: 你要等待多久，单位秒
        :param cookie_file: cookie文件路径
        """
        self.timeout = timeout * 1000
        self.cookie_file = cookie_file

    async def upload(self, p: Playwright) -> None:
        browser = await self.playwright_init(p)
        context = await browser.new_context(storage_state=self.cookie_file, user_agent=self.ua["web"])
        page = await context.new_page()
        await page.add_init_script(path="stealth.min.js")
        await page.goto("https://creator.douyin.com/creator-micro/content/upload")
        print("正在判断账号是否登录")
        if "/creator-micro/" not in page.url:
            print("账号未登录")
            logging.info("账号未登录")
            return
        print("账号已登录")
        try:
            # 等待视频处理完毕
            await self.get_douyin_music()

            video_desc_list = self.video_path.split("\\")
            video_desc = str(video_desc_list[len(video_desc_list) - 1])[:-4]
            video_desc_tag = []
            if '#' in video_desc or '@' in video_desc:
                video_desc_tag = video_desc.split(" ")
                print("该视频有话题或需要@人")
            else:
                video_desc_tag.append(video_desc)
                print("该视频没有检测到话题")

            try:
                async with page.expect_file_chooser() as fc_info:
                    await page.locator(
                        "label:has-text(\"点击上传 或直接将视频文件拖入此区域为了更好的观看体验和平台安全，平台将对上传的视频预审。超过40秒的视频建议上传横版视频\")").click()
                file_chooser = await fc_info.value
                await file_chooser.set_files(self.video_path, timeout=self.timeout)
            except Exception as e:
                print("发布视频失败，可能网页加载失败了\n", e)
                logging.info("发布视频失败，可能网页加载失败了")

            try:
                await page.locator(".modal-button--38CAD").click()
            except Exception as e:
                print(e)
            await page.wait_for_url(
                "https://creator.douyin.com/creator-micro/content/publish?enter_from=publish_page")
            # css视频标题选择器

            css_selector = ".zone-container"
            await page.locator(".ace-line > div").click()
            tag_index = 0
            at_index = 0
            # 处理末尾标题
            video_desc_end = len(video_desc_tag) - 1
            video_desc_tag[video_desc_end] = video_desc_tag[video_desc_end][:-1]
            for tag in video_desc_tag:
                await page.type(css_selector, tag)
                if "@" in tag:
                    at_index += 1
                    print("正在添加第%s个想@的人" % at_index)
                    time.sleep(3)
                    try:
                        if len(conigs.video_at) >= at_index:
                            await page.get_by_text("抖音号 " + conigs.video_at[at_index - 1]).click(
                                timeout=5000)
                        else:
                            tag_at = re.search(r"@(.*?) ", tag + " ").group(1)
                            print("想@的人", tag_at)
                            await page.get_by_text(tag_at, exact=True).first.click(timeout=5000)
                    except Exception as e:
                        print(tag + "失败了，可能被对方拉黑了")
                        logging.info(tag + "失败了，可能被对方拉黑了")

                else:
                    tag_index += 1
                    await page.press(css_selector, "Space")
                    print("正在添加第%s个话题" % tag_index)
            print("视频标题输入完毕，等待发布")

            # 添加位置信息，只能添加当地
            if conigs.city:
                time.sleep(2)
                try:
                    city = random.choice(conigs.city_list)
                    await page.get_by_text("输入地理位置").click()
                    time.sleep(3)
                    await page.get_by_role("textbox").nth(1).fill(city)
                    await page.locator(".detail-v2--3LlIL").first.click()
                    print("位置添加成功")
                except Exception as e:
                    logging.info("位置添加失败", e)

            # 添加声明
            if conigs.declaration:
                declaration_int = conigs.declaration_int
                if declaration_int > 6:
                    raise Exception("失败，添加声明序号超出指定范围")
                declaration_content: str = (lambda content, index: content[index])(conigs.declaration_list,
                                                                                   declaration_int - 1)

                await page.locator("p.contentTitle--1Oe95:nth-child(2)").click()
                await page.get_by_role("radio", name=declaration_content, exact=True).click()
                if declaration_int == 1:
                    if len(conigs.declaration_value) < 2:
                        raise Exception("请设置拍摄地和拍摄日期")
                    await page.get_by_text("选择拍摄地点").click()
                    i1 = 0
                    value_list = (conigs.declaration_value[0]).split("-")
                    for i in value_list:
                        if i1 + 1 == len(value_list):
                            await page.locator("li").filter(has_text=i).click()
                        else:
                            await page.locator("li").filter(has_text=i).locator("svg").click()
                        i1 += 1
                    time.sleep(2)
                    await page.get_by_placeholder("设置拍摄日期").click()
                    declaration_value = conigs.declaration_value[1]
                    if declaration_value is None:
                        declaration_value = datetime.today().strftime("-%m-%d")
                    await page.get_by_title(declaration_value).locator("div").click()
                elif declaration_int == 2:
                    await page.get_by_role("radio", name="取材站外", exact=True).click()
                await page.get_by_role("button", name="确定", exact=True).click()

            is_while = False
            while True:
                # 循环获取点击按钮消息
                time.sleep(2)
                try:
                    await page.get_by_role("button", name="发布", exact=True).click()
                    try:
                        await page.wait_for_url("https://creator.douyin.com/creator-micro/content/manage")
                        logging.info("账号发布视频成功")
                        break
                    except Exception as e:
                        print(e)
                except Exception as e:
                    print(e)
                    break
                msg = await page.locator('//*[@class="semi-toast-content-text"]').all_text_contents()
                for msg_txt in msg:
                    print("来自网页的实时消息：" + msg_txt)
                    if msg_txt.find("发布成功") != -1:
                        is_while = True
                        logging.info("账号发布视频成功")
                        print("账号发布视频成功")
                    elif msg_txt.find("上传成功") != -1:
                        try:
                            await page.locator('button.button--1SZwR:nth-child(1)').click()
                        except Exception as e:
                            print(e)
                            break
                        msg2 = await page.locator(
                            '//*[@class="semi-toast-content-text"]').all_text_contents()
                        for msg2_txt in msg2:
                            if msg2_txt.find("发布成功") != -1:
                                is_while = True
                                logging.info("账号发布视频成功")
                                print("账号发布视频成功")
                            elif msg2_txt.find("已封禁") != -1:
                                is_while = True
                                logging.info("账号视频发布功能已被封禁")
                                print("账号视频发布功能已被封禁")
                    elif msg_txt.find("已封禁") != -1:
                        is_while = True
                        print("视频发布功能已被封禁")
                        logging.info("视频发布功能已被封禁")
                    else:
                        pass

                    if is_while:
                        break

        except Exception as e:
            print("发布视频失败，cookie已失效，请登录后再试\n", e)
            logging.info("发布视频失败，cookie已失效，请登录后再试")
        finally:
            delete_all_files(os.path.join(self.path, "frames"))
            delete_all_files(os.path.join(self.path, "video"))

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)