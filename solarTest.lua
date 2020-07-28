function update()
	if (gps:first_unconfigured_gps() ~= nil) then
		weekNumber = gps:time_week(0)
		gcs:send_text(0, "GPS Week: " .. weekNumber)
	end
	return update, 3000
end

return update()
