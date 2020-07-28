------------------------------------------------
------- duskLights ArduPilot Lua script --------
--                                            --
-- Uses solar elevation from GPS position and --
-- time to activate a relay (lights) when the --
-- sun dips below a given elevation value.    --
--                                            --
--------------- Yuri -- July 2020 ---------------
-------------------------------------------------

--------    USER EDITABLE GLOBALS  --------
LIGHT_RELAY    = 3    -- relay that controls lights
ON_STATE       = 0    -- 0 for LOW, 1 for HIGH
DUSK_ELEVATION = 6    -- (degrees) solar elevation below which to activate the relay (recommend 6-9)
FREQUENCY      = 60    -- (seconds) how often to check solar elevation (recommend 300, which is 5 minutes)
VERBOSE_MODE   = 2    -- 0 to suppress all GCS messages, 1 for light status only, 2 for additional solar data messages
-------- END USER EDITABLE GLOBALS --------

-- relay:enabled(relay) does not work as advartised
-- it appears to return true if the RELAYx_OPTION is greater than -1
-- in current firmware, it doesn't appear possible to poll relay state
-- so best we can do for now is store the last script commanded state
-- TODO: if this is ever fixed in firmware, poll actual relay state
CURRENT_STATE  = -1

if (VERBOSE_MODE > 0) then gcs:send_text(0, "duskLights: Script active") end

function setRelay(relayNum, newState)
	
	if (CURRENT_STATE) == newState then return end
	
	if (newState == 1) then
		relay:on(relayNum)
	else
		relay:off(relayNum)
	end
	
	CURRENT_STATE = newState
	
	if (VERBOSE_MODE < 1) then return end
	
	if (CURRENT_STATE == ON_STATE) then
		gcs:send_text(0, "duskLights: LIGHTS ON")
	else
		gcs:send_text(0, "duskLights: LIGHTS OFF")
	end
end

function IsLeapYear(y)
	if ((y % 4 == 0 and y % 100 ~= 0) or y % 400 == 0) then
		return true
	else
		return false
	end
end

-- iteratively calculate year, Julian day, and UTC time from GPS week number and time of week in milliseconds
-- this would be much easier if os.date and os.time were exposed to ArduPilot's lua interpreter
function GetGPSDate()
	gpsWeek = gps:time_week(0)
	gpsTime = tonumber(tostring(gps:time_week_ms(0))) -- tonumber/tostring coerces number from userdata type
	
	-- GPS epoch occurred on 6 Jan 1980
	year = 1980
	dayNumber = gpsWeek * 7 + 6
	
	-- first attempt at this was iterating over every day since the GPS epoch
	-- it worked in theory, but the loop timed out when ArduPilot's interpreter ran it
	-- far more efficient to only iterate over the years (and there's likely a better way, still...)
	while (dayNumber > 365) do
		if IsLeapYear(year) then
			dayNumber = dayNumber - 366
			year = year + 1
		else
			dayNumber = dayNumber - 365
			year = year + 1
		end
	end
	
	-- could probably set this in the loop and avoid the additional function call
	if (IsLeapYear(year)) then
		daysThisYear = 366
	else
		daysThisYear = 365
	end
	
	-- this may fail slightly during the last week of the year, especially during a leap year
	-- TODO: fix that!
	weekDay = gpsTime // 86400000
	dayNumber = dayNumber + weekDay
	gpsTime = gpsTime - weekDay * 86400000
	
	hour = gpsTime // 3600000
	gpsTime = gpsTime - hour * 3600000
	minute = gpsTime // 60000
	gpsTime = gpsTime - minute * 60000
	second = gpsTime // 1000
	
	return {year=year, daysThisYear=daysThisYear, dayNumber=dayNumber, hour=hour, minute=minute, second=second}
end

function GetSolarElevAngle(gpsDate)
	location = gps:location(0)
	lat = location:lat() / 10000000
	lng = location:lng() / 10000000

	-- astronomical formulas from NOAA: https://www.esrl.noaa.gov/gmd/grad/solcalc/solareqns.PDF
	
	fractionalYear = 2 * math.pi / gpsDate.daysThisYear * (gpsDate.dayNumber - 1 + (gpsDate.hour - 12) / 24)

	decAngle = 0.006918 - 0.399912 * math.cos(fractionalYear) + 0.070257 * math.sin(fractionalYear) - 0.006758 * math.cos(2 * fractionalYear) 
	decAngle = decAngle + 0.000907 * math.sin(2 * fractionalYear) - 0.002697 * math.cos(3 * fractionalYear) + 0.00148 * math.sin(3 * fractionalYear)

	eqTime = 229.18 * (0.000075 + 0.001868 * math.cos(fractionalYear) - 0.032077 * math.sin(fractionalYear) - 0.014615 * math.cos(2 * fractionalYear) - 0.040849 * math.sin(2 * fractionalYear))

	timeOffset = eqTime + 4 * lng

	trueSolarTime = gpsDate.hour * 60 + gpsDate.minute + gpsDate.second / 60 + timeOffset

	hourAngle = math.rad((trueSolarTime / 4) - 180)

	cosZenithAngle = math.sin(math.rad(lat)) * math.sin(decAngle) + math.cos(math.rad(lat)) * math.cos(decAngle) * math.cos(hourAngle)

	return math.deg(math.asin(cosZenithAngle)) -- solar elevation is complementary to zenith angle
end

function update()

	-- wait for GPS fix
	if (gps:location(0):lat() == 0) then
		if (VERBOSE_MODE > 1) then gcs:send_text(0, "duskLights: Waiting for GPS fix") end
		return update, 5000 -- run every 5 seconds until GPS is configured
	end
	
	gpsDate = GetGPSDate() -- could call this from GetSolarElevAngle, but then we wouldn't have all that fun data to display
	
	elevAngle = GetSolarElevAngle(gpsDate)
	
	if (elevAngle < DUSK_ELEVATION) then
		setRelay(LIGHT_RELAY, ON_STATE)
	else
		setRelay(LIGHT_RELAY, ON_STATE ~ 1)
	end

	if (VERBOSE_MODE > 1) then
		gcs:send_text(0, string.format("duskLights: UTC %02d:%02d:%02d", gpsDate.hour, gpsDate.minute, gpsDate.second))	
		gcs:send_text(0, string.format("duskLights: Day %d of year %d", gpsDate.dayNumber, gpsDate.year))
		gcs:send_text(0, string.format("duskLights: Solar elevation %.2f", elevAngle))
	end
	
	return update, FREQUENCY * 1000
end

return update()
