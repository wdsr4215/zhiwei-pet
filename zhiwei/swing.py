"""沿屏幕纵深摆动的秋千投影，水平中心固定。"""
import math


def swing_projection(elapsed, length=145.0, focal=560.0):
    envelope=min(1.0,max(0.0,elapsed)/1.8)
    angle=math.sin(elapsed*math.tau/4.2)*.34*envelope
    depth=length*math.sin(angle)
    rise=length*(1-math.cos(angle))
    return focal/(focal-depth),rise
