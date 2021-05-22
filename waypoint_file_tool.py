# -*- coding: utf-8 -*-
"""
    waypoint_file_tool.py

    Creates an IronPython dialog to manipulate Mission Planner .waypoint and .poly files

    Edit the DEFAULT_PATH variable below with the default directory for your mission files

    Tested under Windows 10, but should be Linux compatible
    (assuming that IronPython sucks less at cross-compatibility than it does ease of coding...)

    Ideally this would be deployed as several files and installed as such, but for ease of distribution,
    it's just one monstrosity of a single file.

    -- Yuri - May 2021

"""

print('\n*** Waypoint File Tool ***\n')
print('Loading modules...')

import clr
from os import listdir
from os import path
from os import sep as file_separator
from re import sub as regex_sub
from collections import namedtuple
from math import radians, degrees, sin, cos, atan2, sqrt
from sys import float_info

clr.AddReference('System.Drawing')
clr.AddReference('System.Windows.Forms')

from System import Char
from System.Windows.Forms import Application, Screen, Form, Keys, HorizontalAlignment, \
    FlatStyle, BorderStyle, ComboBoxStyle, Button, Label, ListBox, TextBox, CheckBox, ComboBox, NumericUpDown
from System.Drawing import Point, Color

# ************************** USER DEFINABLE VALUES ************************** #

DEFAULT_PATH = 'D:\\Documents\\Mission Planner\\Missions\\'  # Windows
# DEFAULT_PATH = '/home/yuri/Documents/Mission Planner/Missions/'  # Linux
OUTPUT_FILE_PREFIX = 'zz_'
OUTPUT_FILE_SUFFIX = ''
DEFAULT_ALTITUDE = 30.48  # meters
ALWAYS_ON_TOP = True

# *************************************************************************** #

EARTH_RADIUS = 6371e3  # in meters


class PointLatLngAlt:
    """ I think you should be able to use Mission Planner's C# class here, but I don't know how to import it
        This class mirrors the required functionality """

    def __init__(self, lat=0.0, lng=0.0, alt=0.0, tag=''):
        self.Lat = lat
        self.Lng = lng
        self.Alt = alt
        self.Tag = tag

    def __str__(self):
        return ",".join([str(self.Lat), str(self.Lng), str(self.Alt), str(self.Tag)])


try:
    debug_val = cs.HomeLocation
except NameError:
    """ If you install IronPython, you can run this script without Mission Planner
        However, the cs object is not available, so we have to create it
        
        To run as a standalone script, enter this at a Windows command line prompt:
        ipy.exe .\waypoint_file_tool.py
        
        Or this in a Linux terminal:
        ipy ./waypoint_file_tool.py """


    class DebugCS:
        def __init__(self):
            self.HomeLocation = PointLatLngAlt(0.0, 0.0, 0.0)
            self.PlannedHomeLocation = PointLatLngAlt(33.31256, -111.68366, 1335.7)


    cs = DebugCS()


def get_home_location():
    if cs.HomeLocation.Lat + cs.HomeLocation.Lng + cs.HomeLocation.Alt < 1:
        return cs.PlannedHomeLocation
    return cs.HomeLocation


