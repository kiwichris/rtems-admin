#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2023-2024 Chris Johns (chris@contemporary.software)
# All rights reserved.
#
# This file is part of the RTEMS Tools package in 'rtems-tools'.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#

import base64
import datetime
import email
import gzip
import hashlib
import json
import mailbox
import os
import os.path
import re
import shutil
import time
import urllib.request


def _print_percentage(what, percent, month):
    if percent > 100:
        percent = 100
    print('\r' + what + ' ' + month + ' ' + \
          '.' * (20 - len(month)) + \
          ' %0.0f%% ' % (percent), end='')


def this_year():
    today = datetime.datetime.today()
    return today.year


def this_month():
    today = datetime.datetime.today()
    return today.month


def this_year_month():
    today = datetime.datetime.today()
    return datetime.date(today.year, today.month, 1).strftime('%Y-%B')


def archive_year(archive):
    dt = datetime.datetime.strptime(archive, '%Y-%B')
    return dt.year


def archive_label(year, month):
    dt = datetime.date(year, month, 1)
    return dt.strftime('%Y-%B')


def archive_month(archive):
    dt = datetime.datetime.strptime(archive, '%Y-%B')
    return dt.month


def month_months(year, month):
    today = datetime.datetime.today()
    mnths = []
    while year < today.year or (year == today.year
                                and month < today.month + 1):
        mnt = datetime.date(year, month, 1).strftime('%Y-%B')
        mnths.append(mnt)
        month += 1
        if month > 12:
            year += 1
            month = 1
    return mnths


def year_months(year, month):
    today = datetime.datetime.today()
    years = {}
    while year < today.year or (year == today.year
                                and month < today.month + 1):
        if year not in years:
            years[year] = []
        mnt = datetime.date(year, month, 1).strftime('%Y-%B')
        years[year].append(mnt)
        month += 1
        if month > 12:
            year += 1
            month = 1
    return years


class lists:

    lists_base = 'https://lists.rtems.org'
    mailman_base = lists_base + '/pipermail'
    builds_base = mailman_base + '/build'
    builds_ext = '.txt.gz'

    #
    # Archives stored in file with the follow path:
    #  https://lists.rtems.org/2022-November.txt.gz
    #

    def __init__(self, cache, start_year, start_month):
        if os.path.exists(cache):
            if not os.path.isdir(cache):
                raise RuntimeError('cache is not a directoru: ' + cache)
        else:
            os.mkdir(cache)
        self.archives = {}
        self.start_year = start_year
        self.start_month = start_month
        self.iter_months = None
        self.archives_dirty = False
        self.cache = cache
        self.data_filename = os.path.join(self.cache, 'months.json')
        self.load()

    def __iter__(self):
        self.iter_months = self.months()
        return self

    def __next__(self):
        if self.iter_months is None:
            raise StopIteration
        month = self.iter_months.pop(0)
        if len(self.iter_months) == 0:
            self.iter_months = None
        return month

    def checksum(self, month):
        archive = self.archives[month]
        hasher = hashlib.new('sha512')
        with open(archive['file'], 'rb') as f:
            hasher.update(f.read())
        return base64.b64encode(hasher.digest()).decode('utf-8')

    def check_checksum(self, month):
        if 'sha512' not in self.archives[month]:
            return False
        return self.checksum(month) == self.archives[month]['sha512']

    def file_name(self, month):
        if month not in self.archives:
            raise Exception('unknown month: ' + month)
        return self.archives[month]['file']

    def url(self, month):
        return self.builds_base + '/' + month + self.builds_ext

    def download(self, force=False, percentage=True):
        today = this_year_month()
        months = self.months()
        if force or len(months) == 0:
            months = month_months(self.start_year, self.start_month)
        for month in months:
            if percentage:
                _print_percentage('Downloading', 0, month)
            load = force
            if month in self.archives:
                archive = self.archives[month]
                if os.path.exists(archive['file']):
                    if not self.check_checksum(month) or month == today:
                        load = True
                if month == today:
                    load = True
            else:
                archive = None
            if load:
                _ssl_context = None
                req = urllib.request.Request(self.url(month))
                try:
                    import ssl
                    _ssl_context = ssl._create_unverified_context()
                    reader = urllib.request.urlopen(req, context=_ssl_context)
                except:
                    _ssl_context = None
                if _ssl_context is None:
                    try:
                        reader = urllib.request.urlopen(req)
                    except:
                        return None
                info = reader.info()
                if archive is None:
                    archive = {
                        'year-month': month,
                        'year': archive_year(month),
                        'month': archive_month(month),
                        'etag': info.get('ETag'),
                        'size': int(info.get('Content-Length').strip()),
                        'sha512': '',
                        'file': os.path.join(self.cache,
                                             month + self.builds_ext)
                    }
                    self.archives[month] = archive
                    self.archives_dirty = True
                    load = True
                with open(archive['file'], 'wb') as writer:
                    chunk_size = 256 * 1024
                    size = archive['size']
                    have = 0
                    while True:
                        chunk = reader.read(chunk_size)
                        if not chunk:
                            break
                        writer.write(chunk)
                        have += chunk_size
                        if percentage:
                            percent = round((float(have) / size) * 100, 2)
                            _print_percentage('Downloading', percent, month)
                with gzip.open(archive['file'], 'rb') as gz:
                    pass
                archive['etag'] = info.get('ETag')
                archive['size'] = int(info.get('Content-Length').strip())
                archive['sha512'] = self.checksum(month)
                reader.close()
            if percentage:
                _print_percentage('Downloading', 100, month)
                print()

    def load(self):
        if self.archives_dirty:
            raise Exception('load with dirty archives')
        if os.path.exists(self.data_filename):
            with open(self.data_filename, 'r', encoding='utf-8') as f:
                self.archives = json.loads(f.read())

    def save(self):
        if self.archives_dirty:
            s = json.dumps(self.archives, sort_keys=True, indent=2)
            with open(self.data_filename, 'w', encoding='utf-8') as f:
                f.write(s)

    def months(self):
        start_datetime = datetime.date(self.start_year, self.start_month,
                                       1).strftime('%Y-%B')
        mnts = sorted(
            list(self.archives),
            key=lambda date: datetime.datetime.strptime(date, '%Y-%B'))
        if start_datetime in mnts:
            mnts = mnts[mnts.index(start_datetime):]
        return mnts


