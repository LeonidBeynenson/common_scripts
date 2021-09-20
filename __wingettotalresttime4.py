#!/usr/bin/env python3

import argparse
import re
import sys
import subprocess
import time
import os
from enum import IntEnum
import copy
import datetime
import math
import texttable as tt
import yaml

def DEFAULT_TARGET_TIME_IN_HOURS():
    return 5.5 # hours

def print_table(list_of_rows):
    tab = tt.Texttable(max_width = 0)
    tab.set_chars(['', '|', '', ''])
    tab.set_deco(tt.Texttable.VLINES| tt.Texttable.BORDER)
    for row in list_of_rows:
        tab.add_row(row)

    print(tab.draw())


date_re = re.compile(r'^[0-9-_]+')
rest_re = re.compile(r'^rest +(\d+) +min')
rest_d_re = re.compile(r'^rest *$')
rest_q_re = re.compile(r'^rest *[?]+ *$')

def END_OF_DAY_TIME():
    return datetime.time(6)

def DEFAULT_TIME_STEP_IN_SECONDS():
    return int(15)

def DEFAULT_TIME_STEP_AS_TIMEDELTA():
    return datetime.timedelta(seconds = DEFAULT_TIME_STEP_IN_SECONDS())

def get_index_for_time(cur_time, first_time):
    delta1 = cur_time - first_time
    assert(delta1.days == 0)
    return int(delta1.seconds) // DEFAULT_TIME_STEP_IN_SECONDS()

def get_time_for_index(cur_index, first_time):
    return first_time + ( DEFAULT_TIME_STEP_AS_TIMEDELTA() * cur_index )

def convert_index_to_another_time_array(cur_index, first_time_from, first_time_to):
    time1 = get_time_for_index(cur_index, first_time_from)
    return get_index_for_time(time1, first_time_to)

class LogFileHandling:
    @staticmethod
    def DEFAULT_FOLDER_WITH_LOGS():
        #return "/home/leonid/worklog/"
        return "/home/lbeynens//worklog/"

    @staticmethod
    def current_worklog_name(date_suffix = None):
        if date_suffix is None:
            return "winlog_" + time.strftime("%Y-%m-%d")
        else:
            return "winlog_" + date_suffix


    @staticmethod
    def current_worklog_path(date_suffix = None):
        return os.path.join(LogFileHandling.DEFAULT_FOLDER_WITH_LOGS(), LogFileHandling.current_worklog_name(date_suffix))

    @staticmethod
    def current_worklog_remote_path(date_suffix = None):
        return LogFileHandling.current_worklog_path(date_suffix)

    @staticmethod
    def current_worklog_path_from_remote(date_suffix = None):
        return LogFileHandling.current_worklog_path(date_suffix) + ".remote"

#    @staticmethod
#    def scp_from_remote(ip_final_part):
#        assert(int(ip_final_part))
#        subprocess.call(["scp", "lbeynens@192.168.0." + str(int(ip_final_part)) + ":" + LogFileHandling.current_worklog_remote_path(), LogFileHandling.current_worklog_path_from_remote()])




