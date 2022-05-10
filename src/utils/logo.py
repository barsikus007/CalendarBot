import PIL.ImageDraw as ImageDraw
import PIL.Image as Image
from math import cos, sin, tan, radians
from random import randint

log = 0
log2 = 0
log3 = 0


def count_cords(middle, middle_angle, time, middle_angle_first, big_r):
    x, y = middle
    angle = middle_angle_first + middle_angle * time
    x = x + big_r * round(cos(radians(angle)), 5)
    y = y - big_r * round(sin(radians(angle)), 5)
    return int(x), int(y)


def count_points(cords, a, n):
    r = a/(2*tan(radians(180/n)))
    big_r = a/(2*sin(radians(180/n)))
    middle = (cords[0]-(a//2), cords[1]-r)
    middle_angle = (360/n)
    middle_angle_first = 360-(90-(360/(n*2)))
    points = [cords]
    if log:
        print(n)
    points.extend(
        count_cords(middle, middle_angle, time, middle_angle_first, big_r)
        for time in range(n)
    )
    return points


def draw_line(draw, color, center, a, n):
    draw.polygon(count_points(cords=center, a=a, n=n), fill=color)


def make_image(
        n=20,
        color=None,
        show_image=True,
        save_image=None,
        make_gif=None,
        frames=0,
        multiplier=1,
        side=100,
        duration=100,
        resolution=(1920, 1080),
        background=256 ** 3 - 1
):
    side = side * multiplier
    screen_x, screen_y = resolution[0] * multiplier, resolution[1] * multiplier
    center = (screen_x // 2 + side // 2, screen_y * 995 // 1000)
    if show_image or save_image:
        image = Image.new("RGB", (screen_x, screen_y), color=background)
        draw = ImageDraw.Draw(image)
        gay_counter = 0
        for i in range(n, 2, -1):
            if log2:
                print(i)
            if not color:
                step = 255//n
                color_1 = (255-(n-i)*step, 255-(n-i)*step, 255-(n-i)*step)
                draw_line(draw, color_1, center, side, i)
            elif color == "gay":
                # rainbow = [(255, 0, 0), (255, 128, 0), (255, 255, 0), (0, 255, 0), (0, 255, 255), (0, 0, 255), (255, 0, 255)]
                rainbow = [(255, 0, 0), (255, 128, 0), (255, 255, 0), (0, 255, 0), (0, 0, 255), (255, 0, 255)]
                draw_line(draw, rainbow[gay_counter % len(rainbow)], center, side, i)
                gay_counter += 1
            elif color == "random":
                color_1 = randint(0, 256**3-1)
                draw_line(draw, color_1, center, side, i)
            elif color == "invert":
                step = 255//n
                color_1 = (255-i*step, 255-i*step, 255-i*step)
                draw_line(draw, color_1, center, side, i)
            elif len(color) == 3:
                color_x, color_y, color_z = color
                step_x, step_y, step_z = color_x//n, color_y//n, color_z//n
                color_1 = (abs(color_x - i * step_x), abs(color_y - i * step_y), abs(color_z - i * step_z))
                # color_1 = (color_x-(n-i)*step, color_y-(n-i)*step, color_z-(n-i)*step)
                # color_1 = (color_x-(n-i)*step, color_y-(n-i)*step, color_z-(n-i)*step)
                print(color_1)
                print(i)
                print((n-i)*step_x)
                draw_line(draw, color_1, center, side, i)
            else:
                step = 255//n
                color_1 = (255-(n-i)*step, 255-(n-i)*step, 255-(n-i)*step)
                draw_line(draw, color_1, center, side, i)
    if show_image:
        image.show()
    if save_image:
        image.save(save_image)
    if make_gif:
        make_image(n=n, show_image=False, save_image=make_gif, color=color, multiplier=multiplier, side=side)
        frame_list = [Image.new("RGB", (screen_x, screen_y), color=256 ** 3 - 1) for _ in range(frames)]
        step_2 = 255//frames
        for gay_counter_2, j in enumerate(frame_list, start=1):
            k = frame_list.index(j)
            draw = ImageDraw.Draw(j)
            gay_counter = 0 + gay_counter_2
            if log3:
                print(j)
                print(step_2*k)
            for i in range(n, 2, -1):
                if log2:
                    print(i)
                if not color:
                    step = 255//n
                    color_1 = (255-(n-i)*step, 255-(n-i)*step, 255-(n-i)*step)
                    draw_line(draw, color_1, center, side, i)
                elif color == "gay":
                    # rainbow = [(255, 0, 0), (255, 128, 0), (255, 255, 0), (0, 255, 0), (0, 255, 255), (0, 0, 255), (255, 0, 255)]
                    rainbow = [(255, 0, 0), (255, 128, 0), (255, 255, 0), (0, 255, 0), (0, 0, 255), (255, 0, 255)]
                    draw_line(draw, rainbow[gay_counter % len(rainbow)], center, side, i)
                    gay_counter += 1
                elif color == "random":
                    color_1 = randint(0, 256**3-1)
                    draw_line(draw, color_1, center, side, i)
                elif color == "invert":
                    step = 255//n
                    color_1 = (255-i*step, 255-i*step, 255-i*step)
                    draw_line(draw, color_1, center, side, i)
                elif len(color) == 3:
                    step = 255//n
                    color_x, color_y, color_z = color
                    color_1 = (color_x-(n-i)*step, color_y-(n-i)*step, color_z-(n-i)*step)
                    draw_line(draw, color_1, center, side, i)
                else:
                    step = 255//n
                    color_1 = (255-(n-i)*step, 255-(n-i)*step, 255-(n-i)*step)
                    draw_line(draw, color_1, center, side, i)
        frame_list.reverse()
        with Image.open(make_gif) as gif:
            gif.save(make_gif, save_all=True, append_images=frame_list[1:], format="gif", duration=duration, loop=0)


if __name__ == '__main__':
    # make_image(n=20, color="random", show_image=False, save_image=None, make_gif="yoy.gif", frames=10)
    # make_image(n=20, color="gay", show_image=False, save_image=None, make_gif="yoy.gif", frames=6, duration=16, side=170)
    # make_image(n=9, color="gay", side=300)
    # make_image(n=20, side=500, resolution=[1080, 2160], color=(255, 127, 0), background=0, save_image="valya.png")
    make_image(n=100, side=100*8*3, resolution=(1920*8*3, 1080*8*3), save_image="48KK.png")
    # gay random invert
    # make_image()
