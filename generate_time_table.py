from datetime import date, timedelta
sdate = date(2022, 1, 1)
edate = date(2022, 12, 31)
delta = edate - sdate
for i in range(delta.days + 1):
    cur_date = sdate + timedelta(days=i)
    weekday = cur_date.strftime('%a')
    target_time_in_hours = 6.0 if weekday not in ('Sat', 'Sun') else 0.0
    print(f"'{cur_date}': {target_time_in_hours}")
