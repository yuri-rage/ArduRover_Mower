gcs:send_text(0, "Solar Elev Script Init")

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
	
	-- GPS epoch occured on 6 Jan 1980
	year = 1980
	dayNumber = gpsWeek * 7 + 6
	
    while (dayNumber > 365) do
		if IsLeapYear(year) then
			dayNumber = dayNumber - 366
			year = year + 1
		else
			dayNumber = dayNumber - 365
			year = year + 1
		end
	end
	
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

	-- wait for GPS config
	if (not gps:first_unconfigured_gps() == nil or not gps:first_unconfigured_gps() == 255) then
		return update, 5000 -- run every 5s until GPS is configured
	end
	
	gpsDate = GetGPSDate() -- could call this from GetSolarElevAngle, but then we wouldn't have all that fun data to display
	
	elevAngle = GetSolarElevAngle(gpsDate)

	gcs:send_text(0, "UTC: " .. string.format("%02d:", gpsDate.hour) .. string.format("%02d:", gpsDate.minute) .. string.format("%02d", gpsDate.second))	
	gcs:send_text(0, "Year: " .. tostring(gpsDate.year) .. "  Day: " .. tostring(gpsDate.dayNumber))
	gcs:send_text(0, "Solar Elevation: " .. string.format("%.2f", elevAngle))
	
	return update, 60000 -- consider 300000 (every 5 mins)
end

return update()
