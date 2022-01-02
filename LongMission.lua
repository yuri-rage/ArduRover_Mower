
--[[----------------------------------------------------------------------------

LongMission ArduPilot Lua script

Executes a waypoint mission from the SD card.  The mission can exceed the
700 waypoint limit set by ArduPilot (limited only by SD card storage).

The default filename is "LongMission.waypoints" (case-sensitive) and should be
placed in the root directory of the SD card.

The script expects an RC channel to be set to RCx_OPTION=300 as written.  The
values 300-307 are valid and can be used provided the RC_OPTION pseudo-constant
below is changed to match the parameter value.

That RC channel should be assigned to a 2 or 3 position switch.  The "high"
position (PWM > ~1700μs) will trigger execution of the mission on the SD card.

CAUTION: This script is capable of engaging and disengaging autonomous control
of a vehicle.  Use this script AT YOUR OWN RISK.

-- Yuri -- Jan 2022

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

Loosely based on the example at: https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_Scripting/examples/mission-load.lua
------------------------------------------------------------------------------]]

---- SETUP "CONSTANTS" YOU MIGHT WANT TO CHANGE --------------------------------
local WP_FILENAME          = 'LongMission.waypoints'  -- filename on SD card
local RC_OPTION            = 300  -- set RCx_OPTION to this value to enable/disable this script
--------------------------------------------------------------------------------

---- SETUP "CONSTANTS" YOU PROBABLY SHOULDN'T CHANGE ---------------------------
local WP_MAX               = 700  -- number of waypoints to load at a time (not more than 700)
local DISABLE              =   0  -- switch position to disable scripted mission loading
local ENABLE               =   2  -- switch position to enable scripted mission loading
local RUN_FREQUENCY        = 500  -- (ms) how often to run this script (500 is probably fine)
local LOAD_FREQUENCY       =  10  -- (ms) faster interval during mission load events
local LINES_PER_ITERATION  =  25  -- number of waypoints to read during each execution time-slice
--------------------------------------------------------------------------------

---- FIXED "CONSTANTS" - DON'T CHANGE THESE ------------------------------------
local MAV_CMD_NAV_WAYPOINT =  16  -- https://mavlink.io/en/messages/common.html#MAV_CMD_NAV_WAYPOINT
local ROVER_MODE_HOLD      =   4  -- https://mavlink.io/en/messages/ardupilotmega.html#ROVER_MODE
local MODE_THRESHOLDS      = {1231,  -- https://github.com/ArduPilot/ardupilot/blob/master/Rover/Parameters.cpp#L177
                             1361,
                             1491,
                             1621,
                             1750,
                             2050}

local MAV_SEVERITY_WARNING   = 4
local MAV_SEVERITY_NOTICE    = 5
local MAV_SEVERITY_INFO      = 6
local MAV_SEVERITY_DEBUG     = 7
--------------------------------------------------------------------------------

local file_posit     = 0
local waypoint_index = 0

local rc_chan = rc:find_channel_for_option(RC_OPTION)
local mode_chan = param:get("MODE_CH")

function get_user_mode(pwm)

    local mode_num = 6

    for i, threshold in pairs(MODE_THRESHOLDS) do
        if (pwm < threshold) then
            mode_num = i
            break
        end
    end

    return tonumber(param:get("MODE" .. mode_num))
end

function set_user_mode(pwm)
    vehicle:set_mode(get_user_mode(pwm))
end

-- the AP Lua implementation appears very susceptible to floating point math errors
-- this function takes a decimal number in string format and returns an integer
-- representation of its value * 10^7 (as in ArduPilot lat/lng arguments)
-- without using any floating point math (takes *much* longer)
-- https://discuss.ardupilot.org/t/overcoming-lua-floating-point-math-precision-errors-latitude-longitude/75710
function strf_to_stri(x)
  local whole, fraction = x:match("(.+)%.(.+)")
  if (fraction == nil) then
    whole = x
    fraction = '00000000'
  end
  if (string.len(fraction) > 8) then
    fraction = fraction:sub(1, 6 - string.len(fraction))
  end
  fraction = fraction .. string.rep('0', 8 - string.len(fraction))
  return whole .. fraction:sub(1, -2)
end

local function create_new_mission()
    local home = ahrs:get_home()
    local item = mavlink_mission_item_int_t()

    mission:clear()

    item:command(MAV_CMD_NAV_WAYPOINT)
    item:x(home:lat())
    item:y(home:lng())
    item:z(home:alt())

    if not mission:set_item(0, item) then
        gcs:send_text(MAV_SEVERITY_WARNING, 'LongMission: Failed to create new mission')
        return false
    end

    return true
end

