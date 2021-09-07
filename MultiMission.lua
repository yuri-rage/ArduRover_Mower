
--[[----------------------------------------------------------------------------

MultiMission ArduPilot Lua script

Checks for AUTO mode commanded with no mission loaded ("flight mode change failed").
If that condition exists, load and execute missions in sequence from the SD card,
starting with "0.waypoints."

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

Loosely based on the example at: https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_Scripting/examples/mission-load.lua
------------------------------------------------------------------------------]]

local LINES_PER_ITERATION =  25  -- number of waypoints to read during each execution time-slice
local FREQUENCY           = 500  -- (ms) how often to run this script (500 seems to work well)

local ROVER_MODE_MANUAL   =   0
local ROVER_MODE_HOLD     =   4
local ROVER_MODE_AUTO     =  10
local IGNORE_MODE         = ROVER_MODE_MANUAL  -- do not abort on changes to this mode
--local ROVER_MODE_LOITER   =   5

local filename_index = 0
local file_count
local file_position = 0
local waypoint_index = 0

local mode_channel = param:get("MODE_CH")

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

function get_file_count()
    local count = 0
    repeat
        local file = io.open(count .. '.waypoints', 'r')
        local header = file:read(1)
        file:close()
        count = count + 1
    until header == nil
    return count - 1
end

-- the AP Lua implementation appears very susceptible to floating point math errors
-- this function takes a decimal number in string format and returns an integer
-- representation of its value * 10^7 (as in ArduPilot lat/lng arguments)
-- without using any floating point math (takes *much* longer)
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

function read_mission(file_name)
    local file = io.open(file_name, 'r')
    local header = assert(file:read('l'), 'Could not open: ' .. file_name)
    if file_position > 0 then
        file:seek('set', file_position)
    else
        assert(string.find(header, 'QGC WPL 110') == 1, file_name .. ': incorrect format')
        assert(mission:clear(), 'Could not clear current mission')
        waypoint_index = 0
        file_position = string.len(header) + 1
    end
    local item = mavlink_mission_item_int_t()
    local lines_read = 0
    while lines_read <= LINES_PER_ITERATION do
        local data = {}
        local line = file:read('*line')
        if (line == nil) then
            gcs:send_text(6, string.format('Loaded %d waypoints from %s', waypoint_index - 1, file_name))
            file:close()
            file_position = 0
            return
        end
        for fld in string.gmatch(line, "([^%s]+)") do
            table.insert(data, fld)
        end
        if (tonumber(data[12]) == nil) then
            mission:clear()
            file:close()
            file_position = 0
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
            file_position = 0
            error(string.format('Failed to set mission item %i', waypoint_index))
        end
        waypoint_index = waypoint_index + 1
        file_position = file_position + string.len(line) + 1
        lines_read = lines_read + 1
    end
    file:close()
end

function idle()
    if (mission:state() == mission.MISSION_RUNNING) then
        return idle, FREQUENCY
    end
    local user_mode = get_user_mode(rc:get_pwm(mode_channel))
    if (user_mode == ROVER_MODE_AUTO and mission:num_commands() <= 1) then
        -- "flight mode change failed" detected
        filename_index = 0
        gcs:send_text(6, 'MultiMission: Starting')
        return load_next_mission, FREQUENCY
    end
    return idle, FREQUENCY
end

function load_next_mission()
    local status, err
    vehicle:set_mode(ROVER_MODE_HOLD)
    if (filename_index < file_count) then
        status, err = pcall(read_mission, filename_index .. '.waypoints')
    end
    if (file_position > 0) then
        return load_next_mission, FREQUENCY
    end
    if (status) then
        mission:set_current_cmd(1)
        vehicle:set_mode(ROVER_MODE_AUTO)
        return running, FREQUENCY
    end
    if (err) then
        gcs:send_text(4, string.match(err, "%s([^:]+)$"))
        return abort, FREQUENCY
    end
    gcs:send_text(6, 'MultiMission: Complete, awaiting mode change')
    return mission_complete, FREQUENCY
end

function running()
    local state = mission:state()
    local mode = vehicle:get_mode()
    if (not arming:is_armed() or (mode ~= ROVER_MODE_AUTO and mode ~= IGNORE_MODE)) then
        return abort, FREQUENCY
    end
    if (state == mission.MISSION_COMPLETE and mode == ROVER_MODE_AUTO) then
        filename_index = filename_index + 1
        return load_next_mission, FREQUENCY
    end
    return running, FREQUENCY
end

function abort()
    mission:clear()
    gcs:send_text(4, 'MultiMission: Aborted')
    return mission_complete, FREQUENCY
end

function mission_complete()
    local user_mode = get_user_mode(rc:get_pwm(mode_channel))
    if (user_mode == ROVER_MODE_AUTO) then
        return mission_complete, FREQUENCY
    end
    mission:clear()
    gcs:send_text(6, 'MultiMission: Idle')
    return idle, FREQUENCY
end

file_count = get_file_count()

if (file_count > 0) then
    gcs:send_text(6, string.format('MultiMission: Ready, %i files found', file_count))
    return idle, FREQUENCY
end

gcs:send_text(4, 'MultiMission: Stopped, no files found')