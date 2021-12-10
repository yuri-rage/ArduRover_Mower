--[[----------------------------------------------------------------------------

ModeMixer ArduPilot Lua script

Polls the switch positions of two three-position RC switch channels and mixes
them to achieve up to 9 discrete flight modes.  Intended for use when
trnasmitter mixing is not available (as in DJI or HereLink hardware).

To modify for your own use, comment/uncomment the relevant sections of the
MODES table for your vehicle type and use the strings from that table to
populate the MODE_MAP table, corresponding to desired switch positions.

CAUTION: This script is capable of engaging and disengaging autonomous control
of a vehicle.  Use this script AT YOUR OWN RISK.

Relevant forum disucssion: https://discuss.ardupilot.org/t/my-1st-script-is-it-ok/79311

-- Yuri -- Dec 2021

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

----- USER CONFIGURABLE 'CONSTANTS' --------------------------------------------
local RC1_OPTION   = 300 -- RCx_OPTION in vehicle parameters
local RC2_OPTION   = 301 -- RCy_OPTION in vehicle parameters
local FREQUENCY    = 200 -- (ms) how often to run this script
local VERBOSE_MODE =   1 -- set 0 to inhibit GCS status messages
--------------------------------------------------------------------------------

local SCR_LABEL    = 'ModeMixer: '
local LOW  = 0
local MID  = 1
local HIGH = 2

local MODES = {
    ['VEHICLE_MODE_UNASSIGNED']  = -1,
    --https://mavlink.io/en/messages/ardupilotmega.html#PLANE_MODE
    ['PLANE_MODE_MANUAL']        =  0,
    ['PLANE_MODE_CIRCLE']        =  1,
    ['PLANE_MODE_STABILIZE']     =  2,
    ['PLANE_MODE_TRAINING']      =  3,
    ['PLANE_MODE_ACRO']          =  4,
    ['PLANE_MODE_FLY_BY_WIRE_A'] =  5,
    ['PLANE_MODE_FLY_BY_WIRE_B'] =  6,
    ['PLANE_MODE_CRUISE']        =  7,
    ['PLANE_MODE_AUTOTUNE']      =  8,
    ['PLANE_MODE_AUTO']          = 10,
    ['PLANE_MODE_RTL']           = 11,
    ['PLANE_MODE_LOITER']        = 12,
    ['PLANE_MODE_TAKEOFF']       = 13,
    ['PLANE_MODE_AVOID_ADSB']    = 14,
    ['PLANE_MODE_GUIDED']        = 15,
    ['PLANE_MODE_INITIALIZING']  = 16,
    ['PLANE_MODE_QSTABILIZE']    = 17,
    ['PLANE_MODE_QHOVER']        = 18,
    ['PLANE_MODE_QLOITER']       = 19,
    ['PLANE_MODE_QLAND']         = 20,
    ['PLANE_MODE_QRTL']          = 21,
    ['PLANE_MODE_QAUTOTUNE']     = 22,
    ['PLANE_MODE_QACRO']         = 23,
    ['PLANE_MODE_THERMAL']       = 24,
    --[[ -- uncomment the relevant section for the vehicle in use
    --https://mavlink.io/en/messages/ardupilotmega.html#COPTER_MODE
    ['COPTER_MODE_STABILIZE']    =  0,
    ['COPTER_MODE_ACRO']         =  1,
    ['COPTER_MODE_ALT_HOLD']     =  2,
    ['COPTER_MODE_AUTO']         =  3,
    ['COPTER_MODE_GUIDED']       =  4,
    ['COPTER_MODE_LOITER']       =  5,
    ['COPTER_MODE_RTL']          =  6,
    ['COPTER_MODE_CIRCLE']       =  7,
    ['COPTER_MODE_LAND']         =  9,
    ['COPTER_MODE_DRIFT']        = 11,
    ['COPTER_MODE_SPORT']        = 13,
    ['COPTER_MODE_FLIP']         = 14,
    ['COPTER_MODE_AUTOTUNE']     = 15,
    ['COPTER_MODE_POSHOLD']      = 16,
    ['COPTER_MODE_BRAKE']        = 17,
    ['COPTER_MODE_THROW']        = 18,
    ['COPTER_MODE_AVOID_ADSB']   = 19,
    ['COPTER_MODE_GUIDED_NOGPS'] = 20,
    ['COPTER_MODE_SMART_RTL']    = 21,
    ['COPTER_MODE_FLOWHOLD']     = 22,
    ['COPTER_MODE_FOLLOW']       = 23,
    ['COPTER_MODE_ZIGZAG']       = 24,
    ['COPTER_MODE_SYSTEMID']     = 25,
    ['COPTER_MODE_AUTOROTATE']   = 26,
    ['COPTER_MODE_AUTO_RTL']     = 27,
    --https://mavlink.io/en/messages/ardupilotmega.html#SUB_MODE
    ['SUB_MODE_STABILIZE'] =  0,
    ['SUB_MODE_ACRO']      =  1,
    ['SUB_MODE_ALT_HOLD']  =  2,
    ['SUB_MODE_AUTO']      =  3,
    ['SUB_MODE_GUIDED']    =  4,
    ['SUB_MODE_CIRCLE']    =  7,
    ['SUB_MODE_SURFACE']   =  9,
    ['SUB_MODE_POSHOLD']   = 16,
    ['SUB_MODE_MANUAL']    = 19,
    --https://mavlink.io/en/messages/ardupilotmega.html#ROVER_MODE
    ['ROVER_MODE_MANUAL']       =  0,
    ['ROVER_MODE_ACRO']         =  1,
    ['ROVER_MODE_STEERING']     =  3,
    ['ROVER_MODE_HOLD']         =  4,
    ['ROVER_MODE_LOITER']       =  5,
    ['ROVER_MODE_FOLLOW']       =  6,
    ['ROVER_MODE_SIMPLE']       =  7,
    ['ROVER_MODE_AUTO']         = 10,
    ['ROVER_MODE_RTL']          = 11,
    ['ROVER_MODE_SMART_RTL']    = 12,
    ['ROVER_MODE_GUIDED']       = 15,
    ['ROVER_MODE_INITIALIZING'] = 16,
    --https://mavlink.io/en/messages/ardupilotmega.html#TRACKER_MODE
    ['TRACKER_MODE_MANUAL']       =  0,
    ['TRACKER_MODE_STOP']         =  1,
    ['TRACKER_MODE_SCAN']         =  2,
    ['TRACKER_MODE_SERVO_TEST']   =  3,
    ['TRACKER_MODE_AUTO']         = 10,
    ['TRACKER_MODE_INITIALIZING'] = 16
    ]]--
}

-- edit the following map with strings from the above MODES table
local MODE_MAP = {
    [LOW] = { -- first switch position
        [LOW]  = 'PLANE_MODE_MANUAL', -- second switch position
        [MID]  = 'PLANE_MODE_STABILIZE',
        [HIGH] = 'PLANE_MODE_AUTO'
    },
    [MID] = {
        [LOW]  = 'PLANE_MODE_FLY_BY_WIRE_A',
        [MID]  = 'PLANE_MODE_AUTOTUNE',
        [HIGH] = 'PLANE_MODE_LOITER'
    },
    [HIGH] = {
        [LOW]  = 'VEHICLE_MODE_UNASSIGNED',
        [MID]  = 'VEHICLE_MODE_UNASSIGNED',
        [HIGH] = 'PLANE_MODE_RTL'
    }
}

local aux_sw_1 = rc:find_channel_for_option(RC1_OPTION)
local aux_sw_2 = rc:find_channel_for_option(RC2_OPTION)

local last_sw1_pos = -1
local last_sw2_pos = -1

local function send_status_msg(severity, txt)
    if VERBOSE_MODE > 0 then gcs:send_text(severity, SCR_LABEL .. txt) end
end

local function set_vehicle_mode(mode_label)
    local mode_value = MODES[mode_label]
    local pretty_label = string.sub(mode_label,
                         string.find(mode_label, 'MODE') + 5)

    if mode_value < 0 then
        send_status_msg(5, pretty_label)
        return
    end

    if vehicle:get_mode() ~= mode_value then
        send_status_msg(5, 'Switching to ' .. pretty_label)
        vehicle:set_mode(mode_value)
    end
end

function update()
    local sw1_pos = aux_sw_1:get_aux_switch_pos()
    local sw2_pos = aux_sw_2:get_aux_switch_pos()

    if sw1_pos == last_sw1_pos and sw2_pos == last_sw2_pos then
        return update, FREQUENCY
    end

    set_vehicle_mode(MODE_MAP[sw1_pos][sw2_pos])
    last_sw1_pos = sw1_pos
    last_sw2_pos = sw2_pos

    return update, FREQUENCY
end

send_status_msg(5, 'Script active')

return update()
