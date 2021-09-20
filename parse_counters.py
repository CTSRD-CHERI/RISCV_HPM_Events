#! /usr/bin/env python3
#
# SPDX-License-Identifier: BSD-2-Clause
#
# Copyright (c) 2021 Franz Fuchs
# All rights reserved.
#
# This software was developed by SRI International and the University of
# Cambridge Computer Laboratory (Department of Computer Science and
# Technology) under DARPA contract HR0011-18-C-0016 ("ECATS"), as part of the
# DARPA SSITH research programme.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#

import yaml
import argparse
from datetime import datetime
import sys

c_bsv_header = """/*-
 * SPDX-License-Identifier: BSD-2-Clause
 *
 * This software was developed by SRI International and the University of
 * Cambridge Computer Laboratory (Department of Computer Science and
 * Technology) under DARPA contract HR0011-18-C-0016 ("ECATS"), as part of the
 * DARPA SSITH research programme.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
 * OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
 * LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
 * OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
 * SUCH DAMAGE.
 */
"""

header_date = """/*
 * This file was generated by the parse_counters.py script
 * %s
 */
""" % str(datetime.now())

data_t = "Bit#(Report_Width)"

parser = argparse.ArgumentParser(description='''
    Generate source files from a YAML configuration
    ''')


class Event():
    def __init__(self, name, offset):
        super().__init__()
        self.name = name
        self.offset = offset


class EventSet():
    def __init__(self, name, config):
        super().__init__()
        self.name = name
        self.struct_name = config["struct_name"]
        self.start = config["start_off"]
        self.end = config["end_off"]
        events = []
        for event, offset in config["events"].items():
            if offset not in range(0, self.end - self.start):
                raise ValueError(name + " event " + event + " - out of bounds")
            events.append(Event(event, offset))
        events.sort(key=lambda event: event.offset)
        if not events:
            raise ValueError(name + " has no events defined")
        self.events = events


class EventsConfig():
    def __init__(self, config):
        super().__init__()
        sets = []
        for name, eventset in config:
            sets.append(EventSet(name, eventset))
        if not sets:
            raise ValueError("no event sets defined")
        sets.sort(key=lambda eventset: eventset.start)
        prev_end = -1
        for eventset in sets:
            if eventset.start <= prev_end:
                raise ValueError(eventset.name +
                                 " overlaps with previous event set")
        self.eventsets = sets
        self.start = sets[0].start
        self.end = sets[-1].end


def load_config(filename):
    with open(filename, "r") as f:
        ya = yaml.load(f, Loader=yaml.FullLoader)
        return EventsConfig(ya.items())


def genHPMVector(config, filename, report_width_import):
    sections = []
    sections.append(c_bsv_header)
    sections.append(header_date)
    imp_decl = "import Vector::*;\n"
    imp_decl += "import StatCounters::*;\n"
    imp_decl += report_width_import
    sections.append(imp_decl)

    function = "function Vector#(" + str(config.end) + ", " + data_t + \
        ") generateHPMVector(HPMEvents ev);\n"
    function += "\tVector#(" + str(config.end) + ", " + data_t + \
        ") events = replicate(0);\n"
    for eventset in config.eventsets:
        function += "\tif (ev.mab_" + eventset.struct_name + \
            " matches tagged Valid .t) begin\n"
        for event in eventset.events:
            function += "\t\tevents[" + \
                str(eventset.start + event.offset) + \
                "] = t.evt_" + event.name.upper() + ";\n"
        function += "\tend\n"
    function += "\treturn events;\n"
    function += "endfunction\n"
    sections.append(function)

    with open(filename, "w") as f:
        f.write("\n".join(sections))


def genStatCounters(config, filename, report_width_import):
    sections = []
    sections.append(c_bsv_header)
    sections.append(header_date)
    sections.append(report_width_import)
    sections.append("typedef %d No_Of_Evts;\n" % (config.end))

    hpm_events_struct = "typedef struct {\n"
    for eventset in config.eventsets:
        decl = "typedef struct {\n"
        for event in eventset.events:
            decl += "\t" + data_t + " evt_" + event.name.upper() + ";\n"
        decl += "} " + eventset.struct_name + " deriving (Bits, FShow);\n"
        sections.append(decl)
        hpm_events_struct += "\tMaybe#(" + eventset.struct_name + \
            ") mab_" + eventset.struct_name + ";\n"
    hpm_events_struct += "} HPMEvents deriving (Bits, FShow);\n"
    sections.append(hpm_events_struct)

    with open(filename, "w") as f:
        f.write("\n".join(sections))


def genCOutput(config, filename):
    sections = []
    sections.append(c_bsv_header)
    sections.append(header_date)

    for eventset in config.eventsets:
        section = "/* " + eventset.name.upper() + " */\n"
        for event in eventset.events:
            section += "#define " + eventset.name.upper() + "_" + \
                event.name.upper() + " " + \
                str(eventset.start + event.offset) + "\n"
        sections.append(section)

    with open(filename, "w") as f:
        f.write("\n".join(sections))


def main():
    parser = argparse.ArgumentParser(description='''
        Generate RISC-V HPM events source files from a YAML configuration
        ''')

    parser.add_argument('config', type=str, help="path to the YAML file")

    parser.add_argument('-m', '--bsv-report-width-module', metavar='module',
                        default=None, help="module containing Report_Width")

    parser.add_argument('-b', '--bsv-output', nargs='?', metavar='file',
                        const="GenerateHPMVector.bsv", default=None,
                        help="output BSV struct to bit vector converter")

    parser.add_argument('-s', '--bsv-stat-definitions-output', nargs='?',
                        metavar='file', const="StatCounters.bsv", default=None,
                        help="output BSV struct definition")

    parser.add_argument('-c', '--c-output', nargs='?', metavar='file',
                        const="counters.h", default=None,
                        help="output C header with event numbers")

    args = parser.parse_args()

    config = load_config(args.config)

    def get_report_width_import():
        if not args.bsv_report_width_module:
            sys.exit("Must specify the module containing Report_Width " +
                     "when generating BSV output")
        return "import " + args.bsv_report_width_module + "::Report_Width;\n"

    if args.c_output:
        genCOutput(config, args.c_output)

    if args.bsv_output:
        genHPMVector(config, args.bsv_output, get_report_width_import())

    if args.bsv_stat_definitions_output:
        genStatCounters(config, args.bsv_stat_definitions_output,
                        get_report_width_import())


if __name__ == "__main__":
    main()
