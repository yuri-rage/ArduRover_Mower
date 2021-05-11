import clr
clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import Application, Screen, Form, Button, Label, FlatStyle
from System.Drawing import Point, Color

mower = MAV.MAV.cs

class TestForm(Form):
	def __init__(self):
		self.Text = "Maximum Roverdrive"
		self.Location = Point(0, 0)
		screenSize = Screen .GetWorkingArea(self)
		self.Height = screenSize.Height
		self.Width = screenSize.Width / 6
		self.BackColor = Color.FromArgb(38, 39, 40)
		self.ForeColor = Color.White

		self.saveWPButton = Button()
		self.saveWPButton.Width = 150
		self.saveWPButton.Location = Point(10, 10)
		self.saveWPButton.FlatStyle = FlatStyle.Flat
		self.saveWPButton.FlatAppearance.BorderSize = 1
		self.saveWPButton.FlatAppearance.BorderColor = Color.FromArgb(68, 69, 70)
		self.saveWPButton.BackColor = Color.FromArgb(165, 203, 70)
		self.saveWPButton.ForeColor = Color.Black
		self.saveWPButton.Text = "Set Ch 8 Save WP"
		self.saveWPButton.Click += self.saveWP
		self.Controls.Add(self.saveWPButton)
		
		self.mowerCtlButton = Button()
		self.mowerCtlButton.Width = 150
		self.mowerCtlButton.Location = Point(10, 35)
		self.mowerCtlButton.FlatStyle = FlatStyle.Flat
		self.mowerCtlButton.FlatAppearance.BorderSize = 1
		self.mowerCtlButton.FlatAppearance.BorderColor = Color.FromArgb(68, 69, 70)
		self.mowerCtlButton.BackColor = Color.FromArgb(165, 203, 70)
		self.mowerCtlButton.ForeColor = Color.Black
		self.mowerCtlButton.Text = "Set Ch 8 Blade Control"
		self.mowerCtlButton.Click += self.controlBlades
		self.Controls.Add(self.mowerCtlButton)
		
		self.channel8Value = Label()
		self.channel8Value.Location = Point(165, 15)
		self.channel8Value.Text = "Channel 8 raw value: " + str(Script.GetParam("RC8_OPTION"))
		self.channel8Value.AutoSize = True
		self.Controls.Add(self.channel8Value)

	def saveWP(self, sender, event):
		Script.ChangeParam("RC8_OPTION", 7.0)
		self.channel8Value.Text = "Channel 8 raw value: " + str(Script.GetParam("RC8_OPTION"))
		
	def controlBlades(self, sender, event):
		Script.ChangeParam("RC8_OPTION", 35.0)
		self.channel8Value.Text = "Channel 8 raw value: " + str(Script.GetParam("RC8_OPTION"))
		
form = TestForm()
form.ShowDialog()
