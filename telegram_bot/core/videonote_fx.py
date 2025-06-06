import tempfile
import numpy as np
import cv2
from moviepy.editor import VideoFileClip
from aiogram.types import Message
from aiogram import Bot
from aiogram.types import BufferedInputFile

def adjust_brightness_contrast(frame, alpha=1.7, beta=50):
    frame = cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)
    return frame

def enhance_video(input_path, output_path):
    def apply_enhance(frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        frame = adjust_brightness_contrast(frame, alpha=1.7, beta=50)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return frame

    clip = VideoFileClip(input_path)
    processed = clip.fl_image(apply_enhance)
    size = min(processed.w, processed.h)
    cropped = processed.crop(
        x_center=processed.w // 2,
        y_center=processed.h // 2,
        width=size,
        height=size
    )
    cropped.write_videofile(
        output_path, codec='libx264', audio_codec='aac',
        threads=2, fps=cropped.fps or 24,
        preset="ultrafast", bitrate="950k",
        ffmpeg_params=["-pix_fmt", "yuv420p"]
    )

def blackwhite_video(input_path, output_path):
    def apply_bw(frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        return rgb

    clip = VideoFileClip(input_path)
    processed = clip.fl_image(apply_bw)
    size = min(processed.w, processed.h)
    cropped = processed.crop(
        x_center=processed.w // 2,
        y_center=processed.h // 2,
        width=size,
        height=size
    )
    cropped.write_videofile(
        output_path, codec='libx264', audio_codec='aac',
        threads=2, fps=cropped.fps or 24,
        preset="ultrafast", bitrate="950k",
        ffmpeg_params=["-pix_fmt", "yuv420p"]
    )

def add_russian_flag_overlay(frame, alpha=0.3):
    """Наложить полупрозрачный флаг России (белый-синий-красный) сверху вниз"""
    h, w, _ = frame.shape
    flag = np.zeros_like(frame, dtype=np.uint8)
    # 1/3 белый
    flag[0:h//3, :] = (255, 255, 255)
    # 1/3 синий
    flag[h//3:2*h//3, :] = (255, 0, 0)    # OpenCV: BGR, поэтому синий - (255,0,0)
    # 1/3 красный
    flag[2*h//3:h, :] = (0, 0, 255)       # Красный - (0,0,255)
    # Смешиваем с альфой
    blended = cv2.addWeighted(frame, 1 - alpha, flag, alpha, 0)
    return blended

def russian_flag_video(input_path, output_path):
    def apply_flag(frame):
        # Переводим RGB->BGR для OpenCV
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        frame = add_russian_flag_overlay(frame, alpha=0.33)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return frame

    clip = VideoFileClip(input_path)
    processed = clip.fl_image(apply_flag)
    size = min(processed.w, processed.h)
    cropped = processed.crop(
        x_center=processed.w // 2,
        y_center=processed.h // 2,
        width=size,
        height=size
    )
    cropped.write_videofile(
        output_path, codec='libx264', audio_codec='aac',
        threads=2, fps=cropped.fps or 24,
        preset="ultrafast", bitrate="950k",
        ffmpeg_params=["-pix_fmt", "yuv420p"]
    )

async def process_videonote_fx(bot: Bot, message: Message, effect: str = "contrast"):
    if not message.reply_to_message or not getattr(message.reply_to_message, "video_note", None):
        await message.reply("❗ Ответь на кружок, чтобы его отредактировать!")
        return

    video_note = message.reply_to_message.video_note
    file = await bot.get_file(video_note.file_id)
    raw_bytes = await bot.download_file(file.file_path)

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_in:
        temp_in.write(raw_bytes.read())
        temp_in_path = temp_in.name

    temp_out_path = tempfile.mktemp(suffix=".mp4")
    try:
        if effect == "contrast":
            enhance_video(temp_in_path, temp_out_path)
        elif effect == "bw":
            blackwhite_video(temp_in_path, temp_out_path)
        elif effect == "rus":
            russian_flag_video(temp_in_path, temp_out_path)
        else:
            await message.reply("❗ Неизвестный эффект.")
            return

        with open(temp_out_path, "rb") as out_video:
            video_bytes = out_video.read()
            video_input = BufferedInputFile(video_bytes, filename="videonote.mp4")
            await bot.send_video_note(
                chat_id=message.chat.id,
                video_note=video_input,
                duration=video_note.duration,
                length=video_note.length,
                reply_to_message_id=message.message_id
            )
    except Exception as e:
        await message.reply(f"❗ Ошибка обработки: {e}")
    finally:
        import os
        try:
            os.remove(temp_in_path)
            os.remove(temp_out_path)
        except Exception:
            pass
