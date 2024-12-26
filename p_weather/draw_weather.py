
from p_weather.sprites import Sprites
from p_weather.openweathermap import OpenWeatherMap,WeatherInfo
from p_weather.sunrise import sun

import datetime 
from PIL import Image
import random


class DrawWeather():
    XSTART = 32
    XSTEP = 44
    XFLAT = 10
    YSTEP = 50  # 64
    
    DEFAULT_DEGREE_PER_PIXEL = 0.5

    @staticmethod
    def mybeizelfnc(t, d0, d1, d2, d3):
        return (1 - t) * ((1 - t) * ((1 - t) * d0 + t * d1) + t * ((1 - t) * d1 + t * d2)) + t * ((1 - t) * ((1 - t) * d1 + t * d2) + t * ((1 - t) * d2 + t * d3))

    def mybezier(self, x, xa, ya, xb, yb):
        xc = (xb + xa) / 2.0
        d = xb - xa
        t = float(x - xa) / float(d)
        y = DrawWeather.mybeizelfnc(t, ya, ya, yb, yb)
        return int(y)

    def __init__(self, canvas, sprites):
        self.img = canvas
        self.sprite = sprites
        (self.IMGEWIDTH, self.IMGHEIGHT) = self.img.size

    def TimeDiffToPixels(self, dt):
        ds = dt.total_seconds()
        secondsperpixel = (WeatherInfo.FORECAST_PERIOD_HOURS * 60 * 60) / DrawWeather.XSTEP
        return int(ds / secondsperpixel)

    def DegToPix(self, t):
        n = (t - self.tmin) / self.degreeperpixel
        y = self.ypos + self.YSTEP - int(n)
        return y

    def is_bike_friendly(self, owm):
        """判断未来五小时的天气是否适合骑单车"""
        bike_friendly = True
        for i in range(5):  # 未来五小时
            f = owm.Get(datetime.datetime.now() + datetime.timedelta(hours=i))
            # print(f.temp, f.rain, f.snow, f.windspeed)
            if f is None:
                continue
            if f.temp < 15 or f.temp > 35:
                bike_friendly = False
                break
            if f.rain > 0: 
                bike_friendly = False
                break
            if f.snow > 0: 
                bike_friendly = False
                break
            if f.windspeed > 15:
                bike_friendly = False
                break
        print(f"Is bike friendly: {bike_friendly}")
        return bike_friendly

    def Draw(self, ypos, owm):
        print("DrawWeather.Draw:", self, ypos, owm)
        self.picheight = self.IMGHEIGHT
        self.picwidth = self.IMGEWIDTH
        self.ypos = ypos

        nforecasrt = (self.picwidth - self.XSTART) / self.XSTEP
        maxtime = datetime.datetime.now() + datetime.timedelta(hours=WeatherInfo.FORECAST_PERIOD_HOURS * nforecasrt)

        (self.tmin, self.tmax) = owm.GetTempRange(maxtime)
        self.temprange = self.tmax - self.tmin
        if self.temprange < self.YSTEP:
            self.degreeperpixel = self.DEFAULT_DEGREE_PER_PIXEL
        else:
            self.degreeperpixel = self.temprange / float(self.YSTEP)

        xpos = 0
        tline = [0] * (self.picwidth + self.XSTEP + 1)
        f = owm.GetCurr()
        oldtemp = f.temp
        oldy = self.DegToPix(oldtemp)
        for i in range(self.XSTART):
            tline[i] = oldy
        yclouds = int(ypos - self.YSTEP / 2)
        f.Print()

        # 绘制 house
        self.sprite.Draw("house", xpos, 0, oldy)
        
        # 绘制 bike
        if self.is_bike_friendly(owm):
            self.sprite.Draw("bike", xpos, 5, oldy - 22) 

        # 其他绘制内容
        self.sprite.DrawInt(oldtemp, xpos + 8, oldy + 10)
        self.sprite.DrawCloud(f.clouds, xpos, yclouds, self.XSTART, self.YSTEP / 2)
        self.sprite.DrawRain(f.rain, xpos, yclouds, self.XSTART, tline)
        self.sprite.DrawSnow(f.snow, xpos, yclouds, self.XSTART, tline)

        t = datetime.datetime.now()
        dt = datetime.timedelta(hours=WeatherInfo.FORECAST_PERIOD_HOURS)
        tf = t

        xpos = int(self.XSTART)
        nforecasrt = int(nforecasrt)

        n = int((self.XSTEP - self.XFLAT) / 2)
        for i in range(nforecasrt + 1):
            f = owm.Get(tf)
            if f is None:
                continue
            f.Print()
            newtemp = f.temp
            newy = self.DegToPix(newtemp)
            for i in range(n):
                tline[xpos + i] = self.mybezier(xpos + i, xpos, oldy, xpos + n, newy)

            for i in range(self.XFLAT):
                tline[int(xpos + i + n)] = newy

            xpos += n + self.XFLAT
            n = (self.XSTEP - self.XFLAT)
            oldtemp = newtemp
            oldy = newy
            tf += dt

        s = sun(owm.LAT, owm.LON)
        tf = t
        xpos = self.XSTART
        objcounter = 0
        for i in range(nforecasrt + 1):
            f = owm.Get(tf)
            if f is None:
                continue

            t_sunrise = s.sunrise(tf)
            t_sunset = s.sunset(tf)

            ymoon = ypos - self.YSTEP * 5 / 8

            if tf <= t_sunrise and tf + dt > t_sunrise:
                dx = self.TimeDiffToPixels(t_sunrise - tf) - self.XSTEP / 2
                self.sprite.Draw("sun", 0, xpos + dx, ymoon)
                objcounter += 1
                if objcounter == 2:
                    break

            if tf <= t_sunset and tf + dt > t_sunset:
                dx = self.TimeDiffToPixels(t_sunset - tf) - self.XSTEP / 2
                self.sprite.Draw("moon", 0, xpos + dx, ymoon)
                objcounter += 1
                if objcounter == 2:
                    break

            xpos += self.XSTEP
            tf += dt

        istminprinted = False
        istmaxprinted = False
        tf = t
        xpos = self.XSTART
        n = int((self.XSTEP - self.XFLAT) / 2)
        for i in range(nforecasrt + 1):
            f = owm.Get(tf)
            if f is None:
                continue

            yclouds = int(ypos - self.YSTEP / 2)

            if f.temp == self.tmin and not istminprinted:
                self.sprite.DrawInt(f.temp, xpos + n, tline[xpos + n] + 10)
                istminprinted = True

            if f.temp == self.tmax and not istmaxprinted:
                self.sprite.DrawInt(f.temp, xpos + n, tline[xpos + n] + 10)
                istmaxprinted = True

            t0 = f.t - dt / 2
            t1 = f.t + dt / 2

            dt_onehour = datetime.timedelta(hours=1)
            dx_onehour = self.XSTEP / WeatherInfo.FORECAST_PERIOD_HOURS
            tt = t0
            xx = xpos
            while tt <= t1:
                ix = int(xx)
                if tt.hour == 12:
                    self.sprite.Draw("flower", 1, ix, tline[ix])
                if tt.hour == 0:
                    self.sprite.Draw("flower", 0, ix, tline[ix])
                if tt.hour in [6, 18, 3, 15, 9, 21]:
                    self.sprite.DrawWind(f.windspeed, f.winddeg, ix, tline)

                tt += dt_onehour
                xx += dx_onehour

            self.sprite.DrawCloud(f.clouds, xpos, yclouds, self.XSTEP, self.YSTEP / 2)
            self.sprite.DrawRain(f.rain, xpos, yclouds, self.XSTEP, tline)
            self.sprite.DrawSnow(f.snow, xpos, yclouds, self.XSTEP, tline)

            xpos += self.XSTEP
            tf += dt

        BLACK = 0
        for x in range(self.picwidth):
            if tline[x] < self.picheight:
                self.sprite.Dot(x, tline[x], Sprites.BLACK)
            else:
                print(f"out of range: {x} - {tline[x]}(max {self.picheight})")




