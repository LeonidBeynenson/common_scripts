#!/usr/bin/env python

import time
import re
import sys
import datetime
import texttable as tt
import os
import termcolor

LINE_STR = ("=" * 100)

def print_table(list_of_rows):
    tab = tt.Texttable(max_width = 0)
    tab.set_chars(['', '=', '', ''])
    tab.set_deco(tt.Texttable.VLINES| tt.Texttable.BORDER)
    for row in list_of_rows:
        tab.add_row(row)

    print tab.draw()

def DEFAULT_FOLDER_WITH_LOGS():
    return "/home/leonid/worklog/"

def get_default_worklog():
    filelist = os.listdir(DEFAULT_FOLDER_WITH_LOGS())
    re_worklog = re.compile(r'winlog_\d\d\d\d-\d\d-\d\d$')
    filtered_filelist = [s for s in filelist if re_worklog.match(s)]

    if not filtered_filelist:
        return None

    filtered_filelist.sort()
    filename = os.path.join(DEFAULT_FOLDER_WITH_LOGS(), filtered_filelist[-1])
    return filename

def _str_timedelta(dt):
    assert(dt.days >= 0)
    numsec = int(dt.total_seconds())
    nummin = numsec // 60
    numhours = nummin // 60
    nummin = nummin % 60
    return "{:02}:{:02}".format(numhours, nummin)

def str_timedelta(dt):
    if dt.days < 0:
        return "-" + _str_timedelta(-dt)
    return _str_timedelta(dt)

def timedelta_from_seconds(val):
    return datetime.timedelta(seconds = int(val))

def str_time_or_day(datetime_val):
    if not datetime_val:
        return "None"

    val_date = datetime_val.date()
    now_date = datetime.datetime.now().date()
    if (val_date == now_date):
        return str(datetime_val.time())
    return "not today"

def parse_file(filename):
    first_time = None
    last_time = None
    rest_array = []

    date_re = re.compile(r'^[0-9-_]+')
    rest_re = re.compile(r'^rest +(\d+) +min')

    lines = [line.rstrip(' \n') for line in open(filename)]

    last_start_of_sitting_date = ""
    for line in lines:
        if not line:
            last_start_of_sitting_date = ""
            continue # it may be a bit faster, although worser for debugging

        date_match = date_re.match(line)
        rest_match = rest_re.match(line)
        if date_match:
            curdate = date_match.group()
            tuple_time = datetime.datetime.strptime(curdate, "%Y-%m-%d_%H-%M-%S")

            if not first_time:
                first_time = tuple_time

            last_time = tuple_time

            if not last_start_of_sitting_date:
                last_start_of_sitting_date = tuple_time

            line = "date (" + curdate + ")=" + str(tuple_time) + ":" + line

        if rest_match:
            rest_minutes = int(rest_match.group(1))
            rest_array.append(rest_minutes)
            line = "rest (" + str(rest_minutes) + " min): " + line

        if not date_match and not rest_match and line:
            line = "!!!! " + line

        if False:
            #for debugging only
            print line

        pass

    print "first_time = " + str(first_time)
    print "last_time = " + str(last_time)

    dt_total_time = last_time - first_time

    print "dt_total_time = " + str(dt_total_time)
    print

    total_rest_minutes = sum(rest_array)
    print "total_rest_minutes = " + str(total_rest_minutes)

    if not total_rest_minutes:
        total_rest_minutes = 0

    dt_total_rest_time = datetime.timedelta(minutes = total_rest_minutes)
    print "dt_total_rest_time = " + str(dt_total_rest_time)
    print "num of rests = " + str(len(rest_array))
    str_rest_array = [str(v) for v in rest_array]
    print "rests = [" + ",".join(str_rest_array) + "]"

    dt_total_time_no_rest = dt_total_time - dt_total_rest_time

    print "dt_total_time_no_rest = " + str(dt_total_time_no_rest)

    dt_target_time_to_work = datetime.timedelta(hours = 6)
#    print "dt_target_time_to_work = " + str(target_time_to_work)


    dt_time_to_should_work_for_target = dt_target_time_to_work - dt_total_time_no_rest
    ideal_time_of_target = last_time + dt_time_to_should_work_for_target
