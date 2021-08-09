# -*- coding: utf-8 -*-
"""
    servo_tuner.py

    Creates an IronPython dialog to augment servo tuning

    Tested under Windows 10, but should be Linux compatible
    (assuming that IronPython sucks less at cross-compatibility than it does ease of coding...)

    -- Yuri - Aug 2021

"""

print('\n*** ServoTuner ***\n')
print('Loading modules...')

from collections import OrderedDict
import clr

clr.AddReference('MAVLink')
clr.AddReference('System.Drawing')
clr.AddReference('System.Windows.Forms')

import MAVLink
from System import Char, Func, Array
from System.Windows.Forms import Application, Screen, Form, Keys, HorizontalAlignment, \
    FlatStyle, BorderStyle, ProgressBar, CheckBox, Label, NumericUpDown, Button, ToolTip
from System.Drawing import Point, Color

SEVERITY = ['EMERGENCY: ', 'ALERT: ', 'CRITICAL: ', 'ERROR: ', 'WARNING: ', 'NOTICE: ', 'INFO: ', 'DEBUG: ']
SPINNER = ['-', '\\', '|', '/']

MIN_PWM = 800
MAX_PWM = 2200

AIL_CH = int(Script.GetParam('RCMAP_ROLL'))
ELE_CH = int(Script.GetParam('RCMAP_PITCH'))
THR_CH = int(Script.GetParam('RCMAP_THROTTLE'))
RUD_CH = int(Script.GetParam('RCMAP_YAW'))

class MPColor:
    """ System.Drawing.Color is a sealed value type that disallows class inheritance
        Dynamically creating MPColor attributes is a workaround for that """

    def __init__(self):
        pass


for attr in dir(Color):
    setattr(MPColor, attr, getattr(Color, attr))

setattr(MPColor, 'MPDarkGray', Color.FromArgb(38, 39, 40))
setattr(MPColor, 'MPMediumGray', Color.FromArgb(53, 54, 55))
setattr(MPColor, 'MPLightGray', Color.FromArgb(68, 69, 70))
setattr(MPColor, 'MPGreen', Color.FromArgb(165, 203, 70))
setattr(MPColor, 'ServoBG', Color.FromArgb(200, 201, 202))

CustomColor = MPColor()