# Rules of parsing of the main file:
#
# * If there is a timestamp in a line, then this time will have state "must_be_work"
#
# * If there is a segment of lines without timestamps and "^rest" patterns, then this segment will have state "may_be_work"
#   The lines with pattern "^work" may be absent in this case.
#
# * If there is a segment of lines without timestamps, with only "^rest *(\d+) *min" patterns, and WITHOUT "^rest *???" and "^rest *$" patterns, then this time segment
#   will correspond to a record in the list of "special time segments".
#   The record will contain information on rest with the pointed number of minutes and on work with the remaining number of minutes. All the items in the time segment will
#   contain the reference to the index of the time segment (see the class SpecialTimeSegment below)
#
#   But if the total number of rest minutes in the special segment is greater or equal the length of the time segment, then the segment will be marked as "must_be_rest"
#   (and special warning will be printed).
#
# * If there is a segment of lines without timestamps, with only "^rest *$" patterns, and WITHOUT "^rest *???" and "rest \d+ min" patterns, then this time segment
#   will be marked as "must_be_rest"
#
# * If there is a segment of lines without timestamps, with "^rest *???" patterns, then this time segment
#   will be marked as "may_be_rest", and any information how much minutes are written in the lines with "^rest *(\d+) *min" will be IGNORED (TODO: think about that)
#
# * Particular case of the latter item: if there is a segment of lines without timestamps, with both
#       "^rest *(\d+) *min *[^?]*$" and
#       "^rest *???" patterns,
#   then a special warning will be printed.
#   Note that the lines with the pattern "^rest *\d+ *min *?+$" will be considered as pattern "^rest *\d+ *min", not as "^rest *???", so
#   if there are only these lines in a segment, then it will be considered either as special time segment or "must_be_rest"
#   (depending on the number of rest minutes)
#
# * The lines with "^work" pattern will be ignored
#
#  So, we have the labels "must_be_work", "may_be_work", "must_be_rest", "may_be_rest", and special records for mixed "special time segments".
#
#
# Rules of parsing of the REMOTE File:
#
# * If there is a timestamp in a line, then this time will have state "must_be_work"
#
# * If there is a segment of lines without timestamps and "^rest" patterns, then this segment will have state "may_be_work"
#   The lines with pattern "^work" may be absent in this case.
#
# * If there is a segment of lines without timestamps that contains "^rest.*" pattern, then this time segment will have state "may_be_rest"
#   (We should not edit the remote file with complicated rest messages)
#
# * The lines with "^work" pattern will be ignored
#
#  So, after parsing a remote file we will have the labels "must_be_work", "may_be_work", and "may_be_rest" only.
#
#
#
# Rules of merging:
#
# the first is local file, the second -- REMOTE
# * X + X => X for any X except special time segments
#
# * must_be_work + must_be_work => must_be_work
# * must_be_work + may_be_work => must_be_work
# * must_be_work + may_be_rest => must_be_work
#
# * may_be_work + must_be_work => must_be_work
# * may_be_work + may_be_work => may_be_work
# * may_be_work + may_be_rest => may_be_work
#
# * must_be_rest + must_be_work => must_be_work (and a warning should be printed)
# * must_be_rest + may_be_work => must_be_rest
# * must_be_rest + may_be_rest => must_be_rest
#
# * may_be_rest + must_be_work => must_be_work
# * may_be_rest + may_be_work => may_be_work
# * may_be_rest + may_be_rest => may_be_rest
#
# * special time segment + must_be_work => must_be_work, and the number of rest items in the special time segment is decreased by 1
# * special time segment + may_be_work => may_be_work, and the number of rest items in the special time segment is decreased by 1
# * special time segment + may_be_rest => this special time segment without changes!
#
#  So, it is sufficient to make order
#  may_be_rest < may_be_work < must_be_rest < must_be_work
#  and for adding "normal" states just make maximum.
#
#  Attention:
#  Note that these rules for merging special time segments shows that in the main log file we should not mark as "work" the time period
#  when we work on another computer with a log that will be used as a remote log later.
#
#
# Rules of calculation:
#
# * must_be_work and may_be_work add 1 to the counter of work items
# * must_be_rest and may_be_rest add 1 to the counter of rest items
# * all special time segments that have negative number of work minutes are counted as "may_be_rest" and add 1 to the counter of rest time items
# * all special time segments that have negative number of rest minutes are counted as "may_be_work" and add 1 to the counter of work time items
# * all special time segments that have non-negative numbers of work and rest minutes convert the minutes to time items and add them to the corresponding counters

class State(IntEnum):
    may_be_rest = 1
    may_be_work = 2
    must_be_rest = 3
    must_be_work = 4

class SpecialTimeSegment:
    def __init__(self, first_time, last_time, num_rest_minutes):
        self.first_time = first_time
        self.last_time = last_time
        delta_time = last_time - first_time
        self.num_items_total = int(delta_time.seconds) // DEFAULT_TIME_STEP_IN_SECONDS();
        self.num_items_rest = int(num_rest_minutes) * 60 // DEFAULT_TIME_STEP_IN_SECONDS();
        self.num_items_work = self.num_items_total - self.num_items_rest

#class ReferenceToSpecialTimeSegment:
#    def __init__(self, index):
#        self.index = index

