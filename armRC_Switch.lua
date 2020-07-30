------------------------------------------------
------ armRC_Switch ArduPilot Lua script -------
--                                            --
-- Arms and disarms the flight controller     --
-- based on RC channel( switch) changes.      --
-- Useful to "overload" a channel for two     --
-- functions, (i.e., ignition and arming).    --
--                                            --
--------------- Yuri -- July 2020 ---------------
-------------------------------------------------

--------    USER EDITABLE GLOBALS  --------
local SWITCH_CHANNEL = 5     -- I used a reversed channel for this
local THRESHOLD      = 1700  -- pwm threshold to arm/disarm
local FREQUENCY      = 100   -- (ms) how often to run this script (100 to 250 works well)
-------- END USER EDITABLE GLOBALS --------

local lastPwm = rc:get_pwm(SWITCH_CHANNEL)
gcs:send_text(0, "armRC_Switch: Script active")
function update()
	local pwm = rc:get_pwm(SWITCH_CHANNEL)
	if pwm == lastPwm then return update, FREQUENCY end
	lastPwm = pwm
	local armed = arming:is_armed()
	if (pwm < THRESHOLD and not armed) then
		arming:arm()
	elseif (pwm > THRESHOLD and armed) then
		arming:disarm()
	end
	return update, FREQUENCY
end
return update()
