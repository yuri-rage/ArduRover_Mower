------------------------------------------------------------
-------- ArmSwitchParkingBrake ArduPilot Lua script --------
--                                                        --
-- Arms and disarms the flight controller based on        --
-- RC channel (switch) changes.  Additionally, sets the   --
-- parking brake when HOLD mode is selected.              --
--                                                        --
-- Useful to "overload" a channel for two functions,      --
-- (i.e., ignition and arming), and similarly avoid using --
-- an RC channel for the parking brake.                   --
--                                                        --
--------------------- Yuri -- Aug 2020 ---------------------
------------------------------------------------------------

--------    USER EDITABLE GLOBALS  --------
local ARM_CHANNEL    = 5     -- I used a reversed channel for this
local THRESHOLD      = 1700  -- pwm threshold to arm/disarm
local BRAKE_SERVO_FN = 95
local BRAKE_OFF      = 1000
local BRAKE_ON       = 2045
local HOLD_MODE      = 4
local FREQUENCY      = 100   -- (ms) how often to run this script (100 to 250 works well)
local VERBOSE_MODE   = 1     -- 0 to suppress all GCS messages, 1 for status updates, 2 for additional debug messages
-------- END USER EDITABLE GLOBALS --------

if (VERBOSE_MODE > 0) then gcs:send_text(6, "Welcome to Maximum Roverdrive") end

local lastPwm = rc:get_pwm(ARM_CHANNEL)
local lastMode = vehicle:get_mode()

function update()
	local pwm = rc:get_pwm(ARM_CHANNEL)
    local mode = vehicle:get_mode()
	if (pwm == lastPwm and mode == lastMode) then return update, FREQUENCY end

    if (pwm ~= lastPwm) then
        lastPwm = pwm
        local armed = arming:is_armed()
        if (pwm < THRESHOLD and not armed) then
            arming:arm()
            if (not ahrs:healthy() and VERBOSE_MODE > 0) then
                gcs:send_text(4, "Armed when not fully aligned!")
            elseif (VERBOSE_MODE > 0) then
                gcs:send_text(6, "Maximum Roverdrive...let's roll!")
            end
        elseif (pwm > THRESHOLD and armed) then
            arming:disarm()
        end
    end
    
    if (mode ~= lastMode) then
        lastMode = mode
        if (mode == HOLD_MODE) then
            SRV_Channels:set_output_pwm(BRAKE_SERVO_FN, BRAKE_ON)
            if (VERBOSE_MODE > 0) then gcs:send_text(6, "Parking brake: ON") end
        else
            SRV_Channels:set_output_pwm(BRAKE_SERVO_FN, BRAKE_OFF)
            if (VERBOSE_MODE > 0) then gcs:send_text(6, "Parking brake: OFF") end
        end
    end
    
    return update, FREQUENCY
end

return update()