class Data:
    def __init__(self, first_time, last_time):
        delta1 = last_time - first_time
        assert (delta1.days == 0), str(delta1)
        if delta1.days > 0:
            print("WARNING: number of days =", delta1.days)
        required_len = 1 + int(delta1.seconds) // DEFAULT_TIME_STEP_IN_SECONDS()

        self.first_time = first_time
        self.last_time = last_time
        self.items = [None] * required_len
        self.special_time_segments = []





class FirstLastTimeDetector:
    @staticmethod
    def round_sec_in_datetime(cur_time, should_floor): #cur_time should be datetime.datetime
        time1 = copy.deepcopy(cur_time)
        time_sec = time1.second
        index_float = float(time_sec) / DEFAULT_TIME_STEP_IN_SECONDS()
        if should_floor:
            index = math.floor(index_float)
        else:
            index = math.ceil(index_float)

        new_seconds = int(index) * DEFAULT_TIME_STEP_IN_SECONDS()
        if new_seconds < 60:
            time1.replace(second = new_seconds)
        else:
            time1.replace(second = new_seconds-60)
            time1 = time1 + datetime.timedelta(minutes = 1)
        return time1


    @staticmethod
    def get_first_last_time_from_line_sequence(line_sequence):
        first_time = None
        last_time = None

        if not line_sequence:
            return (None, None)

        for line in line_sequence:
            date_match = date_re.match(line)
            if not date_match:
                continue
            cur_time_str = date_match.group()
            cur_time = datetime.datetime.strptime(cur_time_str, "%Y-%m-%d_%H-%M-%S")
            if not first_time:
                first_time = cur_time
            last_time = cur_time

        first_time = FirstLastTimeDetector.round_sec_in_datetime(first_time, should_floor = True)
        last_time = FirstLastTimeDetector.round_sec_in_datetime(last_time, should_floor = False)
        return (first_time, last_time)

    @staticmethod
    def get_first_last_time_from_line_sequences(line_sequence1, line_sequence2):
        (first_time1, last_time1) = FirstLastTimeDetector.get_first_last_time_from_line_sequence(line_sequence1)
        (first_time2, last_time2) = FirstLastTimeDetector.get_first_last_time_from_line_sequence(line_sequence2)
        if (first_time2 == None) or (last_time2 == None):
            return (first_time1, last_time1)
        if (first_time1 == None) or (last_time1 == None):
            return (first_time2, last_time2)
        return ( min(first_time1, first_time2), max(last_time1, last_time2) )

class Reader:
    def __init__(self, line_sequence, name, first_time, last_time, is_remote):
        self.line_sequence = line_sequence
        self.name = name
        self.first_time = first_time
        self.last_time = last_time
        self.is_remote = is_remote;

        #state
        self.clean_state(prev_index = None, prev_time = None)

    def clean_state(self, prev_index, prev_time):
#        print("clean_state: prev_index =", prev_index, "prev_time =", prev_time)
        self.prev_filled_index = prev_index
        self.prev_filled_time = prev_time
        self.is_rest = False
        self.is_rest_definitely = False
        self.is_rest_q = False
        self.total_sum_rest_minutes_for_block = 0

    def fill_indexes_in_data(self, data, cur_index, cur_time):
        assert( (cur_index >= 0) and isinstance(data, Data) and (cur_index < len(data.items)) )

        data.items[cur_index] = State.must_be_work

        if self.prev_filled_index == None:
            return

        if self.prev_filled_index == cur_index-1:
            return

        if self.prev_filled_index == cur_index:
            return #TODO: think about that

        prev = self.prev_filled_index #just alias