class month_results:

    re_rtems_buildset = re.compile('^[0-9]+/rtems-.*$')

    # All archs ever supported
    rtems_architectures = [
        'aarch64', 'arm', 'bfin', 'epiphany', 'i386', 'lm32', 'm68k',
        'microblaze', 'mips', 'moxie', 'nios2', 'or1k', 'powerpc', 'riscv',
        'riscv32', 'riscv64', 'sh', 'sparc', 'sparc64', 'v850', 'x86_64'
    ]

    def __init__(self, year, month, passes, fails):
        self.year = year
        self.month = month
        self.passes = passes
        self.fails = fails

    def __str__(self):
        o = 'total: %5d  passes: %5d  fails %5d' % (len(self.passes) + len(
            self.fails), len(self.passes), len(self.fails))
        return o

    @staticmethod
    def _rtems_buildset(bset):
        return month_results.re_rtems_buildset.match(bset)

    @staticmethod
    def _rtems_arch(bset):
        if not month_results._rtems_buildset(bset):
            return False
        bs = bset.replace('.bset', '')
        return True in [
            bset.endswith(a) for a in month_results.rtems_architectures
        ]

    @staticmethod
    def _get_list(key, recs):
        return sorted(list(set(r[key] for r in recs)))

    def _get_passed_list(self, key):
        return self._get_list(key, self.passes)

    def _get_failed_list(self, key):
        return self._get_list(key, self.failed)

    def has_builds(self):
        return (len(self.passes) + len(self.fails)) != 0

    def hosts(self):
        return self._get_list('host', self.fails + self.passes)

    def buildsets(self):
        return self._get_list('buildset', self.fails + self.passes)

    def rtems_archs(self):
        return [
            bs.replace('.bset', '') for bs in self.buildsets()
            if self._rtems_arch(bs)
        ]

    def passed_host(self):
        return self._get_passed_list('host')

    def passed_buildsets(self):
        return self._get_passed_list('buildset')

    def passed_rtems_archs(self):
        return [bs for bs in self.passed_buildsets() if self._rtems_arch(bs)]

    def failed_hosts(self):
        return self._get_list('host', self.fails)

    def failed_buildsets(self):
        return self._get_list('buildset', self.fails)

    def failed_rtems_archs(self):
        return [bs for bs in self.failed_buildsets() if self._rtems_arch(bs)]

    def failed_rtems_arch_builds(self):
        failed_hosts = self.failed_hosts()
        failed_rtems_archs = []
        for arch in self.failed_rtems_archs():
            print(arch)
            xx
            hosts = set([r['host'] for r in self.fails if r['arch'] == arch])
            if not set(failed_hosts).isdisjoint(hosts):
                print(arch, '%d: %r  ' % (len(failed_hosts), failed_hosts),
                      '%d: %r' % (len(hosts), hosts))
                failed_archs += [arch]
        return failed_archs


class year_results:

    def __init__(self):
        self.years = {}

    def _years_months(self, year, month):
        if year is None:
            years = list(self.years)
        else:
            years = [year]
        count = 0
        if month is None:
            months = list(range(0, 12))
        else:
            months = [month]
        return years, months

    def _sweep_counter(self, year, month, action):
        years, months = self._years_months(year, month)
        count = 0
        for year in years:
            for month in months:
                results = self.years[year][month - 1]
                if results is not None:
                    count += action(results)
        return count

    def _sweep_list(self, year, month, action):
        years, months = self._years_months(year, month)
        l = []
        for year in years:
            for month in months:
                results = self.years[year][month - 1]
                if results is not None:
                    d = action(results)
                    l += action(results)
        return sorted(list(set(l)))

    def add(self, year, month, results):
        if year not in self.years:
            self.years[year] = [None] * 12
        if self.years[year][month - 1] is not None:
            raise RuntimeError('month set in year results: ' + str(month))
        self.years[year][month - 1] = results

    def builds_count(self, year=None, month=None):
        return self.passes_count(year, month) + self.fails_count(year, month)

    def passes_count(self, year=None, month=None):
        return self._sweep_counter(year, month,
                                   lambda results: len(results.passes))

    def fails_count(self, year=None, month=None):
        return self._sweep_counter(year, month,
                                   lambda results: len(results.fails))

    def hosts(self, year=None, month=None):
        return self._sweep_list(year, month, lambda results: results.hosts())

    def hosts_count(self, year=None, month=None):
        return self._sweep_counter(year, month,
                                   lambda results: len(results.hosts()))

    def rtems_archs(self, year=None, month=None):
        return self._sweep_list(year, month,
                                lambda results: results.rtems_archs())

    def rtems_archs_count(self, year=None, month=None):
        return self._sweep_counter(year, month,
                                   lambda results: len(results.rtems_archs()))