class ServoTunerForm(Form):
    def __init__(self):

        MAV.SubscribeToPacketType(MAVLink.MAVLINK_MSG_ID.SERVO_OUTPUT_RAW,
                                  Func[MAVLink.MAVLinkMessage, bool](self.get_servo_data))
        MAV.SubscribeToPacketType(MAVLink.MAVLINK_MSG_ID.HEARTBEAT,
                                  Func[MAVLink.MAVLinkMessage, bool](self.heartbeat_received))
        MAV.OnPacketReceived += self.packet_handler

        self.Text = 'Servo Tuner'
        self.Location = Point(0, 0)
        self.TopMost = True
        self.BackColor = CustomColor.MPDarkGray
        self.ForeColor = CustomColor.White
        self.Shown += self.on_load
        self.FormClosing += self.on_exit
        self.heartbeat_count = 0

        self.margin = 5
        start_x, start_y = 12, 10

        self.servo_widgets = []
        for x in range(16):
            progress_bar = ProgressBar()
            progress_bar.Width = 150
            progress_bar.Height = 20
            progress_bar.BackColor = CustomColor.MPMediumGray
            progress_bar.ForeColor = CustomColor.MPGreen
            progress_bar.Minimum = MIN_PWM
            progress_bar.Maximum = MAX_PWM
            progress_bar.Value = int((MIN_PWM + MAX_PWM) / 2)
            progress_bar.Text = str(x)

            lbl_servo = Label()
            lbl_servo.Text = 'Servo  ' + str(x + 1)
            lbl_servo.BackColor = CustomColor.MPDarkGray
            lbl_servo.Width = 60
            lbl_servo.Height = progress_bar.Height - 8

            lbl_value = Label()
            lbl_value.Text = str(progress_bar.Value)
            lbl_value.BackColor = CustomColor.ServoBG
            lbl_value.ForeColor = Color.Black
            lbl_value.Width = 30
            lbl_value.Height = progress_bar.Height - 8

            lbl_min = Label()
            lbl_min.Text = str(MAX_PWM + 1)
            lbl_min.BackColor = CustomColor.MPMediumGray
            lbl_min.Width = 30
            lbl_min.Height = progress_bar.Height - 8

            lbl_max = Label()
            lbl_max.Text = str(MIN_PWM - 1)
            lbl_max.BackColor = CustomColor.MPMediumGray
            lbl_max.Width = 30
            lbl_max.Height = progress_bar.Height - 8
            
            lbl_diff = Label()
            lbl_diff.Text = ''
            lbl_diff.BackColor = CustomColor.MPMediumGray
            lbl_diff.Width = 30
            lbl_diff.Height = progress_bar.Height - 8
            
            lbl_midpt = Label()
            lbl_midpt.Text = ''
            lbl_midpt.BackColor = CustomColor.MPMediumGray
            lbl_midpt.Width = 30
            lbl_midpt.Height = progress_bar.Height - 8

            self.servo_widgets.append(OrderedDict([('lbl_servo', lbl_servo),
                                                   ('progress_bar', progress_bar),
                                                   ('lbl_value', lbl_value),
                                                   ('lbl_min', lbl_min),
                                                   ('lbl_max', lbl_max),
                                                   ('lbl_diff', lbl_diff),
                                                   ('lbl_midpt', lbl_midpt)]))

        self.lbl_min_hdr = Label()
        self.lbl_min_hdr.Text = ' Min:'
        self.lbl_min_hdr.AutoSize = True

        self.lbl_max_hdr = Label()
        self.lbl_max_hdr.Text = ' Max:'
        self.lbl_max_hdr.AutoSize = True
        
        self.lbl_diff_hdr = Label()
        self.lbl_diff_hdr.Text = 'Diff:'
        self.lbl_diff_hdr.AutoSize = True
        
        self.lbl_midpt_hdr = Label()
        self.lbl_midpt_hdr.Text = 'MidPt:'
        self.lbl_midpt_hdr.AutoSize = True

        self.spn_aileron = NumericUpDown()
        self.spn_aileron.Width = 50
        self.spn_aileron.BorderStyle = BorderStyle.FixedSingle
        self.spn_aileron.BackColor = CustomColor.MPLightGray
        self.spn_aileron.ForeColor = CustomColor.White
        self.spn_aileron.Minimum = int(Script.GetParam('RC' + str(AIL_CH) + '_MIN'))
        self.spn_aileron.Maximum = int(Script.GetParam('RC' + str(AIL_CH) + '_MAX'))
        self.spn_aileron.Increment = 1
        self.spn_aileron.Value = int(Script.GetParam('RC' + str(AIL_CH) + '_TRIM'))

        self.chk_aileron = CheckBox()
        self.chk_aileron.Name = str(AIL_CH) + ',spn_aileron'
        self.chk_aileron.FlatAppearance.BorderSize = 1
        self.chk_aileron.FlatAppearance.BorderColor = CustomColor.MPLightGray
        self.chk_aileron.Text = 'Override RC Aileron'
        self.chk_aileron.Checked = False
        self.chk_aileron.AutoSize = True
        self.chk_aileron.CheckedChanged += self.handle_overrides

        self.spn_elevator = NumericUpDown()
        self.spn_elevator.Width = 50
        self.spn_elevator.BorderStyle = BorderStyle.FixedSingle
        self.spn_elevator.BackColor = CustomColor.MPLightGray
        self.spn_elevator.ForeColor = CustomColor.White
        self.spn_elevator.Minimum = int(Script.GetParam('RC' + str(ELE_CH) + '_MIN'))
        self.spn_elevator.Maximum = int(Script.GetParam('RC' + str(ELE_CH) + '_MAX'))
        self.spn_elevator.Increment = 1
        self.spn_elevator.Value = int(Script.GetParam('RC' + str(ELE_CH) + '_TRIM'))

        self.chk_elevator = CheckBox()
        self.chk_elevator.Name = str(ELE_CH) + ',spn_elevator'
        self.chk_elevator.FlatAppearance.BorderSize = 1
        self.chk_elevator.FlatAppearance.BorderColor = CustomColor.MPLightGray
        self.chk_elevator.Text = 'Override RC Elevator'
        self.chk_elevator.Checked = False
        self.chk_elevator.AutoSize = True
        self.chk_elevator.CheckedChanged += self.handle_overrides
        
        self.spn_throttle = NumericUpDown()
        self.spn_throttle.Width = 50
        self.spn_throttle.BorderStyle = BorderStyle.FixedSingle
        self.spn_throttle.BackColor = CustomColor.MPLightGray
        self.spn_throttle.ForeColor = CustomColor.White
        self.spn_throttle.Minimum = int(Script.GetParam('RC' + str(THR_CH) + '_MIN'))
        self.spn_throttle.Maximum = int(Script.GetParam('RC' + str(THR_CH) + '_MAX'))
        self.spn_throttle.Increment = 1
        self.spn_throttle.Value = int(Script.GetParam('RC' + str(THR_CH) + '_TRIM'))

        self.chk_throttle = CheckBox()
        self.chk_throttle.Name = str(THR_CH) + ',spn_throttle'
        self.chk_throttle.FlatAppearance.BorderSize = 1
        self.chk_throttle.FlatAppearance.BorderColor = CustomColor.MPLightGray
        self.chk_throttle.Text = 'Override RC Throttle'
        self.chk_throttle.Checked = False
        self.chk_throttle.AutoSize = True
        self.chk_throttle.CheckedChanged += self.handle_overrides
        
        self.spn_rudder = NumericUpDown()
        self.spn_rudder.Width = 50
        self.spn_rudder.BorderStyle = BorderStyle.FixedSingle
        self.spn_rudder.BackColor = CustomColor.MPLightGray
        self.spn_rudder.ForeColor = CustomColor.White
        self.spn_rudder.Minimum = int(Script.GetParam('RC' + str(RUD_CH) + '_MIN'))
        self.spn_rudder.Maximum = int(Script.GetParam('RC' + str(RUD_CH) + '_MAX'))
        self.spn_rudder.Increment = 1
        self.spn_rudder.Value = int(Script.GetParam('RC' + str(RUD_CH) + '_TRIM'))

        self.chk_rudder = CheckBox()
        self.chk_rudder.Name = str(RUD_CH) + ',spn_rudder'
        self.chk_rudder.FlatAppearance.BorderSize = 1
        self.chk_rudder.FlatAppearance.BorderColor = CustomColor.MPLightGray
        self.chk_rudder.Text = 'Override RC Rudder'
        self.chk_rudder.Checked = False
        self.chk_rudder.AutoSize = True
        self.chk_rudder.CheckedChanged += self.handle_overrides

        self.spn_channel_num = NumericUpDown()
        self.spn_channel_num.Width = 35
        self.spn_channel_num.BorderStyle = BorderStyle.FixedSingle
        self.spn_channel_num.BackColor = CustomColor.MPLightGray
        self.spn_channel_num.ForeColor = CustomColor.White
        self.spn_channel_num.Minimum = 1
        self.spn_channel_num.Maximum = 16
        self.spn_channel_num.Increment = 1
        self.spn_channel_num.Value = 1
        self.spn_channel_num.ValueChanged += self.set_channel_min_max

        self.spn_channel = NumericUpDown()
        self.spn_channel.Width = 50
        self.spn_channel.BorderStyle = BorderStyle.FixedSingle
        self.spn_channel.BackColor = CustomColor.MPLightGray
        self.spn_channel.ForeColor = CustomColor.White
        self.spn_channel.Minimum = int(Script.GetParam('RC' + str(self.spn_channel_num.Value) + '_MIN'))
        self.spn_channel.Maximum = int(Script.GetParam('RC' + str(self.spn_channel_num.Value) + '_MAX'))
        self.spn_channel.Increment = 1
        self.spn_channel.Value = int(Script.GetParam('RC' + str(self.spn_channel_num.Value) + '_TRIM'))

        self.chk_channel = CheckBox()
        self.chk_channel.Name = str(self.spn_channel_num.Value) + ',spn_channel'
        self.chk_channel.FlatAppearance.BorderSize = 1
        self.chk_channel.FlatAppearance.BorderColor = CustomColor.MPLightGray
        self.chk_channel.Text = 'Override RC Channel'
        self.chk_channel.Checked = False
        self.chk_channel.AutoSize = True
        self.chk_channel.CheckedChanged += self.handle_overrides

        self.btn_reset = Button()
        self.btn_reset.Width = 130
        self.btn_reset.FlatStyle = FlatStyle.Flat
        self.btn_reset.FlatAppearance.BorderSize = 1
        self.btn_reset.FlatAppearance.BorderColor = CustomColor.MPLightGray
        self.btn_reset.BackColor = CustomColor.MPGreen
        self.btn_reset.ForeColor = CustomColor.Black
        self.btn_reset.Text = 'Reset Min/Max Values'
        self.btn_reset.Click += self.reset_min_max

        self.btn_inhibit_overrides = Button()
        self.btn_inhibit_overrides.Width = self.btn_reset.Width
        self.btn_inhibit_overrides.Height = self.btn_reset.Height + 15
        self.btn_inhibit_overrides.FlatStyle = FlatStyle.Flat
        self.btn_inhibit_overrides.FlatAppearance.BorderSize = 1
        self.btn_inhibit_overrides.FlatAppearance.BorderColor = CustomColor.MPLightGray
        self.btn_inhibit_overrides.BackColor = Color.DarkRed
        self.btn_inhibit_overrides.ForeColor = Color.White
        self.btn_inhibit_overrides.Text = 'Return RC Control\nNOW!'
        self.btn_inhibit_overrides.Click += self.handle_overrides

        self.chk_sticky = CheckBox()
        self.chk_sticky.FlatAppearance.BorderSize = 1
        self.chk_sticky.FlatAppearance.BorderColor = CustomColor.MPLightGray
        self.chk_sticky.Text = 'Always on top'
        self.chk_sticky.Checked = True
        self.chk_sticky.AutoSize = True

        self.lbl_status = Label()
        self.lbl_status.Text = 'Waiting for heartbeat...'
        self.lbl_status.BackColor = CustomColor.MPMediumGray
        self.lbl_status.Height = self.servo_widgets[0]['progress_bar'].Height - 4

        self.lbl_warning = Label()
        self.lbl_warning.Text = '  WARNING!  This script is capable of servo/motor output.  Make sure the\n' \
                                '  vehicle is safely on jack stands or cannot otherwise cause damage or injury.'
        self.lbl_warning.BackColor = Color.DarkRed
        self.lbl_warning.Height = 30

        # pseudo-responsive form layout

        self.add_control_horizontal(self.lbl_warning, start_x, start_y, self.margin)

        x, y = start_x, start_y + 55
        max_x = 0
        for widget in self.servo_widgets:
            x = start_x
            x, y, x_extent = self.add_control_horizontal(widget['lbl_servo'], x, y, self.margin)
            x, tmp, x_extent = self.add_control_horizontal(widget['progress_bar'], x, y - 4, self.margin)
            widget.items()[2][1].Left = x - 95
            widget.items()[2][1].Top = y
            self.Controls.Add(widget['lbl_value'])
            widget['lbl_value'].BringToFront()
            x, y, x_extent = self.add_control_horizontal(widget['lbl_min'], x + 10, y, self.margin)
            x, y, x_extent = self.add_control_horizontal(widget['lbl_max'], x + 10, y, self.margin)
            x, y, x_extent = self.add_control_horizontal(widget['lbl_diff'], x + 10, y, self.margin)
            x, y, x_extent = self.add_control_horizontal(widget['lbl_midpt'], x + 10, y, self.margin)
            max_x = max([x_extent, max_x])
            y += widget.items()[1][1].Height + self.margin * 3
        self.Width = max_x + self.margin * 4

        x = self.servo_widgets[0]['lbl_min'].Left

        x, y, tmp = self.add_control_vertical(self.btn_reset, x, y + self.margin, self.margin)
        x, y, tmp = self.add_control_horizontal(self.btn_inhibit_overrides, x, y + self.margin, self.margin)

        x, y, tmp = self.add_control_horizontal(self.spn_aileron, start_x, self.btn_reset.Top, self.margin)
        x, y, tmp = self.add_control_vertical(self.chk_aileron, x, y, self.margin)
        x, y, tmp = self.add_control_horizontal(self.spn_elevator, start_x, y + 3, self.margin)
        x, y, tmp = self.add_control_vertical(self.chk_elevator, x, y, self.margin)
        x, y, tmp = self.add_control_horizontal(self.spn_throttle, start_x, y + 3, self.margin)
        x, y, tmp = self.add_control_vertical(self.chk_throttle, x, y, self.margin)
        x, y, tmp = self.add_control_horizontal(self.spn_rudder, start_x, y + 3, self.margin)
        x, y, tmp = self.add_control_vertical(self.chk_rudder, x, y, self.margin)
        x, y, tmp = self.add_control_horizontal(self.spn_channel, start_x, y + 3, self.margin)
        x, y, tmp = self.add_control_horizontal(self.chk_channel, x, y, self.margin)
        x, y, tmp = self.add_control_vertical(self.spn_channel_num, x, y, self.margin)

        x, y, tmp = self.add_control_vertical(self.chk_sticky, start_x, y + 10, self.margin)

        self.lbl_status.Width = self.Width - self.margin * 7
        x, y, x_extent = self.add_control_vertical(self.lbl_status, start_x, y + 3, self.margin)
        self.lbl_warning.Width = self.lbl_status.Width

        self.lbl_min_hdr.Location = Point(self.servo_widgets[0]['lbl_min'].Left,
                                          self.servo_widgets[0]['lbl_min'].Top - 20)
        self.lbl_max_hdr.Location = Point(self.servo_widgets[0]['lbl_max'].Left,
                                          self.servo_widgets[0]['lbl_min'].Top - 20)
        self.lbl_diff_hdr.Location = Point(self.servo_widgets[0]['lbl_diff'].Left,
                                           self.servo_widgets[0]['lbl_min'].Top - 20)
        self.lbl_midpt_hdr.Location = Point(self.servo_widgets[0]['lbl_midpt'].Left,
                                            self.servo_widgets[0]['lbl_min'].Top - 20)
        self.Controls.Add(self.lbl_min_hdr)
        self.Controls.Add(self.lbl_max_hdr)
        self.Controls.Add(self.lbl_diff_hdr)
        self.Controls.Add(self.lbl_midpt_hdr)
        self.Height = y + self.lbl_status.Height + self.margin * 5

        self.Tips = ToolTip()
        self.Tips.SetToolTip(self.btn_inhibit_overrides, 'Inhibit all RC overrides immediately')
        warning = 'WARNING: The vehicle may move when this is enabled!'
        self.Tips.SetToolTip(self.chk_aileron, warning)
        self.Tips.SetToolTip(self.chk_elevator, warning)
        self.Tips.SetToolTip(self.chk_throttle, warning)
        self.Tips.SetToolTip(self.chk_rudder, warning)
        self.Tips.SetToolTip(self.chk_channel, warning)



    def set_sticky(self, sender, event):
        if sender.Checked:
            self.TopMost = True
            return
        self.TopMost = False

    def set_channel_min_max(self, sender, event):
        self.chk_channel.Name = str(sender.Value) + ',spn_channel'
        self.spn_channel.Minimum = int(Script.GetParam('RC' + str(sender.Value) + '_MIN'))
        self.spn_channel.Maximum = int(Script.GetParam('RC' + str(sender.Value) + '_MAX'))
        self.spn_channel.Value = int(Script.GetParam('RC' + str(sender.Value) + '_TRIM'))

    def reset_min_max(self, sender, event):
        for x in range(15):
            self.servo_widgets[x]['lbl_min'].Text = str(MAX_PWM + 1)
            self.servo_widgets[x]['lbl_max'].Text = str(MIN_PWM - 1)
            self.servo_widgets[x]['lbl_diff'].Text = ''
            self.servo_widgets[x]['lbl_midpt'].Text = ''

    def add_control_vertical(self, control, x, y, margin):
        control.Location = Point(x, y)
        self.Controls.Add(control)
        return x, y + control.Height + margin, x + control.Width + margin

    def add_control_horizontal(self, control, x, y, margin):
        control.Location = Point(x, y)
        self.Controls.Add(control)
        return x + control.Width + margin, y, x + control.Width + margin

    def get_servo_data(self, message):
        for x in range(16):
            try:
                val = int(getattr(message.data, 'servo' + str(x + 1) + '_raw'))
            except AttributeError:
                continue
            if val < MIN_PWM:
                if self.servo_widgets[x]['progress_bar'].Visible:
                    self.servo_widgets[x]['progress_bar'].Visible = False
                if self.servo_widgets[x]['lbl_min'].Visible:
                    self.servo_widgets[x]['lbl_min'].Visible = False
                if self.servo_widgets[x]['lbl_max'].Visible:
                    self.servo_widgets[x]['lbl_max'].Visible = False
                if self.servo_widgets[x]['lbl_diff'].Visible:
                    self.servo_widgets[x]['lbl_diff'].Visible = False
                if self.servo_widgets[x]['lbl_midpt'].Visible:
                    self.servo_widgets[x]['lbl_midpt'].Visible = False
                self.servo_widgets[x]['lbl_value'].Text = '   --'
                continue
            self.servo_widgets[x]['progress_bar'].Value = val
            self.servo_widgets[x]['lbl_value'].Text = str(val)
            if val < int(self.servo_widgets[x]['lbl_min'].Text):
                self.servo_widgets[x]['lbl_min'].Text = str(val)
                max = int(self.servo_widgets[x]['lbl_max'].Text)
                self.servo_widgets[x]['lbl_diff'].Text = str(max - val)
                self.servo_widgets[x]['lbl_midpt'].Text = str(int(round((max - val) / 2) + val))
            if val > int(self.servo_widgets[x]['lbl_max'].Text):
                self.servo_widgets[x]['lbl_max'].Text = str(val)
                min = int(self.servo_widgets[x]['lbl_min'].Text)
                self.servo_widgets[x]['lbl_diff'].Text = str(val - min)
                self.servo_widgets[x]['lbl_midpt'].Text = str(int(round((val - min) / 2) + min))

        return True

    def heartbeat_received(self, message):
        self.heartbeat_count = (self.heartbeat_count + 1) % 4
        text = self.lbl_status.Text
        if text.find('heartbeat') > 0:
            text = '   FOUND: Heartbeat'
        text = list(text)
        text[0] = SPINNER[self.heartbeat_count]
        self.lbl_status.Text = ''.join(text)
        self.handle_overrides(self.chk_aileron, None)
        self.handle_overrides(self.chk_elevator, None)
        self.handle_overrides(self.chk_throttle, None)
        self.handle_overrides(self.chk_rudder, None)
        self.handle_overrides(self.chk_channel, None)

    def handle_overrides(self, sender, event):
        if sender == self.btn_inhibit_overrides:
            if self.chk_aileron.Checked:
                self.chk_aileron.Checked = False
            if self.chk_elevator.Checked:
                self.chk_elevator.Checked = False
            if self.chk_throttle.Checked:
                self.chk_throttle.Checked = False
            if self.chk_rudder.Checked:
                self.chk_rudder.Checked = False
            if self.chk_channel.Checked:
                self.chk_channel.Checked = False
            return

        chan, name = sender.Name.split(',')
        chan = int(chan)

        if sender.Checked:
            val = int(getattr(self, name).Value)
            Script.SendRC(chan, val, True)
            if sender.BackColor != Color.DarkRed:
                sender.BackColor = Color.DarkRed
            return

        if event is not None:  # return RC control for this channel by sending a 0 pwm value
            """ https://diydrones.com/forum/topics/how-to-restore-control-back-to-rc-when-running-a-python-script-in """
            Script.SendRC(chan, 0, True)
            if sender.BackColor != self.BackColor:
                sender.BackColor = self.BackColor

    def packet_handler(self, obj, message):
        try:
            if message.msgid == MAVLink.MAVLINK_MSG_ID.STATUSTEXT.value__:
                self.lbl_status.Text = SPINNER[self.heartbeat_count] + ' ' + \
                                       SEVERITY[message.data.severity] + str(bytes(message.data.text))
        except Exception as inst:
            print(inst)  # not sure what situation would raise this, so leaving it for debugging

    def on_load(self, sender, event):
        self.chk_sticky.CheckedChanged += self.set_sticky
        self.set_sticky(self.chk_sticky, None)
        print('Running...')

    def on_exit(self, sender, event):
        MAV.UnSubscribeToPacketType(MAVLink.MAVLINK_MSG_ID.SERVO_OUTPUT_RAW)
        MAV.UnSubscribeToPacketType(MAVLink.MAVLINK_MSG_ID.HEARTBEAT)


print('Loading interface...')
Application.Run(ServoTunerForm())
print('Done')