#        print("prev =", prev, "cur_index =", cur_index, "len(data.items) =", len(data.items))
        assert( (prev >= 0) and (prev < len(data.items)) and (prev < cur_index))

        cur_state = None
        if not self.is_rest and not self.is_rest_q and not self.is_rest_definitely:
            cur_state = State.may_be_work
        elif self.is_rest_q and self.is_rest_definitely:
            print("WARNING: in the '{}' in the time segment from {} to {} both 'definitely rest' and 'may be rest' marks are present " \
                    + "-- make the segment to be 'definitely rest'").format(self.name, self.prev_filled_time, self.cur_time)
            cur_state = State.must_be_rest
        elif self.is_rest and self.is_rest_definitely:
            print("WARNING: in the '{}' in the time segment from {} to {} both 'definitely rest' and 'rest' marks are present " \
                    + "-- make the segment to be 'definitely rest'").format(self.name, self.prev_filled_time, self.cur_time)
            cur_state = State.must_be_rest
        elif self.is_rest and self.is_rest_q:
            print("WARNING: in the '{}' in the time segment from {} to {} both 'may be rest' and 'rest' marks are present " \
                    + "-- make the segment to be 'may be rest'").format(self.name, self.prev_filled_time, cur_time)
            cur_state = State.may_be_rest
        elif  self.is_rest_definitely:
            cur_state = State.must_be_rest
        elif self.is_rest_q:
            cur_state = State.may_be_rest
        else:
            assert(self.is_rest and not self.is_rest_q and not self.is_rest_definitely)
            if self.is_remote:
                cur_state = State.may_be_rest
            else:
                spec_time_segment = SpecialTimeSegment(self.prev_filled_time, cur_time, self.total_sum_rest_minutes_for_block)

                if spec_time_segment.num_items_work <= 1 + 60.0 / DEFAULT_TIME_STEP_IN_SECONDS():
                    cur_state = State.may_be_rest
                elif spec_time_segment.num_items_rest <= 1 + 60.0 / DEFAULT_TIME_STEP_IN_SECONDS():
                    cur_state = State.may_be_work
                else:
                    data.special_time_segments.append(spec_time_segment)
                    last_index = len(data.special_time_segments) - 1
                    cur_state = data.special_time_segments[last_index]

        if self.is_remote and (cur_state == State.must_be_rest):
            cur_state = State.may_be_rest

        for index in range(prev+1, cur_index):
            data.items[index] = cur_state

        pass


    def parse(self):
        data = Data(self.first_time, self.last_time)
        self.clean_state(prev_index = None, prev_time = None)

        for line in self.line_sequence:
            is_empty_line = (len(line.strip()) == 0)
            if is_empty_line:
                continue

            date_match = date_re.match(line)
            rest_match = rest_re.match(line)
            rest_d_match = rest_d_re.match(line)
            rest_q_match = rest_q_re.match(line)

            if date_match:
                cur_time_str = date_match.group()
                cur_time = datetime.datetime.strptime(cur_time_str, "%Y-%m-%d_%H-%M-%S")
                cur_index = get_index_for_time(cur_time, self.first_time)
                assert( (cur_index >= 0) and (cur_index < len(data.items)) )
                self.fill_indexes_in_data(data, cur_index, cur_time)

                self.clean_state(prev_index = cur_index, prev_time = cur_time)

                continue

            if rest_match:
                self.is_rest = True
                self.total_sum_rest_minutes_for_block += int(rest_match.group(1))

            if rest_q_match:
                self.is_rest_q = True

            if rest_d_match:
                self.is_rest_definitely = True

        return data

def merge_data(data1, data2):
    if (data1 == None):
        return data2
    if (data2 == None):
        return data1

    data_loc = copy.deepcopy(data1)
    data_rem = copy.deepcopy(data2)
    #data_loc is local
    #data_rem is remote
    assert(isinstance(data_loc, Data))
    assert(isinstance(data_rem, Data))
    assert(len(data_loc.items) == len(data_rem.items))
    assert(data_loc.first_time == data_rem.first_time)
    assert(data_loc.last_time == data_rem.last_time)

    merged_data = Data(data_loc.first_time, data_loc.last_time)
    merged_data.special_time_segments = data_loc.special_time_segments

    for index in range(0, len(merged_data.items)):
        item1 = data_loc.items[index]
        item2 = data_rem.items[index]

        if item1 == None:
            merged_data.items[index] = item2
            continue
        if item2 == None:
            merged_data.items[index] = item1
            continue

        assert(isinstance(item2, State))
        assert(item2 != State.must_be_rest)

        if (isinstance(item1, State) and isinstance(item2, State)): #simple case

            if (item1 == item2):
                merged_data.items[index] = item1
                continue

            if (item1 == State.must_be_rest) and (item2 == State.must_be_work):
                print("Warning: conflict during merging, setting must_be_work state: in the time item with index {} " \
                        + "(corresponds {}) item1 is {} whereas item2 is {}").format(index, get_time_for_index(index, merged_data.first_time), item1, item2)
                merged_data.items[index] = State.must_be_work
                continue


            merged_data.items[index] = max(item1, item2)
            continue


        if isinstance(item1, SpecialTimeSegment):
            if item2 == State.may_be_rest:
                merged_data.items[index] = item1
                continue
            if (item2 == State.must_be_work) or (item2 == State.may_be_work):
                merged_data.items[index] = item2
                item1.num_items_rest -= 1
                continue
            raise RuntimeError()
        pass
    return merged_data

