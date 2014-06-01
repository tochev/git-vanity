#!/usr/bin/python3
"""
git-vanity, a script to make vanity commits
This is done either by changing the committer's name or the raw commit object.
Copyright (C) 2014  Tocho Tochev <tocho AT tochev DOT net>

Please tweak GS and WS to suit your video card.


    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

VERSION = "0.1.0"

import argparse
import numpy as np
import os
import pyopencl as cl
import re
import struct
import subprocess
import time
from datetime import timedelta
from hashlib import sha1


GS = 4*1024*1024      # GPU iteration global_size
WS = 64               # work_size
MIN_PROGRESS_RESOLUTION = 1.0 # seconds

def hex2target(hex_prefix):
    """Returns 5*int32 0-padded target and bit length based on hex prefix"""
    data = hex_prefix + ('0' * (40 - len(hex_prefix)))
    target = np.array(
        [int(data[i*8 : (i+1)*8], 16) for i in range(5)],
        dtype=np.uint32)
    return target, len(hex_prefix)*4

def progress(start, stop, step, precision_bits, quiet=False):
    """yields new starts and displays progress"""
    # deals with uint64
    assert step > 0

    if not quiet:
        start_time = time.time()
        last_progress_time = None
        last_progress_current = start

    current = start
    while current < stop:

        if not quiet:
            time_now = time.time()

            if (not last_progress_time or
                (time_now - last_progress_time) > MIN_PROGRESS_RESOLUTION):
                finished = current - start
                run_time = time_now - start_time

                if not last_progress_time:
                    print('\b\r\b\r')

                print("Processing GS iteration %s" %
                    (finished // step + 1))
                print("   Time:         %s" %
                        timedelta(seconds=run_time))
                if last_progress_current == current:
                    print("   Last Speed:   N/A MH/s      (Avg: N/A MH/s)")
                else:
                    print("   Last Speed:   %.4f MH/s     (Avg: %.4f MH/s)" %
                            (((current - last_progress_current) /
                                (time_now - last_progress_time)) / 10**6,
                            (finished / run_time) / 10**6))
                print("   Tries remaining (optimistic):  %.6f%% ..." %
                    (100 * (1 - float(finished) / (1 << precision_bits))))
                print("   Chance (CDF):                  %.6f%% ..." %
                    (100 * (1 -
                        (1 - 1.0 / (1 << precision_bits)) ** (finished))))

                last_progress_time = time.time()
                last_progress_current = current

        yield current

        current += step

def get_padded_size(size):
    """Returns the size of the text of size `size' after preprocessing"""
    if (size % 64) > 55:
        return ((size // 64) + 2) * 64
    return ((size // 64) + 1) * 64

def sha1_preprocess_data(data):
    size = get_padded_size(len(data))
    preprocessed_message = np.zeros(size, dtype=np.ubyte)
    preprocessed_message[:len(data)] = list(data)
    preprocessed_message[len(data)] = 0x80
    preprocessed_message[-8:] = list(struct.pack('>Q', len(data)*8))
    return preprocessed_message

def display_device_info(opencl_device):
    print("Using device: '%s' (device type: %s)" %
            (opencl_device.name,
             {cl.device_type.CPU: "CPU",
              cl.device_type.GPU: "GPU"}.get(opencl_device.type, 'unknown')))

def load_opencl():
    """Returns opencl context, queue, program"""
    CL_PROGRAM = open(
        os.path.join(
            os.path.dirname(
                os.path.realpath(
                    __file__)),
            "sha1_prefix_search.cl"),
        "r").read()
    ctx = cl.create_some_context()
    queue = cl.CommandQueue(ctx)
    prg = cl.Program(ctx, CL_PROGRAM).build()
    return ctx, queue, prg

def extract_commit(rev):
    return subprocess.check_output(["git", "cat-file", "-p", rev])

def preprocess_commit_committer_change(commit):
    """
    Returns:
        [commit_with_header_and_placeholder,
        placeholder_offset,
        committer_name, committer_mail, committer_date]
    """
    commit_lines = list(commit.splitlines())

    committer_index = [i for (i,line) in enumerate(commit_lines)
                       if line.startswith(b'committer ')][0]
    committer_line = commit_lines[committer_index]

    match = re.match(br'committer (?P<name>.*?)'
                     br'(?P<hex> [0-9A-F]{16})? <(?P<mail>.*)> '
                     br'(?P<date>.*)',
                     committer_line)

    assert match, "Unable to parse committer line `%s'" % committer_line

    committer_name = match.group('name')
    committer_mail = match.group('mail')
    committer_date = match.group('date')
    # discard match.group('hex'), assume nobody has 64bit hex last name

    prefix = (b'\n'.join(commit_lines[:committer_index]) +
              b'\ncommitter ' + committer_name + b' ')
    rest = ((b'F'*16) + b" <" + committer_mail + b"> " + committer_date +
            b'\n' + b'\n'.join(commit_lines[committer_index + 1:]) + b'\n')

    header = commit_header(len(prefix) + len(rest))

    return (header + prefix + rest,
            len(header) + len(prefix),
            committer_name,
            committer_mail,
            committer_date)

