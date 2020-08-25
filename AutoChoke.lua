------------------------------------------------
------- AutoChoke ArduPilot Lua script ---------
--                                            --
-- Sets choke for cold/warm start by polling  --
-- ignition and starter switch states and     --
-- setting the choke for a cold start, then   --
-- slowly backs the choke off as the engine   --
-- presumably warms up.                       --
--                                            --
--------------- Yuri -- Aug 2020 ---------------
------------------------------------------------

--------    USER EDITABLE GLOBALS  --------
local IGNITION_CHANNEL   = 5     -- I used a reversed channel for this
local IGNITION_THRESHOLD = 2000  -- pwm threshold to determine state
local STARTER_CHANNEL    = 7     -- starter trigger channel
local STARTER_THRESHOLD  = 1500  -- pwm threshold to determine state
local CHOKE_SERVO_FN     = 94    -- recommend 94-109 (SERVOx_FUNCTION = Script <1-16>
local CHOKE_MIN          = 982   -- min choke pwm
local CHOKE_MAX          = 1400  -- max choke pwm
local CHOKE_TIMEOUT      = 3500  -- (ms) incrementally decrease choke during this amount of time (after engine start)
local FREQUENCY          = 50    -- (ms) how often to run this script (100 or maybe a bit less)
local VERBOSE_MODE       = 1     -- 0 to suppress all GCS messages, 1 for status updates, 2 for additional debug messages
-------- END USER EDITABLE GLOBALS --------

local lastStarterPwm  = rc:get_pwm(STARTER_CHANNEL)
local coldStart = false
local cranking = false
local crankingComplete = false
local timer = 0

-- initialize with choke off
SRV_Channels:set_output_pwm(CHOKE_SERVO_FN, CHOKE_MIN)

function update()
    
    if (coldStart and timer > millis()) then
        local choke_pwm_diff = math.floor((CHOKE_MAX - CHOKE_MIN) * (timer:tofloat() - millis():tofloat()) / CHOKE_TIMEOUT)
        local choke_pwm = CHOKE_MIN + choke_pwm_diff
        SRV_Channels:set_output_pwm(CHOKE_SERVO_FN, choke_pwm)
    elseif (coldStart and crankingComplete) then
        SRV_Channels:set_output_pwm(CHOKE_SERVO_FN, CHOKE_MIN)
        coldStart = false
        crankingComplete = false
        if (VERBOSE_MODE > 0) then gcs:send_text(5, "Cold start complete, choke OFF") end
    end
    
    local ignitionPwm = rc:get_pwm(IGNITION_CHANNEL)
	local starterPwm = rc:get_pwm(STARTER_CHANNEL)
    
	if starterPwm == lastStarterPwm then return update, FREQUENCY end
	lastStarterPwm = starterPwm

	if (starterPwm < STARTER_THRESHOLD and ignitionPwm > IGNITION_THRESHOLD) then
		coldStart = not coldStart
        if (coldStart and VERBOSE_MODE > 0) then
            SRV_Channels:set_output_pwm(CHOKE_SERVO_FN, CHOKE_MAX)
            crankingComplete = false
            if (VERBOSE_MODE > 0) then gcs:send_text(5, "Cold start, choke ON") end
         else
            SRV_Channels:set_output_pwm(CHOKE_SERVO_FN, CHOKE_MIN)
            if (VERBOSE_MODE > 0) then gcs:send_text(5, "Warm start, choke OFF") end
         end
         return update, FREQUENCY
    end
    
                      -- not cranking may be redundant here
    if (coldStart and not cranking and starterPwm < STARTER_THRESHOLD and ignitionPwm < IGNITION_THRESHOLD) then
        cranking = true
        if (VERBOSE_MODE > 1) then gcs:send_text(5, "Cold start, cranking engine") end
        return update, FREQUENCY
    end
    
    if (cranking and starterPwm > STARTER_THRESHOLD and ignitionPwm < IGNITION_THRESHOLD) then
        cranking = false
        crankingComplete = true
        timer = millis() + CHOKE_TIMEOUT
        if (VERBOSE_MODE > 1) then gcs:send_text(5, "Cold start, cranking complete") end
        return update, FREQUENCY
    end

    return update, FREQUENCY
end

if (VERBOSE_MODE > 0) then gcs:send_text(5, "Automatic Choke Ready, choke OFF") end

return update()