def calculate_time_info(data):
    if data is None:
        return None

    num_rest_items_from_list = 0;
    num_work_items_from_list = 0;

    for item in data.items:
        if item == None:
            continue

        if item in (State.may_be_work, State.must_be_work):
            num_work_items_from_list += 1
            continue

        if item in (State.may_be_rest, State.must_be_rest):
            num_rest_items_from_list += 1
            continue

        if isinstance(item, SpecialTimeSegment):
            if (item.num_items_rest >=0) and (item.num_items_work >= 0):
                continue #will be handled below
            if (item.num_items_rest <=0) and (item.num_items_work <= 0):
                continue #should not be handled
            if (item.num_items_rest < 0):
                num_work_items_from_list += 1
                continue
            if (item.num_items_work < 0):
                num_rest_items_from_list += 1
                continue

        print("ERROR: item =", item)
        raise RuntimeError()

    num_rest_items = num_rest_items_from_list
    num_work_items = num_work_items_from_list

    for item in data.special_time_segments:
        if (item.num_items_rest < 0) or (item.num_items_work < 0):
            continue #are handled above
        num_rest_items += item.num_items_rest
        num_work_items += item.num_items_work

    return { "num_rest_items_from_list": num_rest_items_from_list,
            "num_work_items_from_list": num_work_items_from_list,
            "num_rest_items": num_rest_items,
            "num_work_items": num_work_items}

def str_timedelta(td, num_colons=1):
    if td < datetime.timedelta():
        str_sign = '-'
        td = -td
    else:
        str_sign = ''
    return str_sign + ':'.join(str(td).split(':')[:(num_colons+1)])

def calc_time_to_should_work_for_target(time_info, target_time_in_hours=None):
    if target_time_in_hours is None:
        target_time_in_hours = DEFAULT_TARGET_TIME_IN_HOURS()

    time_to_should_work_for_target = (
            datetime.timedelta(hours = target_time_in_hours)
            -
            datetime.timedelta(seconds = int(time_info["num_work_items"]) * DEFAULT_TIME_STEP_IN_SECONDS())
            )
    return time_to_should_work_for_target

def print_time_info(time_info, time_to_should_work_for_target):
    print(time_info)
    print("rest from list =", str_timedelta(int(time_info["num_rest_items_from_list"]) * DEFAULT_TIME_STEP_AS_TIMEDELTA()))
    print("work from list =", str_timedelta(int(time_info["num_work_items_from_list"]) * DEFAULT_TIME_STEP_AS_TIMEDELTA()))
    print("total rest =", str_timedelta(int(time_info["num_rest_items"]) * DEFAULT_TIME_STEP_AS_TIMEDELTA()))
    print("total work =", str_timedelta(int(time_info["num_work_items"]) * DEFAULT_TIME_STEP_AS_TIMEDELTA()))
    print("speed of rest ={:.2}".format( float(time_info["num_rest_items"]) / float(time_info["num_rest_items"] + time_info["num_work_items"]) ))

    ideal_time_of_target = datetime.datetime.now() + time_to_should_work_for_target
    print("TIME_TO_SHOULD_WORK_FOR_TARGET =", str_timedelta(time_to_should_work_for_target, num_colons=2))
    print("IDEAL_TIME_OF_TARGET =", ideal_time_of_target.strftime("%H:%M:%S"))

