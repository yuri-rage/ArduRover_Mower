-------------------------------------------------
---- AutoChokeSaveWP ArduPilot Lua script -------
--                                             --
-- Sets choke for cold/warm start by polling   --
-- ignition and starter switch states and      --
-- setting the choke for a cold start, then    --
-- slowly backs the choke off as the engine    --
-- presumably warms up.                        --
--                                             --
-- If the vehicle is armed, the starter switch --
-- becomes a save waypoint switch              --
--                                             --
--------------- Yuri -- Aug 2021 ----------------
-------------------------------------------------

--------    USER EDITABLE GLOBALS  --------
local AUTO               = 10    -- rover auto mode number
local WAYPOINT_COMMAND   = 16    -- normal waypoint command number
local IGNITION_CHANNEL   = 5     -- I used a reversed channel for this
local IGNITION_THRESHOLD = 2000  -- pwm threshold to determine state
local STARTER_RELAY      = 4     -- starter relay channel
local STARTER_CHANNEL    = 7     -- starter trigger channel
local STARTER_THRESHOLD  = 1500  -- pwm threshold to determine state
local CHOKE_SERVO_FN     = 94    -- recommend 94-109 (SERVOx_FUNCTION = Script <1-16>
local CHOKE_MIN          = 982   -- min choke pwm
local CHOKE_MAX          = 1469  -- max choke pwm
local CHOKE_TIMEOUT      = 4500  -- (ms) incrementally decrease choke during this amount of time (after engine start)
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

function autoChoke()
    
    if (coldStart and timer > millis()) then
        local choke_pwm_diff = math.floor((CHOKE_MAX - CHOKE_MIN) * (timer:tofloat() - millis():tofloat()) / CHOKE_TIMEOUT)
        local choke_pwm = CHOKE_MIN + choke_pwm_diff
        SRV_Channels:set_output_pwm(CHOKE_SERVO_FN, choke_pwm)
        return
    end
    
    if (coldStart and crankingComplete) then
        SRV_Channels:set_output_pwm(CHOKE_SERVO_FN, CHOKE_MIN)
        coldStart = false
        crankingComplete = false
        if (VERBOSE_MODE > 0) then gcs:send_text(6, "Cold start complete, choke OFF") end
        return
    end
    
    local ignitionPwm = rc:get_pwm(IGNITION_CHANNEL)
	local starterPwm = rc:get_pwm(STARTER_CHANNEL)
    
	if starterPwm == lastStarterPwm then return end
	lastStarterPwm = starterPwm

	if (starterPwm < STARTER_THRESHOLD and ignitionPwm > IGNITION_THRESHOLD) then
		coldStart = not coldStart

        if (coldStart) then
            SRV_Channels:set_output_pwm(CHOKE_SERVO_FN, CHOKE_MAX)
            crankingComplete = false
            if (VERBOSE_MODE > 0) then gcs:send_text(6, "Cold start, choke ON") end
            return
         end

        SRV_Channels:set_output_pwm(CHOKE_SERVO_FN, CHOKE_MIN)
        if (VERBOSE_MODE > 0) then gcs:send_text(6, "Warm start, choke OFF") end
        return
    end
    
    --if (coldStart and starterPwm < STARTER_THRESHOLD and ignitionPwm < IGNITION_THRESHOLD) then
    if (starterPwm < STARTER_THRESHOLD and ignitionPwm < IGNITION_THRESHOLD) then
        relay:off(STARTER_RELAY)
        cranking = true
        if (VERBOSE_MODE > 1) then gcs:send_text(6, "Cranking engine") end
        return
    end

    if (cranking and starterPwm > STARTER_THRESHOLD and ignitionPwm < IGNITION_THRESHOLD) then
        relay:on(STARTER_RELAY)
        cranking = false
        crankingComplete = true
        if (coldStart) then
            timer = millis() + CHOKE_TIMEOUT
        end
        if (VERBOSE_MODE > 1) then gcs:send_text(6, "Cranking complete") end
        return
    end
end

function waypointSaver()
	local starterPwm = rc:get_pwm(STARTER_CHANNEL)
    
	if starterPwm == lastStarterPwm then return end
	lastStarterPwm = starterPwm

    if (starterPwm < STARTER_THRESHOLD) then
        if (not ahrs:healthy()) then
            if (VERBOSE_MODE > 0) then gcs:send_text(5, "WP not saved, AHRS unhealthy") end
            return
        end
        local location = ahrs:get_position()
        if (location == nil) then
            if (VERBOSE_MODE > 0) then gcs:send_text(5, "WP not saved, location unknown") end
            return
        end
        local template = mission:get_item(0)
        template:command(WAYPOINT_COMMAND)
        template:x(location:lat())
        template:y(location:lng())
        template:z(location:alt())
        mission:set_item(mission:num_commands(), template)
        if (VERBOSE_MODE > 0) then gcs:send_text(6, "Saved Waypoint: " .. mission:num_commands()) end
    end
end

function update()
    if (arming:is_armed() and vehicle:get_mode() ~= AUTO) then
        waypointSaver()
        return update, FREQUENCY
    end
    autoChoke()
    return update, FREQUENCY
end

if (VERBOSE_MODE > 0) then gcs:send_text(6, "AutoChoke: Choke OFF") end

return update()