function read_mission(file_name)
    local file = io.open(file_name, 'r')
    local header = assert(file:read('l'), 'Could not open: ' .. file_name)
    if file_posit > 0 then
        file:seek('set', file_posit)
    else
        assert(string.find(header, 'QGC WPL 110') == 1, file_name .. ': incorrect format')
        assert(mission:clear(), 'Could not clear current mission')
        waypoint_index = 0
        file_posit = string.len(header) + 1
    end
    local item = mavlink_mission_item_int_t()
    local lines_read = 0
    while lines_read <= LINES_PER_ITERATION do
        local data = {}
        local line = file:read('*line')
        if (line == nil) then
            gcs:send_text(MAV_SEVERITY_INFO, string.format('Loaded %d waypoints from %s', waypoint_index - 1, file_name))
            file:close()
            file_posit = 0
            waypoint_index = 0
            return
        end
        for fld in string.gmatch(line, "([^%s]+)") do
            table.insert(data, fld)
        end
        if (tonumber(data[12]) == nil) then
            mission:clear()
            file:close()
            file_posit = 0
            error(string.format('Error reading waypoint %d from %s', waypoint_index, file_name))
        end
        item:seq(data[1])
        item:frame(data[3])
        item:command(data[4])
        item:param1(data[5])
        item:param2(data[6])
        item:param3(data[7])
        item:param4(data[8])
        item:x(strf_to_stri(data[9]))  -- avoids rounding errors in `item:x(data[9]*10^7)`
        item:y(strf_to_stri(data[10]))
        item:z(data[11])
        if not mission:set_item(waypoint_index, item) then
            mission:clear()
            file:close()
            file_posit = 0
            error(string.format('Failed to set mission item %i', waypoint_index))
        end
        waypoint_index = waypoint_index + 1
        file_posit = file_posit + string.len(line) + 1
        lines_read = lines_read + 1
        if (waypoint_index > WP_MAX) then
            gcs:send_text(MAV_SEVERITY_INFO, string.format('Loaded %d waypoints from %s', waypoint_index - 1, file_name))
            file:close()
            waypoint_index = 1
            return
        end
    end
    file:close()
end

function mission_idle()
    if (mission:state() == mission.MISSION_RUNNING) then
        return mission_idle, RUN_FREQUENCY
    end
    local sw_pos = rc_chan:get_aux_switch_pos()
    if (sw_pos == ENABLE) then
        gcs:send_text(MAV_SEVERITY_INFO, 'LongMission: Starting')
        return load_next_mission_segment, LOAD_FREQUENCY
    end
    return mission_idle, RUN_FREQUENCY
end

function load_next_mission_segment()
    local status, err
    vehicle:set_mode(ROVER_MODE_HOLD)
    status, err = pcall(read_mission, WP_FILENAME)
    if (waypoint_index > 1) then
        return load_next_mission_segment, LOAD_FREQUENCY
    end
    if (status) then
        mission:set_current_cmd(1)
        set_user_mode(rc:get_pwm(mode_chan))
        return mission_running, RUN_FREQUENCY
    end
    if (err) then
        gcs:send_text(MAV_SEVERITY_WARNING, string.match(err, "%s([^:]+)$"))
        return mission_abort, RUN_FREQUENCY
    end
    -- function should have returned by now
    gcs:send_text(MAV_SEVERITY_DEBUG, 'LongMission: Unexpected condition during load_next_mission_segment()')
    return mission_abort, RUN_FREQUENCY
end

function mission_running()
    local sw_pos = rc_chan:get_aux_switch_pos()
    if (sw_pos == DISABLE) then
        return mission_abort, RUN_FREQUENCY
    end
    if (mission:state() == mission.MISSION_COMPLETE) then
        if file_posit > 0 then
            create_new_mission()
            return load_next_mission_segment, LOAD_FREQUENCY
        end
        mission:clear()
        gcs:send_text(MAV_SEVERITY_WARNING, 'LongMission: Complete!  Awaiting disable switch...')
        return mission_complete, RUN_FREQUENCY
    end
    return mission_running, RUN_FREQUENCY
end

function mission_abort()
    vehicle:set_mode(ROVER_MODE_HOLD)
    mission:clear()
    file_posit     = 0
    waypoint_index = 0
    gcs:send_text(MAV_SEVERITY_WARNING, 'LongMission: Aborted!')
    return mission_complete, RUN_FREQUENCY
end

function mission_complete()
    local sw_pos = rc_chan:get_aux_switch_pos()
    if (sw_pos == DISABLE) then
        gcs:send_text(MAV_SEVERITY_INFO, 'LongMission: Idle.  Awaiting enable switch...')
        return mission_idle, RUN_FREQUENCY
    end
    return mission_complete, RUN_FREQUENCY
end

-- check if wp file exists
local file = io.open(WP_FILENAME, 'r')
local header = file:read(1)
file:close()
if header ~= nil then
    gcs:send_text(MAV_SEVERITY_INFO, 'LongMission: Idle.  Awating enable switch...')
    return mission_idle, RUN_FREQUENCY
end

gcs:send_text(MAV_SEVERITY_WARNING, string.format('LongMission: Stopped!  %s not found', WP_FILENAME))
