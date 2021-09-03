--[[----------------------------------------------------------------------------

MinFixType ArduPilot Lua script

Checks for mission running and commands a hold/pause if the GPS fix type is less
than a threshold value.

CAUTION: This script is capable of engaging and disengaging autonomous control
of a vehicle.  Use this script AT YOUR OWN RISK.

-- Yuri -- Aug 2021

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
------------------------------------------------------------------------------]]

-------- MODE "CONSTANTS"   --------
local ROVER_MODE_MANUAL    =  0
local ROVER_MODE_HOLD      =  4
local ROVER_MODE_AUTO      = 10
-- local ROVER_MODE_ACRO      =  1
-- local ROVER_MODE_STEERING  =  3
-- local ROVER_MODE_LOITER    =  5
-- local ROVER_MODE_FOLLOW    =  6
-- local ROVER_MODE_SIMPLE    =  7
-- local ROVER_MODE_RTL       = 11
-- local ROVER_MODE_SMART_RTL = 12
-- local ROVER_MODE_GUIDED    = 15
------- END MODE "CONSTANTS"  -------

--------    USER EDITABLE GLOBALS  --------
local GPS_INSTANCE = 0                 -- GPS to monitor (moving base, most likely)
local MIN_FIX_TYPE = 6                 -- 3 is is 3d Fix, 4 is DGPS, 5 is RTK Float, 6 is RTK Fixed
local PAUSE_MODE   = ROVER_MODE_MANUAL -- mode to command when GPS fix is inadequate
local BAD_FIX_TIMEOUT  = 1600          -- how long a bad fix type must be present before pausing the mission
local GOOD_FIX_TIMEOUT =  600          -- how long a good fix type must be present before resuming the mission
local FREQUENCY    = 200               -- (ms) how often to run this script (50-250 should work fine)
local VERBOSE_MODE = 2                 -- 0 to suppress all GCS messages, 1 for pause status only, 2 for additional GPS/debug messages
-------- END USER EDITABLE GLOBALS --------

local FIX_TYPES = {
    [0] = "No GPS",  -- Lua arrays are 1 based unless you specify discrete indices like this
    [1] = "No Fix",
    [2] = "2D Fix",
    [3] = "3D Fix",
    [4] = "DGPS Fix",
    [5] = "RTK Float",
    [6] = "RTK Fixed",
    [7] = "Static Fixed",
    [8] = "PPP, 3D"}

local mode_channel = param:get("MODE_CH")
local paused = false
local pause_time = 0
local resume_time = 0

function get_user_mode(pwm)
    local mode_threshholds = {1231, 1361, 1491, 1621, 1750, 2050}

    local mode_num = 6

    for i, threshold in pairs(mode_threshholds) do
        if (pwm < threshold) then
            mode_num = i
            break
        end
    end

    return tonumber(param:get("MODE" .. mode_num))
end

function handle_pause_condition(now, f_type)
    if (pause_time == 0) then
        pause_time = now + BAD_FIX_TIMEOUT
        if (VERBOSE_MODE > 1) then gcs:send_text(4, "GPS " .. (GPS_INSTANCE + 1) .. ": " .. FIX_TYPES[f_type]) end
        return
    end

    if (now > pause_time) then
        vehicle:set_mode(PAUSE_MODE)
        paused = true
        resume_time = 0
        if (VERBOSE_MODE > 0) then gcs:send_text(4, "Mission Paused: " .. FIX_TYPES[f_type]) end
    end
end

function handle_resume_condition(now, f_type)
    if (resume_time == 0) then
        resume_time = now + GOOD_FIX_TIMEOUT
        if (VERBOSE_MODE > 1) then gcs:send_text(4, "GPS " .. (GPS_INSTANCE + 1) .. ": " .. FIX_TYPES[f_type]) end
        return
    end

    if (now > resume_time) then
        vehicle:set_mode(ROVER_MODE_AUTO)
        paused = false
        pause_time = 0
        if (VERBOSE_MODE > 0) then gcs:send_text(4, "Mission Resumed") end
    end
end

function update()
    if (not arming:is_armed()) then
        local paused = false
        local pause_time = 0
        local resume_time = 0
        return update, FREQUENCY
    end  -- disarmed, reset and return

    local mode = vehicle:get_mode()

    if (mode ~= ROVER_MODE_AUTO and mode ~= PAUSE_MODE) then
        local paused = false
        local pause_time = 0
        local resume_time = 0
        return update, FREQUENCY    
    end  -- vehicle is in a state not controlled by this script, reset and return

    local user_mode = get_user_mode(rc:get_pwm(mode_channel))
    local fix_type = gps:status(GPS_INSTANCE)
    local time_now = millis()

    if (not paused
        and mode == ROVER_MODE_AUTO
        and mission:state() == mission.MISSION_RUNNING
        and fix_type < MIN_FIX_TYPE) then

        handle_pause_condition(time_now, fix_type)
        return update, FREQUENCY
    end

    if (paused
        and mode == PAUSE_MODE
        and fix_type >= MIN_FIX_TYPE) then

        handle_resume_condition(time_now, fix_type)
        return update, FREQUENCY
    end

    if (paused
        and resume_time > 0
        and fix_type < MIN_FIX_TYPE) then  -- fix went from good to bad before GOOD_FIX_TIMEOUT
        resume_time = 0
    end

    if (paused
        and user_mode ~= ROVER_MODE_AUTO) then  -- mission was paused and user commanded a mode change
        paused = false
        pause_time = 0
        resume_time = 0
        if (VERBOSE_MODE > 0) then gcs:send_text(4, "Pause Canceled, Mode Change") end
    end

    if (not paused
        and pause_time > 0
        and fix_type >= MIN_FIX_TYPE) then  -- fix went from bad to good before BAD_FIX_TIMEOUT
        pause_time = 0
        if (VERBOSE_MODE > 1) then gcs:send_text(4, "GPS " .. (GPS_INSTANCE + 1) .. ": " .. FIX_TYPES[fix_type]) end
    end

	return update, FREQUENCY
end

if (VERBOSE_MODE > 1) then gcs:send_text(5, "Loaded Lua Script: MinFixType") end

return update()
