
# Get and fix ISO timestamp (tz_utc) with proper padding for fractional seconds
raw_timestamp = tz_utc.replace('Z', '+00:00')

# Ensure fractional seconds are padded to 6 digits if needed
if '.' in raw_timestamp:
    date_part, frac_part = raw_timestamp.split('.')
    frac, offset = frac_part[:], ''
    if '+' in frac:
        frac, offset = frac.split('+')
        offset = '+' + offset
    elif '-' in frac:
        frac, offset = frac.split('-')
        offset = '-' + offset
    frac = frac.ljust(6, '0')  # Pad to 6 digits
    tz_utc = f"{date_part}.{frac}{offset}"
else:
    tz_utc = raw_timestamp

tz_utc = datetime.fromisoformat(tz_utc)
tz_est = tz_utc.astimezone(ZoneInfo('America/New_York'))
tz_est = tz_est.strftime('%Y-%m-%d %H:%M:%S.%f')[:-7]
