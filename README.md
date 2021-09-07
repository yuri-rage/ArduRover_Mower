# ArduRover_Mower

A collection of files that may be of use to ArduPilot Rover users.

### ArmSwitchParkingBrake.lua

Monitors an RC channel for a threshold PWM value and arms/disarms the flight controller accordingly.  Useful when RC channels are limited - allows "overloading" a channel with an additional arm/disarm function.  I used it on a three position switch for the following functions:
* Position 1: Engine Kill/Disarm
* Position 2: Engine Run/Disarm
* Position 3: Engine Run/Arm

Additionally, monitors the flight mode for changes and sets the parking brake servo accordingly (on when HOLD mode is selected).

### AutoBlades.lua

Controls a relay (lawnmower blade PTO) based on an RC channel's PWM value and autopilot mode.  The RC channel acts as an enable switch, and behavior changes slightly based on the flight controller's arming state and autopilot mode.  The relay is effectively disabled when the flight controller is disarmed or hold mode is selected.  If the RC channel threshold is met when auto mode is selected and the mission is active beyond the first waypoint, the relay turns on, and then off again when the mission is complete.  In any other autopilot mode, the RC channel acts as a simple on/off switch.

### AutoChokeSaveWP.lua

Monitors transmitter output for ignition and starter signals.  When the ignition is off, the starter signal toggles between cold and warm starts (choke on vs choke off).  When cold start is selected, it presets a servo connected to the choke, and then slowly outfeeds the choke upon starter release.  If the vehicle is armed, the starter switch becomes a "save waypoint" switch (if your transmitter has only one spring loaded toggle switch, this can be helpful "overloading" of switch functionality).

### MinFixType.lua

Monitors a GPS instance for minimum performance (fix type) during waypoint missions.  If the GPS reports a fix type less than desired, the mission is paused until the fix type is again reported adequate.

### WaypointFileTool with Reverse.xlsm

Macro enabled Excel workbook that converts between waypoint and polygon files.  Also capable of generating reverse direction perimeter passes for mowing.

### MultiMission.lua

If AUTO mode is commanded via the RC transmitter, and no waypoints are loaded, this script loads missions sequentially from the root of the SD card (0.waypoints, 1.waypoints, etc).  It will run those missions consecutively until the last one completes or another flight mode is commanded.

### servo_tuner.py

Intended to augment the Servo Output page on Mission Planner's Setup tab.  Shows minimum, maximum, difference, and midpoint for each servo's PWM output.  Allows manual override of RC input to be more precise than using an RC transmitter for tuning position/speed.  **Word of caution** - since the script is capable of overriding RC transmitter commands, please use it with care.  It is capable of producing full speed/travel output at a mis-click of the mouse!

### waypoint_file_tool.py

Script that builds upon the Excel tool to convert between waypoint and polygon files.  Provides reversed perimeter passes for spiral patterns just like the Excel tool.  Can be run within the Misison Planner interface.

### min_monitor.py

A friendlier MAVLink Inspector for Mission Planner, allowing for compact viewing of selectable MAVLink messages with color coding based on threshold values and scaling to view the data in proper units rather than their raw transmitted values.

### .param files

* ArduPilot parameter dumps that may be of interest
* Filenames describe the intent

### pid-simulator.py

A very rudimentary PID simulation (visualizer) using matplotlib.  Allows real-time changes to the terms to visualize how the controller responds.  Requires matplotlib and simple-pid (e.g., "pip install matplotlib simple-pid").

## Notes

Good reading:
* https://github.com/ArduPilot/ardupilot/issues/8788
* https://discuss.ardupilot.org/t/skid-steer-mower-overshooting-pivot-turns/28910/104

Mower is well tuned now

ATC_ACCEL_MAX 0.6-0.8 seems to help smooth starts and possibly helps pivot turns

ATC_DECEL_MAX 1.7-5.0 plus ATC_BRAKE 1 is the best discovery yet! Enables significant decel approaching sharp turns and limits overshoots

ATC_STR_RATE_FF 0.3-0.4, ATC_STR_RATE_MAX and WP_PIVOT_RATE 41

ATC_STR_RATE_I 0.9 seems to allow faster update of yaw and fixes some of the s-turn issues

ATC_STR_ANG_P of 1.0 - 1.7 seems appropriate - any more than that overshoots (1.7 set for now)

WP_RADIUS and WP_OVERSHOOT have big effects (increased WP_RADIUS to 1.3, decreased WP_OVERSHOOT to 0.1-0.3)

WP_SPEED 0 does not use CRUISE_SPEED - it literally stands still in auto mode

NAVL1_PERIOD 2 - be careful with this one - make sure everything else is tuned well, or things will get out of hand with aggressive overshoot corrections.  Works really well in conjunction with BendyRuler obstacle avoidance once things are well tuned.

Disabling GPS_AUTO_CFG confuses EKF3 (never sees GPS config data) - boots faster but constantly gives "Unhealthy GPS Signal" messages

GPS_RATE_MS 100 and GPS_RATE_MS2 - set to 100 and forget about it

Using GPS_DRV_OPTIONS 0 is generally too slow for GPS heading - recommend direct RTCCM3 injects with crossover TX/RX from one SimpleRTK board to the other

BendyRuler OA works nicely with fences in 4.1.0-Beta1.  Likely accepts only integer values for circular fences (need to test further).

## Deprecated:

* See [MaximumRoverdrive](https://github.com/yuri-rage/MaximumRoverdrive)
* I kept these files here as a reference for those interested, particularly since ArduPilot scripting documentation isn't very complete.

### Waypoint File Tool (old version)

* Excel Macro enabled workbook that imports waypoint or polygon files generated by Mission Planner software and converts between the two

### test.py

Simple script for Mission Planner's built-in interpreter - changes RC channel 8 from Save Waypoint to Relay 3 control with a single mouse click.  Not pretty.  Functional.

### ArmSwitchParkingBrake (4.0.0).lua

This script works with ArduPilot 4.0.0 and early 4.1.0-dev builds.  4.1.0-beta and later have renamed ahrs:prearm_healthy to ahrs:healthy.

### armSwitch.lua

Monitors an RC channel for a threshold PWM value and arms/disarms the flight controller accordingly.  Useful when RC channels are limited - allows "overloading" a channel with an additional arm/disarm function.  I used it on a three position switch for the following functions:
* Position 1: Engine Kill/Disarm
* Position 2: Engine Run/Disarm
* Position 3: Engine Run/Arm

### duskLights.lua

Builds upon solarElevUTC.lua, which should run on any OS-based interpreter.  duskLights.lua is modified to work with Ardupilot's scripting architecture, accounting for its lack of exposed libraries (os.date and os.time are not available).  Uses an iterative approach to calculate date/time from GPS week number and GPS time of week (in milliseconds).  Turns a relay (lights) on when the sun dips below a definable elevation.  Tested on Cube Orange and Mission Planner with success.

### solarElevUTC.lua

Calculates solar elevation at current system time for a given latitude/longitude.  Intent is to use GPS coordinates to derive sun angle and use the information to turn lights on/off approaching dusk/dawn.  Runs on an OS interpreter - not optimized for ArduPilot.