def preprocess_commit_raw_change(commit):
    """
    Returns:
        [commit_with_header_and_placeholder, placeholder_offset]
    """
    commit_lines = list(commit.splitlines())
    header_end_index = commit_lines.index(b'')

    vanity_token = b'vanity'
    if commit_lines[header_end_index - 1] == b' -----END PGP SIGNATURE-----':
        insert_index = header_end_index - 1
        vanity_token = b' vanity'
    else:
        insert_index = header_end_index
        vanity_token = b'vanity '

    if commit_lines[insert_index - 1].startswith(vanity_token):
        insert_index = insert_index - 1
        commit_lines.pop(insert_index)

    prefix = b'\n'.join(commit_lines[:insert_index]) + b'\n' + vanity_token
    rest = ((b'F'*16) + b'\n' +
             b'\n'.join(commit_lines[insert_index:]) + b'\n')

    header = commit_header(len(prefix) + len(rest))

    return (header + prefix + rest, len(header) + len(prefix))

def commit_header(commit_len):
    return bytes('commit %d\x00' % commit_len, 'ascii')

def commit_add_header(commit):
    return commit_header(len(commit)) + commit

def commit_without_header(commit):
    null_index = commit.find(b'\x00')
    if null_index == -1:
        return commit
    return commit[null_index + 1:]

def sha1_prefix_search_opencl(data, hex_prefix, offset,
                              start=0, stop=(1 << 64),
                              opencl_vars=None,
                              gs=GS, ws=WS,
                              quiet=False):
    """Return %016x.upper() or raises a ValueError if nothing is found"""
    if opencl_vars is None:
        opencl_vars = load_opencl()
    ctx, queue, prg = opencl_vars

    display_device_info(queue.device)

    assert gs % ws == 0, "Global size must be a multiple of work size"

    target, precision_bits = hex2target(hex_prefix)
    preprocessed_message = sha1_preprocess_data(data)

    result = np.zeros(2, dtype=np.uint64)

    mf = cl.mem_flags
    # create buffers
    message_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR,
                            hostbuf=preprocessed_message)
    target_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR,
                           hostbuf=target)
    result_buf = cl.Buffer(ctx, mf.WRITE_ONLY | mf.COPY_HOST_PTR,
                           hostbuf=result)

    # the main stuff
    for current_start in progress(start, stop, gs, precision_bits, quiet):
        prg.sha1_prefix_search(queue,
                               (gs,),
                               (ws,),
                               message_buf,
                               struct.pack('I', preprocessed_message.shape[0]),
                               target_buf,
                               struct.pack('I', precision_bits),
                               struct.pack('I', offset),
                               struct.pack('Q', current_start),
                               result_buf)

        cl.enqueue_copy(queue, result, result_buf)

        if result[0]: # we found it
            return ('%016x' % result[1]).upper()

    else:
        raise ValueError("Unable to find matching prefix...")

