import os
import time
import datetime
from PIL import Image
from http.server import HTTPServer, BaseHTTPRequestHandler
from weather_landscape import WeatherLandscape
import secrets
import socket
import threading

SERV_IPADDR = "0.0.0.0"
SERV_PORT = 3355

EINKFILENAME = "test.bmp"
USERFILENAME = "test1.bmp"
FAVICON = "favicon.ico"

FILETOOOLD_SEC = 60 * 15  # 每 15 分钟刷新一次（以秒为单位）
HTML_UPDATE_INTERVAL = 60  # 每 60 秒刷新一次 HTML 页面

WEATHER = WeatherLandscape()

class WeatherLandscapeServer(BaseHTTPRequestHandler):

    def do_GET_sendfile(self, filepath: str, mimo: str):
        try:
            with open(filepath, "rb") as f:
                databytes = f.read()
        except Exception as e:
            databytes = None
            print("File read error '%s' :%s" % (filepath, str(e)))

        if databytes is not None:
            self.send_response(200)
            self.send_header("Content-type", mimo)
        else:
            self.send_response(404)

        self.end_headers()
        if databytes is not None:
            self.wfile.write(databytes)

    def do_GET(self):
        # 去除查询参数（例如 ?timestamp=123456）以获取文件路径
        path = self.path.split('?')[0]  # 分离 URL 和查询参数
        print("GET:", path)  # 打印请求路径，便于调试
    
        if path == '/':
            path = '/index.html'  # 将根路径重定向到 index.html
    
        # 确保路径开始时有 "/index.html"
        if path.startswith('/index.html'):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(bytes(self.IndexHtml(), 'utf-8'))
            return
    
        # 处理 favicon 请求
        if path.startswith('/' + FAVICON):
            self.do_GET_sendfile(FAVICON, "image/ico")
            return
    
        # 处理图片请求
        if path.startswith('/' + EINKFILENAME) or path.startswith('/' + USERFILENAME):
            # 根据请求路径生成完整的图片文件路径
            file_name = WEATHER.TmpFilePath(path[1:])
            self.do_GET_sendfile(file_name, "image/bmp")
            return

         # 处理 NoSleep.min.js 的请求
        if path.startswith('/NoSleep.min.js'):
            self.do_GET_sendfile('NoSleep.min.js', 'application/javascript')
            return
    
        # 如果路径不被识别，则返回 403 错误
        print("Path not accessible:", path)
        self.send_response(403)


    def IsFileTooOld(self, filename):
        return (not os.path.isfile(filename)) or ((time.time() - os.stat(filename).st_mtime) > FILETOOOLD_SEC)

    def IndexHtml(self):
        return """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0">
                <meta name="apple-mobile-web-app-capable" content="yes" />
                <title>Weather as Landscape</title>
                <style>
                    body {{
                        margin: 0;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        width: 100vw;
                        overflow: hidden;
                        background-color: rgb(190, 200, 207);
                        user-select: none;
                        pointer-events:none;
                    }}
                    img {{
                        width: 100%;
                        height: 100%;
                        object-fit: contain;
                    }}
                </style>
            </head>
            <body>
                <img id="weatherImage" src="{user_file}?timestamp={timestamp}" alt="Weather">
                <script src="./NoSleep.min.js"></script>
                <script>
                    var noSleep = new NoSleep();
                    var wakeLock = null;
    
                    async function requestWakeLock() {{
                        if ('wakeLock' in navigator) {{
                            try {{
                                wakeLock = await navigator.wakeLock.request('screen');
                                console.log("Wake lock acquired");
                                noSleep.enable();
    
                                wakeLock.addEventListener('release', () => {{
                                    console.log("Wake lock released");
                                    wakeLock = null;
                                }});
                            }} catch (err) {{
                                keepScreenActiveFallback();
                                console.error(`Wake lock failed: ${{err.name}}`);
                            }}
                        }} else {{
                            keepScreenActiveFallback();
                            console.warn("Wake Lock API is not supported in this browser");
                        }}
                    }}
                    requestWakeLock();
    
                    function releaseWakeLock() {{
                        noSleep.disable();

                        if (wakeLock !== null) {{
                            wakeLock.release().then(() => {{
                                console.log("Wake lock manually released");
                                wakeLock = null;
                            }});
                        }}
                    }}
    
                    function keepScreenActiveFallback() {{
                        noSleep.enable();

                        const video = document.createElement('video');
                        video.src = 'data:video/mp4,';
                        video.loop = true;
                        video.muted = true;
                        video.play();
                        console.log('Fallback: Using video to keep the screen active');
                    }}
    
                    function updateImage() {{
                        var weatherImage = document.getElementById("weatherImage");
                        var timestamp = new Date().getTime();
                        weatherImage.src = "{user_file}?timestamp=" + timestamp;
                        setTimeout(updateImage, {update_time} * 1000);
                    }}
                    updateImage();
    
                    function toggleFullScreen() {{
                        var element = document.documentElement;
    
                        // iOS-specific full screen handling
                        if (navigator.userAgent.includes('iPhone') || navigator.userAgent.includes('iPad')) {{
                            const body = document.body;
                            body.style.height = '100%';
                            body.style.width = '100%';
                            body.style.overflow = 'hidden';
                            body.style.position = 'fixed';
                            console.log('iOS: Adjusted for full screen experience');
                        }}
    
                        if (document.fullscreenElement || document.webkitFullscreenElement) {{
                            if (document.exitFullscreen) {{
                                document.exitFullscreen();
                            }} else if (document.webkitExitFullscreen) {{
                                document.webkitExitFullscreen();
                            }}
                        }} else {{
                            if (element.requestFullscreen) {{
                                element.requestFullscreen();
                            }} else if (element.webkitRequestFullscreen) {{
                                element.webkitRequestFullscreen();
                            }}
                        }}
                    }}
    
                    document.addEventListener('visibilitychange', () => {{
                        if (document.visibilityState === 'visible') {{
                            console.log("Page is visible, requesting wake lock again...");
                            requestWakeLock();
                        }} else {{
                            console.log("Page is hidden, releasing wake lock...");
                            releaseWakeLock();
                        }}
                    }});
    
                    window.onload = function() {{
                        document.body.addEventListener('click', toggleFullScreen);
                    }};
                </script>
            </body>
            </html>
        """.format(user_file=USERFILENAME, update_time=HTML_UPDATE_INTERVAL, timestamp=str(time.time()))