class emails:

    def __init__(self, archive, mbox):
        self.archive = archive
        self.year = archive_year(archive)
        self.month = archive_month(archive)
        self.mbox = mbox
        self.data = {
            'messages': {},
            'from': {},
            'builds': [],
            'tests': [],
            'bsp-builds': [],
            'unknown': [],
            'pass': {},
            'fail': {}
        }

    def __str__(self):
        s = [self.archive + ':']
        s += [' messages: ' + str(len(self.data['messages']))]
        s += [' builds: ' + str(len(self.data['builds']))]
        s += [' tests: ' + str(len(self.data['tests']))]
        s += [' bsp-builds: ' + str(len(self.data['bsp-builds']))]
        s += [' unknown: ' + str(len(self.data['unknown']))]
        return os.linesep.join(s)

    def _add_mid(self, bucket, key, mid):
        if key not in bucket:
            bucket[key] = []
        bucket[key] += [mid]

    def _get_message(self, mid):
        if mid not in self.data['messages']:
            raise Exception('message not found: ' + mid)
        return self.data['messages'][mid]

    def _get_subject(self, mid):
        s = self._get_message(mid)['Subject']
        return s.replace(os.linesep, '')

    def parse(self, percentage=True):
        mbox_txt = os.path.splitext(self.mbox)[0]
        with gzip.open(self.mbox, 'rb') as gz:
            with open(mbox_txt, 'wb') as txt:
                shutil.copyfileobj(gz, txt)
        try:
            mbox = mailbox.mbox(mbox_txt, create=False)
            msgs = len(mbox)
            count = 0
            for msg in mbox.values():
                if count % 64 == 0 and percentage:
                    percent = round((float(count) / msgs) * 100, 2)
                    _print_percentage('Parsing', percent, self.archive)
                e = email.message_from_string(str(msg))
                mid = e['Message-ID']
                if mid in self.data['messages']:
                    continue
                self.data['messages'][mid] = e
                mfrom = e['From']
                msubject = self._get_subject(mid)
                self._add_mid(self.data['from'], mfrom, mid)
                if msubject.startswith('Build '):
                    self.data['builds'] += [mid]
                elif msubject.startswith('[rtems-test] '):
                    self.data['tests'] += [mid]
                elif msubject.startswith('[rtems-bsp-builder] '):
                    self.data['bsp-builds'] += [mid]
                else:
                    self.data['unknown'] += [mid]
                count += 1
            if percentage:
                _print_percentage('Parsing', 100, self.archive)
                print()
        finally:
            if os.path.exists(mbox_txt):
                os.remove(mbox_txt)

    def build_results(self):
        fails = []
        passes = []
        for mid in self.data['builds']:
            msg = self._get_message(mid)
            s = self._get_subject(mid)
            ss = s.split(':')
            if len(ss) != 2:
                raise Exception('invalid build subject: ' + s)
            srs = ss[1].split()
            if len(srs) < 4:
                raise Exception('invalid build subject: ' + s)
            rec = {
                'result': srs[0].strip(),
                'host': ss[0][len('Build '):].strip(),
                'os': srs[3].strip(),
                'buildset': srs[1].strip()
            }
            # Early logs do not have the host
            if rec['host'] == '':
                sss = ss[1].split()
                if len(sss) != 4 or sss[2] != 'on':
                    rec['host'] = 'unknown'
                else:
                    if 'linux' in sss[3]:
                        rec['host'] = 'Linux'
                    elif 'freebsd' in sss[3]:
                        rec['host'] = 'FreeBSD'
                    elif 'w64-mingw32' in sss[3]:
                        rec['host'] = 'MINGW64_NT-10.0'
                    elif 'darwin' in sss[3]:
                        rec['host'] = 'Darwin'
                    else:
                        rec['host'] = 'unknown'
            if rec['result'] == 'PASSED':
                passes += [rec]
            elif rec['result'] == 'FAILED':
                fails += [rec]
            else:
                raise Exception('invalid build result: ' + rec['results'])
        return month_results(self.year, self.month, passes, fails)

    def has_unknowns(self):
        return len(self.data['unknown']) != 0

    def list_unknowns(self):
        s = []
        for mid in self.data['unknown']:
            s += [self._get_subject(mid)]
        return s