def print_data_as_list(data, should_shorten = False, num_minutes_to_print_in_short=2):
    if data == None:
        print("No data")
        return

    assert(isinstance(data, Data))
    prev_item = data.items[0]
    prev_index = 0

    list_rests = []

    for (cur_index, cur_item) in enumerate(data.items):
        if (cur_item == prev_item) and (cur_index+1 != len(data.items)):
            continue
        prev_time = get_time_for_index(prev_index, data.first_time)
        cur_time = get_time_for_index(cur_index-1, data.first_time)
        diff_time = cur_time - prev_time
        diff_time_min = diff_time.seconds // 60

        str_prev_time = prev_time.strftime("%H:%M:%S")
        str_cur_time = cur_time.strftime("%H:%M:%S")

        str_prev_item = str(prev_item)
        if isinstance(prev_item, SpecialTimeSegment):
            w = prev_item.num_items_work * DEFAULT_TIME_STEP_IN_SECONDS() // 60
            r = prev_item.num_items_rest * DEFAULT_TIME_STEP_IN_SECONDS() // 60
            str_prev_item = "work: {} rest: {}".format(w, r)
        else:
            if prev_item == State.must_be_work:
                str_prev_item = "W"
            elif prev_item == State.must_be_rest:
                str_prev_item = "R"
            elif prev_item == State.may_be_work:
                str_prev_item = "W?"
            elif prev_item == State.may_be_rest:
                str_prev_item = "R?"

        if (not should_shorten) or (diff_time_min > num_minutes_to_print_in_short):
            print("{} => {}  ({:3} min): {}".format(str_prev_time, str_cur_time, diff_time_min, str_prev_item))

        if ( (prev_item == State.must_be_rest) or (prev_item == State.may_be_rest) ) and (diff_time_min > 2):
            list_rests.append(diff_time_min)

        prev_index = cur_index
        prev_item = cur_item

    print("rests from lists:", list_rests)
    rests_from_spec_time_segments = [ int(x.num_items_rest) * DEFAULT_TIME_STEP_IN_SECONDS() // 60 for x in data.special_time_segments ]
    print("rests from special time segments:", rests_from_spec_time_segments)


def print_data_as_table(data1, data2 = None, data3 = None):
    def str_for_item(item):
        str_item = str(item)
        if isinstance(item, SpecialTimeSegment):
            w = item.num_items_work * DEFAULT_TIME_STEP_IN_SECONDS() // 60
            r = item.num_items_rest * DEFAULT_TIME_STEP_IN_SECONDS() // 60
            str_item = "w: {} r: {}".format(w, r)
        else:
            if item == State.must_be_work:
                str_item = "W"
            elif item == State.must_be_rest:
                str_item = "R"
            elif item == State.may_be_work:
                str_item = "W?"
            elif item == State.may_be_rest:
                str_item = "R?"
        return str_item

    assert(isinstance(data1, Data))
    if data2:
        assert(isinstance(data2, Data))
    if data3:
        assert(isinstance(data3, Data))

    first_time = data1.first_time
    last_time = data1.last_time

    if data2:
        first_time = min(first_time, data2.first_time)
        last_time = max(last_time, data2.last_time)
    if data3:
        first_time = min(first_time, data3.first_time)
        last_time = max(last_time, data3.last_time)

    num_items = get_index_for_time(last_time, first_time) + 1

    table_rows = []
    for cur_index in range(num_items):
        index1 = convert_index_to_another_time_array(cur_index, first_time, data1.first_time)
        item1 = data1.items[index1]
        item2 = None
        item3 = None
        if data2:
            index2 = convert_index_to_another_time_array(cur_index, first_time, data2.first_time)
            item2 = data2.items[index2]
        if data3:
            index3 = convert_index_to_another_time_array(cur_index, first_time, data3.first_time)
            item3 = data3.items[index3]

        cur_time = get_time_for_index(cur_index, first_time)
        str_cur_time = cur_time.strftime("%H:%M:%S")

        table_rows.append([str_cur_time, str_for_item(item1), str_for_item(item2), str_for_item(item3)])
    print_table(table_rows)

def _skip_up_to_char(s, c):
    if c not in s:
        return s
    return s[s.rindex(c)+1:]

def main_for_line_sequences(line_sequence1, line_sequence2, name1, name2, should_print_whole_table,
                            very_short_print=False,
                            target_time_table=None):
    LEN_SMALL_HRULE = 60
    LEN_BIG_HRULE = 80
    HRULE = "=" * LEN_SMALL_HRULE
    HEADING_HRULE = "=" * LEN_BIG_HRULE
    what_parsing = "parsing {} and {}".format(name1, name2)

    print(HEADING_HRULE)
    print("Begin " + what_parsing)

    (total_first_time, total_last_time) = FirstLastTimeDetector.get_first_last_time_from_line_sequences(line_sequence1, line_sequence2)

    if line_sequence1:
        reader1 = Reader(line_sequence1, name1, total_first_time, total_last_time, is_remote=False)
    else:
        reader1 = None

    if line_sequence2:
        reader2 = Reader(line_sequence2, name2, total_first_time, total_last_time, is_remote=True)
    else:
        reader2 = None

    if reader1:
        data1 = reader1.parse()
    else:
        data1 = None

    if reader2:
        data2 = reader2.parse()
    else:
        data2 = None

    data_merged = merge_data(data1, data2)

    time_info = calculate_time_info(data_merged)

    print((HRULE))
    if not very_short_print:
        print("Local")
        print_data_as_list(data1)
        print("")
        print("Remote")
        print_data_as_list(data2)
        print("")
        print("Merged")
        print_data_as_list(data_merged)

        print(HRULE)
    print("Merged shortened")
    num_minutes_to_print_in_short = 2 if not very_short_print else 10
    print_data_as_list(data_merged, True, num_minutes_to_print_in_short=num_minutes_to_print_in_short)

    if should_print_whole_table:
        print(HRULE)
        print_data_as_table(data1, data2, data_merged)

    print(HRULE)
    if target_time_table:
        name_for_time_table = name1
        name_for_time_table = _skip_up_to_char(name_for_time_table, '_')
        name_for_time_table = _skip_up_to_char(name_for_time_table, '/')
        target_time_in_hours = target_time_table.get(name_for_time_table, DEFAULT_TARGET_TIME_IN_HOURS())
        print(f'target_time_in_hours={target_time_in_hours}')
    else:
        target_time_in_hours = DEFAULT_TARGET_TIME_IN_HOURS()

    time_to_should_work_for_target = calc_time_to_should_work_for_target(time_info, target_time_in_hours)
    print_time_info(time_info, time_to_should_work_for_target)

    print(HRULE)
    print("End " + what_parsing)
    print(HEADING_HRULE)
    return time_to_should_work_for_target

def read_line_sequence_from_file(file_path):
    with open(file_path, encoding="utf8", errors='ignore') as f:
        lines = list(f)
    return lines

def main_for_files(file1, file2, should_print_whole_table, very_short_print=False):
    line_sequence1 = read_line_sequence_from_file(file1)
    line_sequence2 = read_line_sequence_from_file(file1)
    name1 = os.path.basename(file1) if file1 else None
    name2 = os.path.basename(file2) if file2 else None
    return main_for_line_sequences(line_sequence1, line_sequence2, name1, name2, should_print_whole_table,
                                   very_short_print=very_short_print)

def read_line_sequence_from_files(files):
    # TODO: add sorting of files
    separator = []
    line_sequence = []
    for file1 in files:
        cur_line_sequence = read_line_sequence_from_file(file1)
        line_sequence += separator + cur_line_sequence
        separator = ["rest"]
    return line_sequence

def split_line_sequence_by_dates(line_sequence):
    cur_day_begin_date = None
    line_sequences_by_dates = {}
    for line in line_sequence:
        date_match = date_re.match(line)
        if not date_match:
            if cur_day_begin_date:
                line_sequences_by_dates[cur_day_begin_date].append(line)
            else:
                print(f"WARNING: skipping the first line '{line}'")
            continue
        cur_time_str = date_match.group()
        cur_time = datetime.datetime.strptime(cur_time_str, "%Y-%m-%d_%H-%M-%S")
        cur_date = cur_time.date()
        if cur_time.time() < END_OF_DAY_TIME():
            cur_date -= datetime.timedelta(days=1)
        cur_day_begin_date = cur_date.strftime("%Y-%m-%d")
        line_sequences_by_dates.setdefault(cur_day_begin_date, []).append(line)
    return line_sequences_by_dates


def main_for_file_list(files1, should_print_whole_table, very_short_print=False,
                       target_time_table_path=None):
    if target_time_table_path:
        with open(target_time_table_path) as f:
            target_time_table = yaml.safe_load(f)
    else:
        target_time_table = None

    line_sequence = read_line_sequence_from_files(files1)
    line_sequences_by_dates = split_line_sequence_by_dates(line_sequence)

    summary_dt = datetime.timedelta()
    for cur_date, line_sequence in line_sequences_by_dates.items():
        dt = main_for_line_sequences(line_sequence, None, cur_date, None, should_print_whole_table,
                                     very_short_print=very_short_print,
                                     target_time_table=target_time_table)
        summary_dt += dt

    print("SUM OF TIME_TO_SHOULD_WORK_FOR_TARGET-s =", str_timedelta(summary_dt, num_colons=2))
    print("SUM OF TIME_TO_SHOULD_WORK_FOR_TARGET-s in DAYS = {:.3}".format(summary_dt / datetime.timedelta(hours = DEFAULT_TARGET_TIME_IN_HOURS())))


def main_for_one_date_suffix(date_suffix, should_print_whole_table):
    file1 = LogFileHandling.current_worklog_path(date_suffix)
    file2 = LogFileHandling.current_worklog_path_from_remote(date_suffix)
    print(f'Date suffix = {date_suffix}')
    print(f'file1 = {file1}')
    print(f'file2 = {file2}')
    main_for_files(file1, file2, should_print_whole_table)

def main_for_date_suffixes(date_suffixes, should_print_whole_table):
    if not date_suffixes:
        main_for_one_date_suffix(None, should_print_whole_table)
        return

    for date_suffix in date_suffixes:
        main_for_one_date_suffix(date_suffix, should_print_whole_table)

def extract_date_suffixes_from_inputs(inputs):
    date_suffixes = []
    for cur_arg in inputs:
        date_suffix = cur_arg
        winlog_prefix = "winlog_"
        if winlog_prefix in date_suffix:
            print("Since input_param is", date_suffix, "remove the first part of it to get date_suffix")
            index = date_suffix.rfind(winlog_prefix )
            date_suffix = date_suffix[index + len(winlog_prefix):]
        print("date_suffix =", date_suffix)
        date_suffixes.append(date_suffix)
    return date_suffixes

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--should_print_whole_table", action="store_true", help="If should print the whole table")
    parser.add_argument("--should_use_date_suffix", action="store_true",
                        help="If the input values should be used as date suffixes, not files "
                             "(at the moment the second remote file is implemented for date suffixes only)")
    parser.add_argument("--short", action="store_true",
                        help="If should print very shortened time list only")
    parser.add_argument("--target-time-table", nargs='?', const='/home/lbeynens/worklog/time_table.yml',
                        help="The path to the time table -- a YAML file with dict of target time-s in format {<date>: <time in hours>}, "
                              "(e.g. {'2021-04-30':5.5, '2021-05-01': 0})")
    parser.add_argument("inputs", nargs="*", help="Input files or date suffixes")
    args = parser.parse_args()

    should_print_whole_table = args.should_print_whole_table
    if args.should_use_date_suffix:
        date_suffixes = extract_date_suffixes_from_inputs(args.inputs)
        main_for_date_suffixes(date_suffixes, should_print_whole_table)
        return

    inputs = args.inputs
    if not inputs:
        inputs = [LogFileHandling.current_worklog_path(None)]

    main_for_file_list(inputs, should_print_whole_table, very_short_print=args.short,
                       target_time_table_path=args.target_time_table)


if __name__ == "__main__":
    main()

#
#
#    should_print_whole_table = False
#    date_suffixes = []
#    for cur_arg in sys.argv[1:]:
#        # TODO: use ArgumentParser
#
#        if (cur_arg == "all"):
#            should_print_whole_table = True
#            continue
#
#        date_suffix = cur_arg
#        winlog_prefix = "winlog_"
#        if winlog_prefix in date_suffix:
#            print("Since input_param is", date_suffix, "remove the first part of it to get date_suffix")
#            index = date_suffix.rfind(winlog_prefix )
#            date_suffix = date_suffix[index + len(winlog_prefix):]
#        print("date_suffix =", date_suffix)
#        date_suffixes.append(date_suffix)
#
#    main(date_suffixes, should_print_whole_table)

