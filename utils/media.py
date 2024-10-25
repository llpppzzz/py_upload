import os
import cv2
import logging

from tqdm import tqdm
from config import conigs
from PIL import Image
from utils.file import delete_all_files

async def merge_images_video(image_folder, output_file, video_path, fps=None):
    """
    把图片合并成视频并添加背景音乐
    :param image_folder: 图片文件夹路径
    :param output_file: 输出视频文件路径
    :param video_path: 待提取背景音乐的视频文件路径
    :param fps:
    :return:
    """
    # 获取文件夹内所有图片的列表
    image_list = os.listdir(image_folder)
    # 获取图片总数量
    index = len(image_list)

    # 获取第一张图片的大小作为视频分辨率
    first_img = Image.open(os.path.join(image_folder, image_list[0]))
    if fps is None:
        fps = 30
    try:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # MP4格式
        videowrite = cv2.VideoWriter(output_file, fourcc, fps, first_img.size)
        img_array = []

        start_frame = conigs.start_frame

        for filename in [f'./frames/{i}.jpg' for i in range(start_frame, index + start_frame)]:
            img = cv2.imread(filename)
            if img is None:
                print("is error!")
                continue
            img_array.append(img)
        # 合成视频
        with tqdm(total=len(img_array), desc="图片合成进度") as pbar:
            for i in range(len(img_array)):
                img_array[i] = cv2.resize(img_array[i], first_img.size)
                videowrite.write(img_array[i])
                pbar.update(1)
                # print('第{}张图片合成成功'.format(i))
        # 关闭视频流
        videowrite.release()

        print('开始添加背景音乐！')
        # 从某个视频中提取一段背景音乐
        fps = 48000
        audio_file = AudioFileClip(video_path, fps=fps)
        # 将背景音乐写入.mp3文件
        output_dir = "music/"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        else:
            delete_all_files(output_dir)
        audio = CompositeAudioClip([audio_file])
        audio.write_audiofile(os.path.join(output_dir, "background.mp3"), fps=fps)
        dd_path = output_file[:-5] + "3.mp4"
        # 2种方案
        # 方案一 使用moviepy，内存更小
        clip = VideoFileClip(output_file)
        clip = clip.set_audio(audio)
        clip.write_videofile(dd_path)

        # 方案二 使用ffmpeg，内存更大
        # ff = FFmpeg(
        #     inputs={output_file: None, output_dir + '/background.mp3': None},
        #     outputs={dd_path: '-map 0:v -map 1:a -c:v copy -c:a aac -shortest'},
        #     global_options='-stream_loop -1',  # 全局参数 视频时长小于音乐时长时将循环视频
        #     # executable=r'E:\易语言\ffmpeg\ffmpeg-5.0.1-essentials_build\bin\ffmpeg.exe'
        # )
        # ff.run()
        print('背景音乐添加完成！')

    except Exception as e:
        print("发生错误：", e)
        logging.info(e)


async def set_video_frame(video_path):
    """
    抽取视频帧，返回fps用于后面合成
    :param video_path: 视频文件路径
    :return:
    """
    # 打开视频文件
    video = cv2.VideoCapture(video_path)

    # 获取视频的帧数、每秒帧数等信息
    frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = video.get(cv2.CAP_PROP_FPS)

    # 设置要提取的帧数范围
    start_frame = conigs.start_frame - 1  # 起始帧
    end_frame = frame_count - (conigs.end_frame + 1)  # 结束帧

    # 创建保存抽取帧的目录
    output_dir = 'frames/'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        delete_all_files(output_dir)

    # 定位到指定的起始帧
    video.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    # 按照指定的间隔提取并保存帧图像
    with tqdm(total=(end_frame - start_frame), desc="视频抽帧进度") as pbar:
        for i in range(start_frame + 1, end_frame + 1):
            ret, frame = video.read()
            if not ret:
                break
            output_file = os.path.join(output_dir, f"{i}.jpg")
            cv2.imwrite(output_file, frame)
            pbar.update(1)
            # print(f"已处理 {i + 1}/{end_frame + 1} 帧")

    # print("所有帧都已成功抽取！")
    # 关闭视频流
    video.release()
    await merge_images_video(os.path.join(os.path.abspath(""), "frames"), video_path[:-4] + "2.mp4", video_path, fps)