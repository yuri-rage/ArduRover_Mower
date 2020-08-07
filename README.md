# ArduRover_Mower

A collection of files that may be of use to ArduPilot Rover users.


### Waypoint File Tool

* Excel Macro enabled workbook that imports waypoint or polygon files generated by Mission Planner software and converts between the two


### .param files

* ArduPilot parameter dumps that may be of interest
* Filenames describe the intent


### test.py

Simple script to change RC channel 8 from Save Waypoint to Relay 3 control with a single mouse click.  Not pretty.  Functional.

### armSwitch.lua

Monitors an RC channel for a threshold PWM value and arms/disarms the flight controller accordingly.  Useful when RC channels are limited - allows "overloading" a channel with an additional arm/disarm function.  I used it on a three position switch for the following functions:
* Position 1: Engine Kill/Disarm
* Position 2: Engine Run/Disarm
* Position 3: Engine Run/Arm

### duskLights.lua

Builds upon solarElevUTC.lua, which should run on any OS-based interpreter.  duskLights.lua is modified to work with Ardupilot's scripting architecture, accounting for its lack of exposed libraries (os.date and os.time are not available).  Uses an iterative approach to calculate date/time from GPS week number and GPS time of week (in milliseconds).  Turns a relay (lights) on when the sun dips below a definable elevation.  Tested on Cube Orange and Mission Planner with success.

### solarElevUTC.lua

Calculates solar elevation at current system time for a given latitude/longitude.  Intent is to use GPS coordinates to derive sun angle and use the information to turn lights on/off approaching dusk/dawn.  Runs on an OS interpreter - not optimized for ArduPilot.

### Notes

Next to-do:
https://github.com/ArduPilot/ardupilot/issues/8788

Per that link, mess with ATC_STR_ACC_MAX (default 180), but be careful not to set too low.

Good reading:
https://discuss.ardupilot.org/t/skid-steer-mower-overshooting-pivot-turns/28910/104

Normal steering and throttle nicely tuned - PID follows well

Pivot turn tuning is close - occasionally under/overshoots slightly and pauses to correct before continuing on path - suspect ATC_STR_ANG_P needs attention

ATC_ACCEL_MAX 0.6-0.7 seems to help smooth starts and possibly helps pivot turns

ATC_DECEL_MAX 1.6 plus ATC_BRAKE 1 is the best discovery yet! Enables significant decel approaching sharp turns and limits overshoots

ATC_STR_RATE_FF 0.3-0.4, ATC_STR_RATE_MAX and WP_PIVOT_RATE 37

ATC_STR_RATE_I 0.9 seems to allow faster update of yaw and fixes some of the s-turn issues

ATC_STR_ANG_P of 1.0 - 1.7 seems appropriate - any more than that overshoots (1.7 set for now)

WP_RADIUS and WP_OVERSHOOT have big effects (0.4 each for now)

WP_SPEED 0 does not use CRUISE_SPEED - it literally stands still in auto mode

NAVL1 parameters now at defaults (I think) - changing them from defaults results in overshoots or slow updates

Disabling GPS_AUTO_CFG confuses EKF3 (never sees GPS config data) - boots faster but seems to hang waiting for complete initialization

GPS_RATE_MS 100.  Seems to make GPS2 quirky, but any other value makes it worse
(Unhealthy GPS Signal warnings still exist, but less frequent with this setting - 50 is too fast and results in rapidly cycling GPS2 solutions, most of which are not RTK corrected)

Using GPS_DRV_OPTIONS 0 is too slow for GPS heading - need to use direct inject with crossover TX/RX from one SimpleRTK board to the other

FENCE and OA seem broken - really bad behavior so far with GPS yaw and this tune
