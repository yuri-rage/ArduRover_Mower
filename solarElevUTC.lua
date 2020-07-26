-- formulas available here: https://www.esrl.noaa.gov/gmd/grad/solcalc/solareqns.PDF
-- test results against: https://www.esrl.noaa.gov/gmd/grad/solcalc/

-- online lua interpreter: https://www.lua.org/cgi-bin/demo

-- lat/long can/should be derived by GPS - coords depict Phoenix in this example
LAT = 33.43
LON = -112.07

hour = os.date("!%H")
minute = os.date("!%M")
second = os.date("!%S")

daysThisYear = os.date("!%j", os.time({year=os.date("%Y"), month=12, day=31}))
dayNumber = os.date("!%j")

fractionalYear = 2 * math.pi / daysThisYear * (dayNumber - 1 + (hour - 12) / 24)

decAngle = 0.006918 - 0.399912 * math.cos(fractionalYear) + 0.070257 * math.sin(fractionalYear) - 0.006758 * math.cos(2 * fractionalYear) + 0.000907 * math.sin(2 * fractionalYear) - 0.002697 * math.cos(3 * fractionalYear) + 0.00148 * math.sin(3 * fractionalYear)

eqTime = 229.18 * (0.000075 + 0.001868 * math.cos(fractionalYear) - 0.032077 * math.sin(fractionalYear) - 0.014615 * math.cos(2 * fractionalYear) - 0.040849 * math.sin(2 * fractionalYear))

timeOffset = eqTime + 4 * LON

trueSolarTime = hour * 60 + minute + second / 60 + timeOffset

hourAngle = math.rad((trueSolarTime / 4) - 180)

cosZenithAngle = math.sin(math.rad(LAT)) * math.sin(decAngle) + math.cos(math.rad(LAT)) * math.cos(decAngle) * math.cos(hourAngle)

elevAngle = math.deg(math.asin(cosZenithAngle))

print(elevAngle)
