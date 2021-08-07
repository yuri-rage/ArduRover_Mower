"""
    VERY rudimentary PID simulation using matplotlib and simple-pid

    Lots of hard-coded values and global variables - not my finest work, but maybe my fastest

    Dependencies:
        matplotlib
        simple-pid

    -- Yuri - Aug 2021
"""

import time
import random
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button
from simple_pid import PID

MAX_PLOT_POINTS = 32


def animate(i):
    global achieved, desired, last_plot_time, next_set_time  # yep, I did that...
    achieved = pid(achieved)
    time_now = round(time.time() * 1000) - start_time
    if time_now >= next_set_time:
        desired = random.uniform(-100.0, 100.0)
        pid.setpoint = desired
        next_set_time = time_now + random.randint(1000, 3000)
    if time_now - last_plot_time > 300:
        list_time.append(round(time_now / 1000, 3))
        list_desired.append(desired)
        list_achieved.append(achieved)

        if len(list_time) > MAX_PLOT_POINTS:
            list_time.pop(0)
            list_desired.pop(0)
            list_achieved.pop(0)

        ax.cla()

        ax.plot(list_time, list_desired, label='PID Desired')
        ax.plot(list_time, list_achieved, label='PID Achieved')
        ax.set_ylim([-125, 125])
        ax.legend(loc='upper left')
        ax.margins(x=0.001)
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.3)
        last_plot_time = time_now


def update(val):
    # factor of 2 on the Ki term because it *seems* scaled incorrectly in the library
    # divide Kd by 100 for the same reason
    pid.tunings = (p_slider.val, i_slider.val * 2.0, d_slider.val / 100.0)


def reset_controller(event):
    pid.reset()
    pid.setpoint = desired
    p_slider.reset()
    i_slider.reset()
    d_slider.reset()


start_time = round(time.time() * 1000)
last_plot_time = 0
next_set_time = random.randint(1000, 3000)

desired = random.uniform(-100.0, 100.0)
achieved = 0.0

pid = PID(0.7, 0.7, 0.0, setpoint=desired, sample_time=None)

list_time = []
list_desired = []
list_achieved = []

for t in range(MAX_PLOT_POINTS):
    list_time.append((t / 4 - 8))
    list_desired.append(desired)
    list_achieved.append(achieved)

fig, ax = plt.subplots()
plt.style.use('fivethirtyeight')
fig.set_figheight(5)
fig.set_figwidth(16)

ax_p = plt.axes([0.1, 0.2, 0.7, 0.03])
ax_i = plt.axes([0.1, 0.12, 0.7, 0.03])
ax_d = plt.axes([0.1, 0.04, 0.7, 0.03])
ax_btn = plt.axes([0.88, 0.2, 0.1, 0.04])
button = Button(ax_btn, 'Reset')

p_slider = Slider(ax_p, 'P', 0.6, 1.0, valinit=pid.Kp, valstep=.0001)
i_slider = Slider(ax_i, 'I', 0.3, 1.0, valinit=pid.Ki / 2.0, valstep=0.0001)
d_slider = Slider(ax_d, 'D', 0, 0.5, valinit=pid.Kd * 100.0, valstep=0.00001)

p_slider.on_changed(update)
i_slider.on_changed(update)
d_slider.on_changed(update)
button.on_clicked(reset_controller)

# force the update function to run very quickly to get plenty of PID feedback
# next_plot_time slows the actual animation down
ani = FuncAnimation(plt.gcf(), animate, interval=0.001)

plt.show()
