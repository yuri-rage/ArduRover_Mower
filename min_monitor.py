# -*- coding: utf-8 -*-
"""
    min_monitor.py

    Creates an IronPython dialog to display select MAVLink messages

    Tested under Windows 10, but should be Linux compatible
    (assuming that IronPython sucks less at cross-compatibility than it does ease of coding...)

    Derived from the example at https://github.com/ArduPilot/MissionPlanner/blob/master/Scripts/example10.py

    -- Yuri - Jun 2021

"""

print('\n*** MAVLink MinMonitor ***\n')
print('Loading modules...')

from collections import OrderedDict
from os import getcwd, path

import clr

clr.AddReference('MAVLink')
clr.AddReference('System.Drawing')
clr.AddReference('System.Windows.Forms')

import MAVLink
from System import Char, Func, Array
from System.Windows.Forms import Application, Screen, Form, Keys, HorizontalAlignment, \
    FlatStyle, BorderStyle, ComboBoxStyle, Button, Label, ListBox, TextBox, CheckBox, ComboBox, NumericUpDown
from System.Drawing import Point, Color

# ************************** USER DEFINABLE VALUES ************************** #

DEFAULT_NUM_MESSAGES = 5
CONFIG_FILENAME = 'min_monitor.cfg'

# *************************************************************************** #

SEVERITY = ['EMERGENCY: ', 'ALERT: ', 'CRITICAL: ', 'ERROR: ', 'WARNING: ', 'NOTICE: ', 'INFO: ', 'DEBUG: ']


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

CustomColor = MPColor()