def periodic_refresh():
    """
    定期刷新天气图像，同时将背景色修改为 #F0F0F0，并打印调试信息
    """
    while True:
        try:
            print("[INFO] Checking if weather images need to be updated...")
            user_file_name = WEATHER.TmpFilePath(USERFILENAME)
            eink_file_name = WEATHER.TmpFilePath(EINKFILENAME)

            # 检查文件是否过期
            if not os.path.isfile(user_file_name) or not os.path.isfile(eink_file_name) or \
                    (time.time() - os.path.getmtime(user_file_name)) > FILETOOOLD_SEC:
                print("[INFO] Weather images are outdated or missing. Refreshing...")

                # 调用 MakeImage 方法生成原始天气图像
                img = WEATHER.MakeImage()
                print(f"[DEBUG] Original Image Info:")
                print(f"- Size: {img.size}")
                print(f"- Mode: {img.mode}")

                # 如果图像模式是 '1'，将其转换为 RGBA 模式
                if img.mode == '1':
                    img = img.convert('RGBA')
                    print("[INFO] Converted image to RGBA mode.")

                # 创建背景为 #F0F0F0 (240, 240, 240) 的新图像，并填充背景色 216, 216, 205 190, 200, 207
                bg_color = (190, 200, 207)  # 背景颜色
                bg_image = Image.new("RGBA", img.size, bg_color + (255,))  # 背景带不透明度

                # 确保背景颜色正确应用
                print(f"[DEBUG] Background image created with color: {bg_color}")

                # 获取原图数据并逐像素检查透明区域
                img_data = img.getdata()
                new_img_data = []

                # 遍历原图数据，替换白色像素为背景色
                for i, pixel in enumerate(img_data):
                    # 如果是白色像素，替换为背景色
                    if pixel == (255, 255, 255, 255):  # 白色像素
                        new_img_data.append(bg_color + (255,))
                    else:
                        new_img_data.append(pixel)

                # 更新图像数据
                img.putdata(new_img_data)

                # 将处理后的图像粘贴到背景上
                bg_image.paste(img, (0, 0), img)

                # 检查粘贴后的图像左上角像素
                top_left_pixel_after_paste = bg_image.getpixel((0, 0))
                print(f"[DEBUG] Top-left Pixel Color (After paste) (RGB): {top_left_pixel_after_paste} (Expected: {bg_color})")

                # 转换为 RGB 模式（去除透明度）
                final_image = bg_image.convert("RGB")
                print(f"[DEBUG] Final Image Info (with background):")
                print(f"- Size: {final_image.size}")
                print(f"- Mode: {final_image.mode}")

                # 检查最终图像的左上角像素
                top_left_pixel = final_image.getpixel((0, 0))
                print(f"[DEBUG] Top-left Pixel Color (RGB): {top_left_pixel} (Expected: {bg_color})")

                # 保存用户文件
                final_image.save(user_file_name)
                print(f"[INFO] User image saved as {user_file_name}")

                # 生成 Eink 图像
                eink_image = final_image.rotate(-90, expand=True).transpose(Image.FLIP_TOP_BOTTOM)
                eink_image.save(eink_file_name)
                print(f"[INFO] Eink image saved as {eink_file_name}")

                print("[INFO] Weather images updated successfully.")
            else:
                print("[INFO] Weather images are up to date.")
        except Exception as e:
            print(f"[ERROR] Error refreshing weather images: {str(e)}")

        # 等待 15 分钟
        print("[INFO] Sleeping for 15 minutes before the next refresh...")
        time.sleep(FILETOOOLD_SEC)

# 获取本地 IP 地址
def get_my_ips():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        yield s.getsockname()[0]
    finally:
        s.close()

# 启动 HTTP 服务
httpd = HTTPServer((SERV_IPADDR, SERV_PORT), WeatherLandscapeServer)

# 启动后台线程定时刷新图片
refresh_thread = threading.Thread(target=periodic_refresh, daemon=True)
refresh_thread.start()

# 打印服务地址
for ip in get_my_ips():
    print(r"Serving at http://%s:%i/" % (ip, SERV_PORT))

httpd.serve_forever()