def haversine_distance(point1, point2):
    """ distance between coordinates -- https://www.movable-type.co.uk/scripts/latlong.html """
    phi1 = radians(point1.Lat)
    phi2 = radians(point2.Lat)
    delta_phi = radians(point2.Lat - point1.Lat)
    delta_lambda = radians(point2.Lng - point1.Lng)

    a = sin(delta_phi / 2) * sin(delta_phi / 2) + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) * sin(delta_lambda / 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return EARTH_RADIUS * c  # in meters


def midpoint(point1, point2):
    """ midpoint between coordinates
        https://stackoverflow.com/questions/4656802/midpoint-between-two-latitude-and-longitude """
    phi1 = radians(point1.Lat)
    phi2 = radians(point2.Lat)
    lambda1 = radians(point1.Lng)
    delta_lambda = radians(point2.Lng - point1.Lng)

    b_x = cos(phi2) * cos(delta_lambda)
    b_y = cos(phi2) * sin(delta_lambda)
    phi_mid = atan2(sin(phi1) + sin(phi2), sqrt((cos(phi1) + b_x) * (cos(phi1) + b_x) + b_y * b_y))
    lambda_mid = lambda1 + atan2(b_y, cos(phi1) + b_x)

    alt_avg = (point1.Alt + point2.Alt) / 2

    return PointLatLngAlt(degrees(phi_mid), degrees(lambda_mid), alt_avg)


class InvalidFile(Exception):
    pass


def is_valid_wp_line(line):
    arr = line.split()
    if len(arr) != 12:
        return False
    if arr[3] != '16':
        return False
    return True


def is_valid_poly_line(line):
    arr = line.split()
    if len(arr) != 2:
        return False
    return True


MPFileInfo = namedtuple('MPFileInfo',
                        ['file_type', 'lat_index', 'lng_index', 'alt_index', 'start_index', 'is_valid_line'])

wp_file = MPFileInfo(file_type='.waypoints',
                     lat_index=8,
                     lng_index=9,
                     alt_index=10,
                     start_index=2,
                     is_valid_line=is_valid_wp_line)

poly_file = MPFileInfo(file_type='.poly',
                       lat_index=0,
                       lng_index=1,
                       alt_index=0,
                       start_index=1,
                       is_valid_line=is_valid_poly_line)


class WaypointConverter:
    def __init__(self,
                 filename=None,
                 output_file_type=wp_file,
                 num_reverse_passes=0,
                 default_alt=DEFAULT_ALTITUDE):
        self.output_filename = None
        if filename is None:
            return
        if not path.exists(filename):
            raise InvalidFile
        lines, file_info = self._read_file(filename)
        points = self._raw_to_points(lines, file_info, default_alt)
        if output_file_type == wp_file and num_reverse_passes > 0:
            points = self._reverse_perimeter(points, num_reverse_passes)
        self.output_filename = self._convert_file(points, filename, output_file_type)

    def _read_file(self, filename):
        with open(filename, "r") as f:
            lines = f.readlines()
            f.close()
        if len(lines) < 2:  # any file worth processing needs more than 1 line
            raise InvalidFile
        file_info = None
        if self._is_wp_file(lines):
            file_info = wp_file
        if self._is_poly_file(lines):
            file_info = poly_file
        if file_info is None:
            raise InvalidFile
        return lines, file_info

    @staticmethod
    def _raw_to_points(raw_lines, file_info, default_alt):
        points = []
        for x in range(file_info.start_index, len(raw_lines)):
            line = raw_lines[x]
            if file_info.is_valid_line(line):
                line = line.split()
                lat = float(line[file_info.lat_index])
                lng = float(line[file_info.lng_index])
                alt = float(line[file_info.alt_index]) if file_info.alt_index else default_alt
                points.append(PointLatLngAlt(lat, lng, alt, ''))
        return points

    @staticmethod
    def _get_num_perimeter_points(points):
        shortest_dist = float_info.max
        start_point = points[0]
        index = None
        for x in range(1, len(points)):
            dist = haversine_distance(start_point, points[x])
            if dist < shortest_dist:
                shortest_dist = dist
                index = x
        return index

    def _reverse_perimeter(self, points, num_reverse_passes):
        num_perimeter_points = self._get_num_perimeter_points(points)
        if num_perimeter_points * (num_reverse_passes + 2) > len(points):
            num_reverse_passes = int(len(points) / num_perimeter_points - 2)  # truncate to the max feasible number
        index = 0
        for i in range(num_reverse_passes):
            points[index:num_perimeter_points + index] = points[index:num_perimeter_points + index][::-1]
            index += num_perimeter_points

        # now cover the gap created by reversing the pattern midstream
        index_split1 = num_reverse_passes * num_perimeter_points
        if index_split1 < len(points):
            index_split2 = num_reverse_passes * num_perimeter_points - 1
            index_split3 = (num_reverse_passes + 1) * num_perimeter_points - 1
            index_split4 = (num_reverse_passes - 1) * num_perimeter_points
            split_point1 = midpoint(points[index_split1], points[index_split2])  # neatly split the lane
            split_point2 = midpoint(points[index_split3], points[index_split4])
            reverse_point = midpoint(split_point1, split_point2)  # point halfway up the reverse lane
            reverse_point = midpoint(reverse_point, split_point2)  # reverse 3/4 of the way up the lane
            points.insert(index_split1, reverse_point)
        points.insert(0, points[num_perimeter_points - 1])  # this used to be waypoint 1, so let's start there
        return points

    def _convert_file(self, points, filename, output_file_type):
        output_filename = self._get_output_filename(filename, output_file_type.file_type)
        f = open(output_filename, "w")
        if output_file_type == poly_file:
            self._write_poly_file(f, points)
        if output_file_type == wp_file:
            self._write_wp_file(f, points)
        f.close()
        return output_filename

    @staticmethod
    def _write_poly_file(f, points):
        f.write('# saved by Waypoint File Tool\n')
        for point in points:
            f.write(' '.join([str(point.Lat), str(point.Lng)]) + '\n')

    @staticmethod
    def _write_wp_file(f, points):
        f.write('QGC WPL 110\n')
        h = get_home_location()
        f.write('\t'.join(['0', '1', '0', '16', '0', '0', '0', '0', str(h.Lat), str(h.Lng), str(h.Alt), '1']) + '\n')
        for x in range(len(points)):
            f.write('\t'.join([str(x + 1), '0', '3', '16', '0', '0', '0', '0',
                               str(points[x].Lat), str(points[x].Lng), str(points[x].Alt), '1']) + '\n')

    @staticmethod
    def _get_output_filename(filename, extension):
        output_path, output_name = path.split(filename)
        output_name = path.splitext(output_name)[0]
        output_name = regex_sub('(_\d\d)$', '', output_name)
        if not output_name.startswith(OUTPUT_FILE_PREFIX):
            output_name = OUTPUT_FILE_PREFIX + output_name
        if not output_name.endswith(OUTPUT_FILE_SUFFIX):
            output_name = output_name + OUTPUT_FILE_SUFFIX
        file_count = 0
        output_name = output_name + '_??' + extension
        while path.exists(path.join(output_path, output_name.replace('??', '{0:02d}'.format(file_count)))):
            file_count += 1
        output_name = output_name.replace('??', '{0:02d}'.format(file_count))
        return path.join(output_path, output_name)

    @staticmethod
    def _is_wp_file(lines):
        if len(lines[1].split()) == 12:  # wp files have 12 fields in lines 1 and beyond
            return True
        return False

    @staticmethod
    def _is_poly_file(lines):
        if len(lines[1].split()) == 2:  # poly files have 12 fields in lines 1 and beyond
            return True
        return False


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


class WaypointFileToolForm(Form):
    def __init__(self):
        self.file_path = DEFAULT_PATH
        self.Text = 'Waypoint File Tool'
        self.Location = Point(0, 0)
        self.TopMost = ALWAYS_ON_TOP
        screen_size = Screen.GetWorkingArea(self)
        num_buttons = 3
        btn_width = 150
        margin = 5
        start_x, start_y = 12, 10
        self.Height = screen_size.Height
        self.Width = btn_width * num_buttons + margin * (num_buttons + 7)
        self.BackColor = CustomColor.MPDarkGray
        self.ForeColor = CustomColor.White
        """ OpenFileDialog does not appear to work in Mission Planner scripts...
                so, we create a rudimentary file picker with a textbox and listbox """
        self.txt_path = TextBox()
        self.txt_path.Width = self.Width - (margin * 8)
        self.txt_path.BorderStyle = BorderStyle.FixedSingle
        self.txt_path.BackColor = CustomColor.MPLightGray
        self.txt_path.ForeColor = CustomColor.White
        self.txt_path.Text = self.file_path
        self.txt_path.LostFocus += self.refresh_filenames

        self.lst_files = ListBox()
        self.lst_files.Width = self.txt_path.Width
        self.lst_files.Height = self.Height / 5
        self.lst_files.BorderStyle = BorderStyle.FixedSingle
        self.lst_files.BackColor = CustomColor.MPLightGray
        self.lst_files.ForeColor = CustomColor.White
        self.lst_files.SelectedIndexChanged += self.file_selection_changed

        self.btn_output_wp = Button()
        self.btn_output_wp.Width = 150
        self.btn_output_wp.FlatStyle = FlatStyle.Flat
        self.btn_output_wp.FlatAppearance.BorderSize = 1
        self.btn_output_wp.FlatAppearance.BorderColor = CustomColor.MPLightGray
        self.btn_output_wp.BackColor = CustomColor.MPGreen
        self.btn_output_wp.ForeColor = CustomColor.Black
        self.btn_output_wp.Text = 'Output as WP'
        self.btn_output_wp.Click += self.convert_file

        self.btn_output_poly = Button()
        self.btn_output_poly.Width = 150
        self.btn_output_poly.FlatStyle = FlatStyle.Flat
        self.btn_output_poly.FlatAppearance.BorderSize = 1
        self.btn_output_poly.FlatAppearance.BorderColor = CustomColor.MPLightGray
        self.btn_output_poly.BackColor = CustomColor.MPGreen
        self.btn_output_poly.ForeColor = CustomColor.Black
        self.btn_output_poly.Text = 'Output as POLY'
        self.btn_output_poly.Click += self.convert_file

        self.btn_refresh_files = Button()
        self.btn_refresh_files.Width = 150
        self.btn_refresh_files.FlatStyle = FlatStyle.Flat
        self.btn_refresh_files.FlatAppearance.BorderSize = 1
        self.btn_refresh_files.FlatAppearance.BorderColor = CustomColor.MPLightGray
        self.btn_refresh_files.BackColor = CustomColor.MPGreen
        self.btn_refresh_files.ForeColor = CustomColor.Black
        self.btn_refresh_files.Text = 'Refresh Files'
        self.btn_refresh_files.Click += self.refresh_filenames
        self.AcceptButton = self.btn_refresh_files

        self.spn_num_perimeter_passes = NumericUpDown()
        self.spn_num_perimeter_passes.Width = 40
        self.spn_num_perimeter_passes.BorderStyle = BorderStyle.FixedSingle
        self.spn_num_perimeter_passes.BackColor = CustomColor.MPLightGray
        self.spn_num_perimeter_passes.ForeColor = CustomColor.White
        self.spn_num_perimeter_passes.Value = 3

        self.chk_reverse_perimeter = CheckBox()
        self.chk_reverse_perimeter.FlatAppearance.BorderSize = 1
        self.chk_reverse_perimeter.FlatAppearance.BorderColor = CustomColor.MPLightGray
        self.chk_reverse_perimeter.Text = 'Reverse Perimeter - Enter desired number of passes:'
        self.chk_reverse_perimeter.AutoSize = True
        self.chk_reverse_perimeter.CheckedChanged += self.set_txt_num_perimeter_passes_state
        self.chk_reverse_perimeter.Checked = True

        self.lbl_default_altitude = Label()
        self.lbl_default_altitude.Text = 'Waypoint Altitude (if unspecified):'
        self.lbl_default_altitude.AutoSize = True

        self.txt_default_altitude = TextBox()
        self.txt_default_altitude.Width = 50
        self.txt_default_altitude.BorderStyle = BorderStyle.FixedSingle
        self.txt_default_altitude.BackColor = CustomColor.MPLightGray
        self.txt_default_altitude.ForeColor = CustomColor.White
        self.txt_default_altitude.MaxLength = 5
        self.txt_default_altitude.TextAlign = HorizontalAlignment.Center
        self.txt_default_altitude.Text = str(round(DEFAULT_ALTITUDE * 3.28084, 2))[:5]
        self.txt_default_altitude.KeyPress += self.limit_to_decimal_digits

        self.cbo_default_altitude = ComboBox()
        self.cbo_default_altitude.Width = 60
        self.cbo_default_altitude.DropDownStyle = ComboBoxStyle.DropDownList
        self.cbo_default_altitude.FlatStyle = FlatStyle.Flat
        self.cbo_default_altitude.BackColor = CustomColor.MPLightGray
        self.cbo_default_altitude.ForeColor = CustomColor.White
        self.cbo_default_altitude.DataSource = ['Feet', 'Meters']
        self.cbo_default_altitude.SelectionChangeCommitted += self.convert_altitude_units

        self.lbl_status = Label()
        self.lbl_status.Text = 'Choose a file...'
        self.lbl_status.BackColor = CustomColor.MPMediumGray
        self.lbl_status.Width = self.txt_path.Width
        self.lbl_status.Height = self.txt_path.Height - 5

        # pseudo-responsive form layout
        x, y = start_x, start_y
        x, y = self.add_control_vertical(self.txt_path, x, y, margin)
        x, y = self.add_control_vertical(self.lst_files, x, y, margin)
        x, y = self.add_control_horizontal(self.btn_output_wp, x, y, margin)
        x, y = self.add_control_horizontal(self.btn_output_poly, x, y, margin)
        x, y = self.add_control_vertical(self.btn_refresh_files, x, y, margin + 10)
        x, y = self.add_control_horizontal(self.chk_reverse_perimeter, start_x, y, margin)
        x, y = self.add_control_vertical(self.spn_num_perimeter_passes, x - 5, y, margin + 10)
        x, y = self.add_control_horizontal(self.lbl_default_altitude, start_x, y + 3, margin)
        x, y = self.add_control_horizontal(self.txt_default_altitude, x, y - 3, margin + 3)
        x, y = self.add_control_vertical(self.cbo_default_altitude, x, y, margin)
        self.Height = y + 100
        self.add_control_vertical(self.lbl_status, start_x, self.Height - 60, margin)

        self.set_txt_num_perimeter_passes_state(None, None)
        self.refresh_filenames(None, None)

    def add_control_vertical(self, control, x, y, margin):
        control.Location = Point(x, y)
        self.Controls.Add(control)
        return x, y + control.Height + margin

    def add_control_horizontal(self, control, x, y, margin):
        control.Location = Point(x, y)
        self.Controls.Add(control)
        return x + control.Width + margin, y

    def refresh_filenames(self, sender, event, refresh_lbl_status=True):
        file_path = self.txt_path.Text
        previous_selection = self.lst_files.SelectedItem
        if not path.exists(file_path):
            self.lst_files.DataSource = ['', 'Path does not exist...']
            self.file_selection_changed(None, None)
            return False
        if file_path[-1] != file_separator:
            file_path += file_separator
            self.txt_path.Text = file_path
        self.lst_files.DataSource = \
            [f for f in listdir(file_path) if path.isfile(path.join(file_path, f)) and
             ('.waypoints' in f or '.poly' in f)]
        if previous_selection in self.lst_files.DataSource:
            self.lst_files.SelectedItem = previous_selection
        if refresh_lbl_status:
            self.file_selection_changed(None, None)
        return True

    def file_selection_changed(self, sender, event):
        self.lbl_status.Text = self.lst_files.SelectedItem

    def limit_to_decimal_digits(self, sender, event):
        if not Char.IsDigit(event.KeyChar) and not Char.IsControl(event.KeyChar) and not event.KeyChar == '.':
            event.Handled = True
        if event.KeyChar == '.' and '.' in sender.Text:
            event.Handled = True

    def set_txt_num_perimeter_passes_state(self, sender, event):
        self.spn_num_perimeter_passes.Enabled = True if self.chk_reverse_perimeter.Checked else False

    def convert_altitude_units(self, sender, event):
        if not self.txt_default_altitude.Text:
            return
        alt = float(self.txt_default_altitude.Text)
        factor = 3.28084
        if self.cbo_default_altitude.Text == 'Meters':
            factor = 1 / factor
        self.txt_default_altitude.Text = str(round(alt * factor, 2))[:5]

    def get_default_altitude(self):
        if not self.txt_default_altitude.Text:
            return 0.0
        alt = float(self.txt_default_altitude.Text)
        if self.cbo_default_altitude.Text == 'Feet':
            alt /= 3.28084
        return round(alt, 3)

    def convert_file(self, sender, event):
        try:
            output_file_type = poly_file
            num_reverse_passes = 0
            if sender == self.btn_output_wp:
                output_file_type = wp_file
                if self.spn_num_perimeter_passes.Enabled and int(self.spn_num_perimeter_passes.Value):
                    num_reverse_passes = int(self.spn_num_perimeter_passes.Value)
            filename = path.join(self.txt_path.Text, self.lst_files.SelectedItem)
            default_altitude = self.get_default_altitude()
            result = WaypointConverter(filename, output_file_type, num_reverse_passes, default_altitude).output_filename
            result = '{old_f}   →   {new_f}'.format(old_f=path.basename(filename), new_f=path.basename(result))
        except InvalidFile:
            result = 'Conversion failed - invalid file/filetype'
        self.refresh_filenames(None, None, False)
        self.lbl_status.Text = result


print('Running...')
Application.Run(WaypointFileToolForm())
print('Done')