def amend_commit_using_committer(committer_name,
                                 committer_mail,
                                 committer_date,
                                 hex_magic):
    env = os.environ.copy()
    env['GIT_COMMITTER_NAME'] = committer_name.decode() + " " + hex_magic
    env['GIT_COMMITTER_EMAIL'] = committer_mail.decode()
    env['GIT_COMMITTER_DATE'] = committer_date.decode()

    print(env['GIT_COMMITTER_NAME'])

    subprocess.check_call(['git', 'commit', '--amend', '--no-edit',
                           '-c', 'HEAD'], env=env)
    print('Current HEAD:')
    subprocess.check_call(['git', 'rev-parse', 'HEAD'])

def amend_commit_using_raw(object_contents):
    cmd = subprocess.Popen(
                ['git', 'hash-object', '-w', '-t', 'commit', '--stdin'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE
            )
    commit = cmd.communicate(input=object_contents)[0].strip()

    subprocess.check_call(['git', 'update-ref', 'HEAD', commit])
    print('Current HEAD:')
    subprocess.check_call(['git', 'rev-parse', 'HEAD'])


def main(hex_prefix, start=0, gs=GS, ws=WS, write_changes=False, quiet=False,
         use_raw_changes=False):
    """
    Attempts to change in the current directory
    hex_prefix is the desired prefix
    start is int or hex string
    """
    commit = extract_commit('HEAD')

    if use_raw_changes:
        [data, placeholder_offset] = preprocess_commit_raw_change(commit)
    else:
        [data,
         placeholder_offset,
         committer_name,
         committer_mail,
         committer_date] = preprocess_commit_committer_change(commit)

    if isinstance(start, str):
        start = int(start, 16)

    print(("Attempting to find sha1 prefix `%s'\n"
           "for commit `%s'\n"
           "================\n%s================\n\n")
          % (hex_prefix,
             sha1(commit_add_header(commit)).hexdigest(),
             commit.decode()))

    result = sha1_prefix_search_opencl(data,
                                       hex_prefix,
                                       placeholder_offset,
                                       start,
                                       gs=gs, ws=ws,
                                       quiet=quiet)

    final = (data[:placeholder_offset] +
             result.encode() +
             data[placeholder_offset + 16:])
    final_object = commit_without_header(final)

    print(("\nFound sha1 prefix `%s'\n"
           "with sha1 `%s'\n"
           "Using %s\n"
           "================\n%s================\n\n")
          % (hex_prefix,
             sha1(final).hexdigest(),
             result,
             final_object.decode()))

    if write_changes:
        print("Writing changes to the repository...\n")
        if use_raw_changes:
            amend_commit_using_raw(final_object)
        else:
            amend_commit_using_committer(committer_name,
                                         committer_mail,
                                         committer_date,
                                         result)
        print("All done.")
    else:
        print("Changes not written to the repository.")


if __name__ ==  '__main__':
    parser = argparse.ArgumentParser(
        prog="git-vanity",
        description="Create vanity commits "
                    "by extending the committer's name or the commit object.")
    parser.add_argument('hex_prefix',
                        type=str,
                        help="the desired hex prefix")
    parser.add_argument('-s', '--start',
                        default='0',
                        type=lambda x: int(x, 16),
                        help="start the search from number (hex)")
    parser.add_argument('-g', '--global-size',
                        dest='gs',
                        default=GS,
                        type=int,
                        help="OpenCL global size (use carefully)")
    parser.add_argument('-w', '--work-size',
                        dest='ws',
                        default=WS,
                        type=int,
                        help="OpenCL work size (64,128,256,...)")
    parser.add_argument('-W', '--write',
                        action='store_true',
                        default=False,
                        help="write to the repo")
    parser.add_argument('-q', '--quiet',
                        action='store_true',
                        default=False,
                        help="quiet mode, disables progress")
    parser.add_argument('-r', '--raw',
                        action='store_true',
                        default=False,
                        help="change the raw commit instead of the committer")
    parser.add_argument('--version',
                        action='version',
                        version="%(prog)s " + VERSION)

    args = parser.parse_args()

    main(args.hex_prefix, args.start,
         args.gs, args.ws,
         args.write,
         args.quiet,
         args.raw)