class MinMonitorForm(Form):
    def __init__(self):
        self.received_messages = {}
        self.msg_ids = {}

        self.config = None
        self.num_messages = DEFAULT_NUM_MESSAGES
        if path.exists(CONFIG_FILENAME):
            print('Reading config...')
            self.config = open(CONFIG_FILENAME, 'r').readlines()
            for x in range(len(self.config)):
                self.config[x] = self.config[x].strip('\n')
            self.num_messages = int(self.config[0].split(',')[0])

        # we subscribe to every possible MAVLink message here
        # super inefficient, but much easier to just collect 'em all!
        for attr_name in dir(MAVLink.MAVLINK_MSG_ID):
            if attr_name.upper() == attr_name:
                attr = getattr(MAVLink.MAVLINK_MSG_ID, attr_name)
                self.msg_ids[attr.value__] = attr
                MAV.SubscribeToPacketType(attr, Func[MAVLink.MAVLinkMessage, bool](self.get_message_data))
        MAV.OnPacketReceived += self.packet_handler

        self.Text = 'MAVLink MinMonitor'
        self.Location = Point(0, 0)
        self.TopMost = True
        self.BackColor = CustomColor.MPDarkGray
        self.ForeColor = CustomColor.White
        self.Shown += self.on_load
        self.FormClosing += self.on_exit

        self.margin = 5
        start_x, start_y = 12, 10

        self.msg_widgets = []
        for x in range(self.num_messages):
            cbo_msg_id = ComboBox()
            cbo_msg_id.Width = 175
            cbo_msg_id.DropDownStyle = ComboBoxStyle.DropDown
            cbo_msg_id.FlatStyle = FlatStyle.Flat
            cbo_msg_id.BackColor = CustomColor.MPLightGray
            cbo_msg_id.ForeColor = CustomColor.White
            cbo_msg_id.DataSource = self.received_messages.keys()
            cbo_msg_id.MouseDown += self.update_message_ids
            cbo_msg_id.SelectionChangeCommitted += self.update_datasource
            cbo_msg_id.Text = ''

            cbo_msg_dataframes = ComboBox()
            cbo_msg_dataframes.Width = 120
            cbo_msg_dataframes.DropDownStyle = ComboBoxStyle.DropDown
            cbo_msg_dataframes.FlatStyle = FlatStyle.Flat
            cbo_msg_dataframes.BackColor = CustomColor.MPLightGray
            cbo_msg_dataframes.ForeColor = CustomColor.White
            cbo_msg_dataframes.Text = ''

            lbl_data = Label()
            lbl_data.Text = 'NO DATA'
            lbl_data.BackColor = CustomColor.MPMediumGray
            lbl_data.Width = 120
            lbl_data.Height = cbo_msg_id.Height - 5

            txt_min = TextBox()
            txt_min.Width = 75
            txt_min.BorderStyle = BorderStyle.FixedSingle
            txt_min.BackColor = CustomColor.MPLightGray
            txt_min.ForeColor = CustomColor.White
            txt_min.MaxLength = 10
            txt_min.TextAlign = HorizontalAlignment.Center
            txt_min.KeyPress += self.limit_to_decimal_digits

            txt_max = TextBox()
            txt_max.Width = 75
            txt_max.BorderStyle = BorderStyle.FixedSingle
            txt_max.BackColor = CustomColor.MPLightGray
            txt_max.ForeColor = CustomColor.White
            txt_max.MaxLength = 10
            txt_max.TextAlign = HorizontalAlignment.Center
            txt_max.KeyPress += self.limit_to_decimal_digits

            txt_factor = TextBox()
            txt_factor.Width = 75
            txt_factor.BorderStyle = BorderStyle.FixedSingle
            txt_factor.BackColor = CustomColor.MPLightGray
            txt_factor.ForeColor = CustomColor.White
            txt_factor.MaxLength = 10
            txt_factor.TextAlign = HorizontalAlignment.Center
            txt_factor.KeyPress += self.limit_to_decimal_digits

            self.msg_widgets.append(OrderedDict([('cbo_msg_id', cbo_msg_id),
                                                 ('cbo_msg_dataframes', cbo_msg_dataframes),
                                                 ('lbl_data', lbl_data),
                                                 ('txt_min', txt_min),
                                                 ('txt_max', txt_max),
                                                 ('txt_factor', txt_factor)]))

        self.lbl_min = Label()
        self.lbl_min.Text = 'Min'
        self.lbl_min.BackColor = CustomColor.MPDarkGray
        self.lbl_min.Width = self.msg_widgets[0]['txt_min'].Width
        self.lbl_min.Height = self.msg_widgets[0]['txt_min'].Height - 5

        self.lbl_max = Label()
        self.lbl_max.Text = 'Max'
        self.lbl_max.BackColor = CustomColor.MPDarkGray
        self.lbl_max.Width = self.msg_widgets[0]['txt_max'].Width
        self.lbl_max.Height = self.msg_widgets[0]['txt_max'].Height - 5

        self.lbl_factor = Label()
        self.lbl_factor.Text = 'Factor'
        self.lbl_factor.BackColor = CustomColor.MPDarkGray
        self.lbl_factor.Width = self.msg_widgets[0]['txt_factor'].Width
        self.lbl_factor.Height = self.msg_widgets[0]['txt_factor'].Height - 5

        self.lbl_num_messages = Label()
        self.lbl_num_messages.Text = 'Number of messages to monitor (restart to take effect)'
        self.lbl_num_messages.BackColor = CustomColor.MPDarkGray
        self.lbl_num_messages.AutoSize = True

        self.spn_num_messages = NumericUpDown()
        self.spn_num_messages.Width = 40
        self.spn_num_messages.BorderStyle = BorderStyle.FixedSingle
        self.spn_num_messages.BackColor = CustomColor.MPLightGray
        self.spn_num_messages.ForeColor = CustomColor.White
        self.spn_num_messages.Value = self.num_messages

        self.chk_hide_factors = CheckBox()
        self.chk_hide_factors.FlatAppearance.BorderSize = 1
        self.chk_hide_factors.FlatAppearance.BorderColor = CustomColor.MPLightGray
        self.chk_hide_factors.Text = 'Hide threshold/scaling preferences'
        self.chk_hide_factors.AutoSize = True

        self.chk_sticky = CheckBox()
        self.chk_sticky.FlatAppearance.BorderSize = 1
        self.chk_sticky.FlatAppearance.BorderColor = CustomColor.MPLightGray
        self.chk_sticky.Text = 'Always on top'
        self.chk_sticky.AutoSize = True

        self.lbl_status = Label()
        self.lbl_status.Text = 'No messages received'
        self.lbl_status.BackColor = CustomColor.MPMediumGray
        self.lbl_status.Height = self.msg_widgets[0]['txt_min'].Height - 5

        # pseudo-responsive form layout
        x, y = start_x, start_y
        max_x = 0
        x = start_x + (self.msg_widgets[0]['cbo_msg_id'].Width +
                       self.msg_widgets[0]['cbo_msg_dataframes'].Width +
                       self.msg_widgets[0]['lbl_data'].Width) + self.margin * 4
        x, y, x_extent = \
            self.add_control_horizontal(self.lbl_min, x, y, self.margin)
        x, y, x_extent = \
            self.add_control_horizontal(self.lbl_max, x, y, self.margin)
        x, y, x_extent = \
            self.add_control_vertical(self.lbl_factor, x, y, self.margin)
        for widget in self.msg_widgets:
            x = start_x
            for control in widget.items():
                x, y, x_extent = self.add_control_horizontal(control[1], x, y, self.margin)
            max_x = max([x_extent, max_x])
            y += widget.items()[0][1].Height + self.margin
        self.Width = max_x + self.margin * 4
        self.WideWidth = self.Width
        self.NarrowWidth = self.msg_widgets[0]['lbl_data'].Location.X + \
                           self.msg_widgets[0]['lbl_data'].Width + self.margin * 5
        y += 20
        x, y, x_extent = self.add_control_horizontal(self.spn_num_messages, start_x, y, self.margin)
        x, y, x_extent = self.add_control_vertical(self.lbl_num_messages, x, y + 3, self.margin)
        x, y, x_extent = self.add_control_vertical(self.chk_hide_factors, start_x + 3, y + 5, self.margin)
        x, y, x_extent = self.add_control_vertical(self.chk_sticky, x, y, self.margin)
        self.lbl_status.Width = self.Width - self.margin * 7
        x, y, x_extent = self.add_control_vertical(self.lbl_status, start_x, y + 3, self.margin)
        self.Height = y + self.lbl_status.Height + self.margin * 5

    def configure_messages(self):
        line_num = 1
        for widget in self.msg_widgets:
            line_index = 0
            for control in widget.items():
                if 'lbl' not in control[0]:
                    try:
                        control[1].Text = str(self.config[line_num].split(',')[line_index])
                    except IndexError:
                        pass
                    line_index += 1
            line_num += 1

    def update_message_ids(self, sender, event):
        sender.DataSource = sorted(self.received_messages.keys())

    def update_datasource(self, sender, event):
        for widget in self.msg_widgets:
            if widget['cbo_msg_id'] == sender:
                widget['cbo_msg_dataframes'].DataSource = None
                widget['cbo_msg_dataframes'].DataSource = sorted(self.received_messages[sender.SelectedItem].keys())
                widget['cbo_msg_dataframes'].Text = ''
                widget['lbl_data'].Text = 'NO DATA'

    @staticmethod
    def limit_to_decimal_digits(sender, event):
        if not Char.IsDigit(event.KeyChar) and \
                not Char.IsControl(event.KeyChar) and \
                not event.KeyChar == '.' and \
                not event.KeyChar == '-':
            event.Handled = True
        if event.KeyChar == '.' and '.' in sender.Text:
            event.Handled = True

    def set_sticky(self, sender, event):
        if sender.Checked:
            self.TopMost = True
            return
        self.TopMost = False

    def toggle_width(self, sender, event):
        self.lbl_min.Visible = not sender.Checked
        self.lbl_max.Visible = not sender.Checked
        self.lbl_factor.Visible = not sender.Checked
        for widget in self.msg_widgets:
            for control in widget.items():
                if 'txt' in control[0]:
                    control[1].Visible = not sender.Checked
        if sender.Checked:
            self.Width = self.NarrowWidth
            self.lbl_status.Width = self.Width - self.margin * 7
            return
        self.Width = self.WideWidth
        self.lbl_status.Width = self.Width - self.margin * 7

    def add_control_vertical(self, control, x, y, margin):
        control.Location = Point(x, y)
        self.Controls.Add(control)
        return x, y + control.Height + margin, x + control.Width + margin

    def add_control_horizontal(self, control, x, y, margin):
        control.Location = Point(x, y)
        self.Controls.Add(control)
        return x + control.Width + margin, y, x + control.Width + margin

    def display_message_data(self, message_name, msg_data):
        for widget in self.msg_widgets:
            if message_name == widget['cbo_msg_id'].Text:
                data = msg_data[widget['cbo_msg_dataframes'].Text]
                min, max, factor = None, None, 1.0
                try:
                    min = float(widget['txt_min'].Text)
                    max = float(widget['txt_max'].Text)
                except ValueError:
                    pass
                try:
                    factor = float(widget['txt_factor'].Text)
                except ValueError:
                    pass
                if isinstance(data, Array):
                    data = bytes(data)
                try:
                    data = float(data) * factor
                    widget['lbl_data'].Text = str(data)
                    if min <= data <= max:
                        widget['lbl_data'].BackColor = CustomColor.MPMediumGray
                        continue
                    if min is not None and max is not None:
                        widget['lbl_data'].BackColor = CustomColor.DarkRed
                        continue
                    widget['lbl_data'].BackColor = CustomColor.MPMediumGray
                except ValueError:
                    pass

    def get_message_data(self, message):
        message_name = str(self.msg_ids[message.msgid])
        msg_data = {}
        for attr_name in dir(message.data):
            attr = getattr(message.data, attr_name)
            if not callable(attr) and '__' not in attr_name:
                msg_data[attr_name] = getattr(message.data, attr_name)
        self.received_messages[message_name] = msg_data
        self.display_message_data(message_name, msg_data)
        return True

    def packet_handler(self, obj, message):
        try:
            if message.msgid == MAVLink.MAVLINK_MSG_ID.STATUSTEXT.value__:
                self.lbl_status.Text = SEVERITY[message.data.severity] + str(bytes(message.data.text))
        except Exception as inst:
            print(inst)  # not sure what situation would raise this, so leaving it for debugging

    def on_load(self, sender, event):
        self.chk_hide_factors.CheckedChanged += self.toggle_width
        self.chk_sticky.CheckedChanged += self.set_sticky
        if self.config is not None:
            self.chk_hide_factors.Checked = bool(int(self.config[0].split(',')[1]))
            self.chk_sticky.Checked = bool(int(self.config[0].split(',')[2]))
        self.toggle_width(self.chk_hide_factors, None)
        self.set_sticky(self.chk_sticky, None)
        if self.config is not None:
            self.configure_messages()
        print('Running...')

    def on_exit(self, sender, event):
        for attr_name in dir(MAVLink.MAVLINK_MSG_ID):
            if attr_name.upper() == attr_name:
                attr = getattr(MAVLink.MAVLINK_MSG_ID, attr_name)
                self.msg_ids[attr.value__] = attr
                MAV.UnSubscribeToPacketType(attr)
        print('Saving config: {}'.format(path.join(getcwd(), CONFIG_FILENAME)))
        f = open(CONFIG_FILENAME, 'w')
        f.write(str(self.spn_num_messages.Text) + ',')
        f.write(str(int(self.chk_hide_factors.Checked)) + ',')
        f.write(str(int(self.chk_sticky.Checked)) + ',\n')
        for widget in self.msg_widgets:
            for control in widget.items():
                if 'lbl' not in control[0]:
                    f.write('{},'.format(control[1].Text))
            f.write('\n')
        f.close()


print('Loading interface...')
Application.Run(MinMonitorForm())
print('Done')