#    print "CURRENT_ARREARS = TIME_TO_SHOULD_WORK_FOR_TARGET = " + str(dt_time_to_should_work_for_target)
#    print "ideal_time_of_target = " + str(ideal_time_of_target.time())


    print
    print "last_start_of_sitting_time = " + str(last_start_of_sitting_date.time())
    print "time of sitting = " + str_timedelta(last_time - last_start_of_sitting_date)


    print
    print LINE_STR
    print


    speed_of_rest = 0
    if dt_total_time.total_seconds():
        speed_of_rest = dt_total_rest_time.total_seconds() / dt_total_time.total_seconds()

    assert(speed_of_rest >= 0)
    assert(speed_of_rest <= 1)

    coeff_to_approx = 1.0 / (1.0 - speed_of_rest - 0.0001)
    print "speed_of_rest = {:.2}\n(coeff_to_approx = {:.2})".format(speed_of_rest, coeff_to_approx)

    print


    dt_approx_time_to_make_the_target = datetime.timedelta(seconds = int(coeff_to_approx * dt_time_to_should_work_for_target.total_seconds()))
    approx_time_of_target_fulfill = last_time + dt_approx_time_to_make_the_target

    print_table([
        ["dt_approx_time_to_make_the_target", str_timedelta(dt_approx_time_to_make_the_target)],
        ["approx_time_of_target_fulfill", str_time_or_day(approx_time_of_target_fulfill)]
        ])


    print
    print LINE_STR
    print

    time_to_go = datetime.datetime.combine(last_time, datetime.time(hour = 20, tzinfo = last_time.time().tzinfo))
    dt_time_to_job_if_go_intime = time_to_go - last_time
    dt_approx_additional_rest_time_if_go_in_time = timedelta_from_seconds(dt_time_to_job_if_go_intime.total_seconds() * speed_of_rest)
    dt_approx_arrears__if_go_in_time = dt_time_to_should_work_for_target - dt_time_to_job_if_go_intime + dt_approx_additional_rest_time_if_go_in_time
    ideal_arrears__if_go_in_time = ideal_time_of_target - time_to_go

    #begin calculation of time_to_start_work_hard
    speed_of_rest_ideal = 0.1
    print "speed_of_rest_ideal =", speed_of_rest_ideal
    _dt_time_to_job_with_coeff__minus__cur_arrears_seconds = (
            (1 - speed_of_rest_ideal) * dt_time_to_job_if_go_intime.total_seconds()
            -
            dt_time_to_should_work_for_target.total_seconds()
            )
    delta_speeds_of_rest = speed_of_rest - speed_of_rest_ideal
#    print "(dt_time_to_job_if_go_intime.total_seconds() =", dt_time_to_job_if_go_intime.total_seconds()
#    print "(dt_time_to_should_work_for_target.total_seconds() =", dt_time_to_should_work_for_target.total_seconds()
#    print "(_dt_time_to_job_with_coeff__minus__cur_arrears_seconds =", _dt_time_to_job_with_coeff__minus__cur_arrears_seconds
#    print "(delta_speeds_of_rest =", delta_speeds_of_rest

    if delta_speeds_of_rest > 0:
        time_to_start_work_hard = last_time + timedelta_from_seconds(_dt_time_to_job_with_coeff__minus__cur_arrears_seconds / delta_speeds_of_rest )
    else:
        time_to_start_work_hard = None
    #end calculation of time_to_start_work_hard

    print_table([
        ["time_to_go", str_time_or_day(time_to_go)],
        ["dt_time_to_job_if_go_intime", str_timedelta(dt_time_to_job_if_go_intime)],
        ["dt_approx_additional_rest_time_if_go_in_time", str_timedelta(dt_approx_additional_rest_time_if_go_in_time)],
        ])
    print_table([
        ["APPROX_ARREARS__IF_GO_IN_TIME", str_timedelta(dt_approx_arrears__if_go_in_time)],
        ["IDEAL_ARREARS__IF_GO_IN_TIME", str_timedelta(ideal_arrears__if_go_in_time)],
        ["TIME_TO_START_WORK_HARDER", str_time_or_day(time_to_start_work_hard)]
        ])


    print
    print LINE_STR
    print
    print "CURRENT_ARREARS:"
    print_table([
        ["TIME_TO_SHOULD_WORK_FOR_TARGET", str_timedelta(dt_time_to_should_work_for_target)],
        ["ideal_time_of_target", str_time_or_day(ideal_time_of_target)]
        ])

#    first_datetime = datetime.datetime(*first_time[:6])
#    last_datetime = datetime.datetime(*last_time[:6])
#    print "first_datetime = " + str(first_datetime)
#    print "last_datetime = " + str(last_datetime)


if __name__ == "__main__":
    filename = None
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = get_default_worklog()

    if not filename:
        print "ERROR -- cannot get the last worklog"
        exit(1)

    print "filename =", filename

    parse_file(filename)

