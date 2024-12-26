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
                        background-color: #ffffff;
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
                <script>
                    let wakeLock = null;
    
                    async function requestWakeLock() {{
                        if ('wakeLock' in navigator) {{
                            try {{
                                wakeLock = await navigator.wakeLock.request('screen');
                                console.log("Wake lock acquired");
    
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
                        if (wakeLock !== null) {{
                            wakeLock.release().then(() => {{
                                console.log("Wake lock manually released");
                                wakeLock = null;
                            }});
                        }}
                    }}
    
                    function keepScreenActiveFallback() {{
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
                        setTimeout(updateImage, 60000);
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
        """.format(user_file=USERFILENAME, timestamp=str(time.time()))

def periodic_refresh():
    """
    定期刷新天气图像
    """
    while True:
        try:
            print("Checking if weather images need to be updated...")
            user_file_name = WEATHER.TmpFilePath(USERFILENAME)
            eink_file_name = WEATHER.TmpFilePath(EINKFILENAME)

            # 检查文件是否过期
            if not os.path.isfile(user_file_name) or not os.path.isfile(eink_file_name) or \
                    (time.time() - os.path.getmtime(user_file_name)) > FILETOOOLD_SEC:
                print("Refreshing weather images...")
                img = WEATHER.MakeImage()
                img.save(user_file_name)

                img = img.rotate(-90, expand=True)
                img = img.transpose(Image.FLIP_TOP_BOTTOM)

                img.save(eink_file_name)
                print("Weather images updated.")
            else:
                print("Weather images are up to date.")
        except Exception as e:
            print("Error refreshing weather images:", str(e))

        # 等待 15 分钟
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
