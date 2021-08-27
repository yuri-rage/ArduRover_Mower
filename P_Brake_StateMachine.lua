------------------------------------------------------------
-------- P_Brake_StateMachine ArduPilot Lua script ---------
--                                                        --
-- Sets a parking brake servo based on arm/disarm and     --
-- flight mode states.                                    --
--                                                        --
--------------------- Yuri -- Aug 2021 ---------------------
------------------------------------------------------------

--------    USER EDITABLE GLOBALS  --------
local BRAKE_SERVO_FN = 95
local BRAKE_OFF_PWM  = 1000
local BRAKE_ON_PWM   = 2045
local ENGAGE_TIMEOUT = 2000  -- (ms) how long to wait before engaging parking brake
local FREQUENCY      = 250   -- (ms) how often to run this script (100 to 250 works well)
local VERBOSE_MODE   = 2     -- 0 to suppress all GCS messages, 1 for status updates, 2 for additional debug messages
-------- END USER EDITABLE GLOBALS --------

--------    "CONSTANTS"   --------
local ROVER_MODE_HOLD = 4
-------- END "CONSTANTS"  --------

function brake_off()
    if not arming:is_armed() then
        return brake_engage, ENGAGE_TIMEOUT
    end
  
    if vehicle:get_mode() == ROVER_MODE_HOLD then
        return brake_engage, ENGAGE_TIMEOUT
    end
    
    return brake_off, FREQUENCY
end

function brake_on()
    if arming:is_armed() and vehicle:get_mode() ~= ROVER_MODE_HOLD then
        return brake_disengage, 0
    end
    
    return brake_on, FREQUENCY
end

function brake_engage()
    if not arming:is_armed() then
        SRV_Channels:set_output_pwm(BRAKE_SERVO_FN, BRAKE_ON_PWM)
        if (VERBOSE_MODE > 0) then gcs:send_text(4, "Parking Brake: On") end
        return brake_on, FREQUENCY
    end
  
    if vehicle:get_mode() == ROVER_MODE_HOLD then
        SRV_Channels:set_output_pwm(BRAKE_SERVO_FN, BRAKE_ON_PWM)
        if (VERBOSE_MODE > 0) then gcs:send_text(4, "Parking Brake: On") end
        return brake_on, FREQUENCY
    end
    
    return brake_off, FREQUENCY
end

function brake_disengage()
    if arming:is_armed() and vehicle:get_mode() ~= ROVER_MODE_HOLD then
        SRV_Channels:set_output_pwm(BRAKE_SERVO_FN, BRAKE_OFF_PWM)
        if (VERBOSE_MODE > 0) then gcs:send_text(4, "Parking Brake: Off") end
        return brake_off, FREQUENCY
    end
    
    return brake_on, FREQUENCY
end

if (VERBOSE_MODE > 1) then gcs:send_text(6, "Parking Brake State Machine: Active") end

return brake_off, FREQUENCY
