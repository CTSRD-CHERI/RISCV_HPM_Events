#! /usr/bin/env python3
#-
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

parser = argparse.ArgumentParser(description='''
    Generate source files from a YAML configuration
    ''')

def roundup_power2 (x):
    return 2**(max(0, x-1)).bit_length()

parser.add_argument('-b','--bsv-output', nargs='?', const="Counters.bsv", default=None,
                    help="generate Bluespec file for defining RISC-V HPM events")

parser.add_argument('-c','--c-output', nargs='?', const="counters.h", default=None,
                    help="generate C header file for defining RISC-V HPM events")

args = parser.parse_args()

if args.bsv_output:
    header = c_bsv_header
    header += "\n// This file was generated by the parse_counters.py script"
    header += "\n// %s\n\n" % str(datetime.now())
    with open("counters.yaml", "r") as yfile, open(args.bsv_output, "w") as ofile:
        ya = yaml.load(yfile, Loader=yaml.FullLoader)
        vec_list = []
        for k in (ya.keys()):
            start_off = ya[k]["start_off"]
            end_off = ya[k]["end_off"]
            for c in (ya[k]["events"]):
                if(ya[k]["events"][c] + start_off >= end_off):
                    sys.exit("Node has counter numbers out of bounds: " + k)
            vec_list.append(ya[k])
        vec_list.sort(key=lambda x: x["start_off"])
        append_list = []
        zero_decls = "\n// Zero vector declarations"
        app_decls = "\n\n// Appending vectors"
        for i in range(len(vec_list)):
            append_list.append(vec_list[i]["toooba_name"])
            if (i + 1 < len(vec_list) and len(vec_list)):
                end_off = vec_list[i]["end_off"]
                start_off = vec_list[i+1]["start_off"]
                diff = start_off - end_off
                zero_decls += "\nVector#(%d, Bit #(Report_Width)) zero_vec_%d = replicate(0);" % (diff, i)
                append_list.append("zero_vec_%d" % i)
        print(append_list)


        for i in range(len(append_list)):
            if(i < 2):
                if(len(append_list) == 1):
                    app_decls += "\nlet events = " + (append_list[i]) + ";"
                elif (i == 1):
                    app_decls += "\nlet events = append(" + (append_list[i-1]) + ", " + append_list[i] + ");"
            else:
                app_decls += "\nevents = append(events, " + (append_list[i]) + ");"


        ofile.write(header)
        ofile.write(zero_decls)
        ofile.write(app_decls)


if args.c_output:
    header = c_bsv_header
    header += "\n// This file was generated by the parse_counters.py script"
    header += "\n// %s\n\n" % str(datetime.now())
    with open("counters.yaml", "r") as yfile, open(args.c_output, "w") as ofile:
        ya = yaml.load(yfile, Loader=yaml.FullLoader)
        vec_list = []
        for k in (ya.keys()):
            start_off = ya[k]["start_off"]
            end_off = ya[k]["end_off"]
            for c in (ya[k]["events"]):
                if(ya[k]["events"][c] + start_off >= end_off):
                    sys.exit("Node has counter numbers out of bounds: " + k)
            vec_list.append((k, ya[k]["start_off"]))


        vec_list.sort(key=lambda x: x[1])
        defines = ""
        for tu in vec_list:
            defines += "\n\n// " + tu[0].upper()
            for c in ya[tu[0]]["events"]:
                defines += "\n#define " + c.upper() + " " + str(ya[tu[0]]["events"][c] + tu[1])

        ofile.write(header)
        ofile.write(defines)