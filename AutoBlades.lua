------------------------------------------------
------- AutoBlades ArduPilot Lua script --------
--                                            --
-- Checks for mission running and enables a   --
-- relay for the duration of the mission.     --
--                                            --
--------------- Yuri -- May 2021 ---------------
------------------------------------------------

--------    USER EDITABLE GLOBALS  --------
local ENABLE_CHANNEL   = 8
local ENABLE_THRESHOLD = 1700  -- pwm threshold to enable relay control
local RELAY            = 2     -- relay to control
local ACTIVE_STATE     = 0     -- 0 for LOW, 1 for HIGH
local FREQUENCY        = 50    -- (ms) how often to run this script (50-100 for fast response to switch actuation)
local GCS_MESSAGE      = "Mower Blades" -- GCS message prefix for relay status updates
local VERBOSE_MODE     = 1     -- 0 to suppress all GCS messages, 1 for relay status only, 2 for additional debug messages
-------- END USER EDITABLE GLOBALS --------

--------    "CONSTANTS"   --------
local ROVER_MODE_HOLD   = 4
local ROVER_MODE_AUTO   = 10
-------- END "CONSTANTS"  --------

local relayState  = -1
local lastPwm = rc:get_pwm(ENABLE_CHANNEL)
local lastMode = vehicle:get_mode()
local lastArmState = arming:is_armed()
local lastMsnState = mission:state()
local requireSwitchRecycle = false
local enabled = false

if (lastPwm > ENABLE_THRESHOLD) then
    requireSwitchRecycle = true  -- safeguard against starting blades during boot sequence
end

if (VERBOSE_MODE > 1) then gcs:send_text(5, "AutoBlades: Script active") end

function SetRelay(relayNum, newState)
	if (relayState == newState) then return end
	if (newState == 1) then
		relay:on(relayNum)
	else
		relay:off(relayNum)
	end
	relayState = newState
	if (VERBOSE_MODE < 1) then return end
	if (relayState == ACTIVE_STATE) then
		gcs:send_text(4, GCS_MESSAGE .. ": ON")
	else
		gcs:send_text(4, GCS_MESSAGE .. ": OFF")
	end
end

function update()
	local pwm = rc:get_pwm(ENABLE_CHANNEL)
    local mode = vehicle:get_mode()
    local armState = arming:is_armed()
    local msnState = mission:state()
    local navIndex = mission:get_current_nav_index()
    
    local somethingChanged = false
    
    if (pwm ~= lastPwm) then
        lastPwm = pwm
        somethingChanged = true
    end
    
    if (mode ~- lastMode) then
        lastMode = mode
        somethingChanged = true
    end
    
    if (armState ~= lastArmState) then
        lastArmState = armState
        somethingChanged = true
    end
    
    if (msnState ~= lastMsnState) then
        lastMsnState = msnState
        somethingChanged = true
    end
    
    if (not somethingChanged) then return update, FREQUENCY end  -- early return
    
    if (pwm < ENABLE_THRESHOLD) then
        enabled = true
    else
        enabled = false
    end
    
    if (not enabled) then
        SetRelay(RELAY, ACTIVE_STATE ~ 1)
        requireSwitchRecycle = false
        return update, FREQUENCY
    end
    
    if (not armState) then
        SetRelay(RELAY, ACTIVE_STATE ~ 1)
        requireSwitchRecycle = true
        return update, FREQUENCY
    end
    
    if (mode == ROVER_MODE_HOLD) then
        SetRelay(RELAY, ACTIVE_STATE ~ 1)
        requireSwitchRecycle = true
        return update, FREQUENCY
    end
    
    if (mode == ROVER_MODE_AUTO and msnState ~= mission.MISSION_RUNNING) then
        SetRelay(RELAY, ACTIVE_STATE ~ 1)
        requireSwitchRecycle = true
        return update, FREQUENCY
    end
    
    if (mode == ROVER_MODE_AUTO and enabled and navIndex > 1) then
        SetRelay(RELAY, ACTIVE_STATE)
        return update, FREQUENCY
    end
    
    if (mode ~= ROVER_MODE_AUTO and enabled and not requireSwitchRecycle) then
        SetRelay(RELAY, ACTIVE_STATE)
        return update, FREQUENCY
    end

	return update, FREQUENCY  -- this should be redundant and unnecessary
end

return update()
